"""This module contains all of the DHT functions. In theory it could be used
as a standalone library. (still would be dependent on gobject though)."""

import SocketServer
import traceback
import socket
import gobject
import glib
import math
import hashlib
import random
import sqlite3
from datetime import datetime

from bencode import *
from net import Hash, ContactInfo
from torrent import TorrentDB
from sql import SQLiteThread

MAX_BUCKET_SIZE = 8
MAX_PENDING_PINGS = 2
IDLE_TIMEOUT = 15 * 60 # s
REFRESH_CHECK = 30 # s

class BloomFilter:
  K = 2
  M = 256 * 8
  def __init__(self):
    self.bloom = [0 for x in range(256)]
  def insert_host(self, host):
    hash = Hash(hashlib.sha1(socket.inet_pton(host.host)).digest()).get_20()

    index1 = ord(hash[0]) | ord(hash[1]) << 8
    index2 = ord(hash[2]) | ord(hash[3]) << 8

    index1 %= self.M
    index2 %= self.M

    self.bloom[index1 / 8] |= 0x01 << (index1 % 8)
    self.bloom[index2 / 8] |= 0x01 << (index2 % 8)
  def get_estimate(self):
    set_bits = 0
    for a in self.bloom:
      b = a & 0b01010101
      c = (a >> 1) & 0b01010101
      d = b+c
      e = d & 0b00110011
      f = (d >> 2) & 0b00110011
      g = e + f
      h = g & 0b00001111
      i = (g >> 4) & 0b00001111
      j = h + i
      set_bits += j
    count = float(min(M-1, M-set_bits))
    size = math.log(count/m) / (K * log(1-1./M))
    return size
  def get_hex(self):
    result = ""
    for b in self.bloom:
      result += "{0:x}".format(b)
    return result
  def get_bin(self):
    result = ""
    for b in self.bloom:
      result += chr(b)

#  def _handle_ping_response(self, message):
#    if message["y"] == "r" and message["r"]["id"] == self.get_id_20():
#      self.good = True
#      self.last_good = time.time()
#    else:
#      self.good = False
#    glib.idle_add(self.emit, "changed")
#    self.bucket.update()

class DHTRoutingTable(gobject.GObject):
  __gsignals__ = {
    "changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    "bucket-split": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (int, int)),
    "bucket-changed" : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (int,)),
    "node-added":
       (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "node-removed":
       (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "node-changed":
       (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
  }
  def __init__(self, server, conn):
    gobject.GObject.__init__(self)

    self.conn = conn
    self.server = server
    r = self.conn.select_one("SELECT COUNT(*) FROM buckets")
    if r[0] == 0:
      lower = Hash(0).get_20()
      upper = Hash((1 << 160) - 1).get_20()
      now = datetime.now()
      self.conn.execute("INSERT INTO buckets VALUES(NULL, ?, ?, ?, ?)",
                        (lower, upper, now, now))
    glib.idle_add(self.emit, "changed")

  def _add_node(self, hash, contact, bucket, seed, time, pending=False):
    if pending:
      bid = None
    else:
      bid = bucket
    id = self.conn.insert("INSERT INTO nodes VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                          (hash.get_20(), contact.get_packed(),
                           bid, seed, time, time))
    glib.idle_add(self.emit, "node-added", hash)
    if not pending:
      self.conn.execute("UPDATE buckets SET updated=? WHERE id=?",
                        (time, bucket))
    else:
      self.conn.execute("INSERT INTO pending_nodes VALUES (NULL, ?, ?)",
                        (id, bucket))
    glib.idle_add(self.emit, "bucket-changed", bucket)
    return id

  def _delete_node(self, id, hash):
    self.conn.execute("DELETE FROM nodes WHERE id=?", (id,))
    glib.idle_add(self.emit, "node-removed", Hash(hash))

  def _cull_bucket(self, now, bucket):
    rows = self.conn.select("""SELECT * FROM nodes
                               WHERE bucket_id=?
                               ORDER BY updated ASC""",
                            (bucket,))
    culled = False
    for row in rows:
      if row["good"]:
        if (now - row["updated"]).seconds >= IDLE_TIMEOUT:
          self.server.send_ping(contact.get_tuple())
      else:
        self._delete_node(row["id"], row["hash"])
        culled = True
        break
    return culled

  def _split_bucket(self, now, bucket_row, bstart, bend):
    bmid = bstart + (bend - bstart)/2
    self.conn.execute("UPDATE buckets SET end=?, updated=? WHERE id=?",
                      (Hash(bmid).get_20(), now, bucket_row["id"]))
    newb = self.conn.insert("INSERT INTO buckets VALUES (NULL, ?, ?, ?, ?)",
                            (Hash(bmid).get_20(), bucket_row["end"], now, now))
    oldb = bucket_row["id"]
    glib.idle_add(self.emit, "bucket-split", oldb, newb)

    rows = self.conn.select("SELECT id,hash FROM nodes WHERE bucket_id=?",
                            (oldb,))
    for row in rows:
      h = Hash(row[1])
      if h.get_int() < bmid:
        self.conn.execute("UPDATE nodes SET bucket_id=? WHERE id=?",
                          (newb,row["id"]))
        glib.idle_add(self.emit, "node-changed", h)

  def add_node(self, contact, hash):
    now = datetime.now()

    node_row = self.conn.select_one("SELECT * FROM nodes WHERE hash=? LIMIT 1",
                                    (hash.get_20(),))
    if node_row is not None:
      self.conn.execute("UPDATE nodes SET updated=? WHERE id=?",
                        (now, node_row["id"]))
      glib.idle_add(self.emit, "node-changed", hash)
      return

    bucket_row = self.conn.select_one("""SELECT * FROM buckets
                                         WHERE start<=? AND end>?
                                         LIMIT 1""",
                                      (hash.get_20(),hash.get_20()))
    if bucket_row is None:
      raise ValueError("No bucket found???")

    count = self.conn.select_one("""SELECT COUNT(*) FROM nodes
                                    WHERE bucket_id=?""",
                                 (bucket_row["id"],))[0]

    bstart = Hash(bucket_row["start"]).get_int()
    bend = Hash(bucket_row["end"]).get_int()

    if count < MAX_BUCKET_SIZE:
      # add normally
      self._add_node(hash, contact, bucket_row["id"], True, now)
    elif (bstart <= self.server.id.get_int() and
          self.server.id.get_int() < bend):
      # split bucket
      self._split_bucket(now, bucket_row, bstart, bend)
      self.add_node(contact, hash)
    else:
      # add pending
      culled = self._cull_bucket(now, bucket_row["id"])
      if culled:
        self.add_node(contact, hash)
      else:
        self._add_node(hash, contact, bucket_row["id"], True, now, True)
  def get_node_row(self, hash):
    return self.conn.select_one("SELECT * FROM nodes WHERE hash=? LIMIT 1",
                                (hash.get_20(),))
  def get_bucket_row(self, id):
    return self.conn.select_one("SELECT * FROM buckets WHERE id=? LIMIT 1",
                                (id,))
  def get_node_rows(self):
    return self.conn.select("SELECT * FROM nodes")
  def get_bucket_rows(self):
    return self.conn.select("SELECT * FROM buckets")
  def do_bucket_split(self, bucket1, bucket2):
    self.emit("changed")
  def do_bucket_changed(self, bucket):
    self.emit("changed")
  def do_node_added(self, node):
    self.emit("changed")
  def do_node_changed(self, node):
    self.emit("changed")
  def do_node_removed(self, node):
    self.emit("changed")
  def refresh(self):
    now = datetime.now()
    self.conn.execute("DELETE FROM nodes WHERE NOT good")
    rows = self.conn.select('''SELECT nodes.*, pending_nodes.* FROM nodes
                               INNER JOIN pending_nodes
                               ON nodes.id=pending_nodes.node_id''')

    for row in rows:
      if not (row["nodes.good"] and
              (now - row["nodes.updated"]).seconds > IDLE_TIMEOUT):
        self.conn.execute("DELETE FROM nodes WHERE id=?", (row["nodes.id"],))
        self.conn.execute("DELETE FROM pending_nodes WHERE id=?",
                          (row["pending_nodes.id"],))
      else:
        culled = self._cull_bucket(now, row["pending_nodes.bucket_id"])
        if culled:
          self.conn.execute("""UPDATE nodes SET bucket_id=?, updated=?
                               WHERE id=?""",
                            (row["pending_nodes.bucket_id"], now,
                             row["nodes.id"]))
          glib.idle_add(self.emit, "node-added", Hash(row["nodes.hash"]))
          self.conn.execute("UPDATE buckets SET update=? WHERE id=?",
                            (now, row["pending_nodes.bucket_id"]))
          glib.idle_add(self.emit, "bucket-changed",
                        row["pending_nodes.bucket_id"])

    rows = self.conn.select("SELECT * FROM buckets")
    for r in rows:
      if (now - r["updated"]).seconds > IDLE_TIMEOUT:
        self._refresh_bucket(r["id"])

  def _refresh_bucket(self, bucket):
    r = self.conn.select_one("""SELECT contact FROM nodes WHERE bucket_id=?
                                ORDER BY random() LIMIT 1""",
                             (bucket,))
    if r is not None:
      self.server.send_ping(ContactInfo(r["contact"]).get_tuple())
  def _handle_ping_response(self, hash, message):
    pass
  def _handle_find_response(self, hash, message):
    pass
  def _handle_get_peers_response(self, hash, message):
    pass
  def close(self):
    pass

class DHTRequestHandler(SocketServer.DatagramRequestHandler):
  def handle(self):
    enc_message = self.rfile.read()
    if not enc_message:
      if self.server.logfunc:
        self.server.logfunc("From "+str(self.client_address)+":None")
      return
    message = bdecode(enc_message)[0]
    if message.has_key("q") and message["q"] == "refresh":
      self.server._update()
      return
    if self.server.logfunc:
      self.server.logfunc("From "+str(self.client_address)+":"+str(message))
    if message["y"] == "r":
      self.server.routingtable.add_node(ContactInfo(*self.client_address),
                                        Hash(message["r"]["id"]))
    if self.server.callbacks.has_key(message["t"]):
      while self.server.callbacks[message["t"]]:
        self.server.callbacks[message["t"]].pop()(message)

class DHTServer(SocketServer.UDPServer):
  allow_reuse_address = True
  def __init__(self, config, id = None, bind=("127.0.0.1", 6881), logfunc=None):
    self.logfunc = logfunc
    if self.logfunc:
      self.logfunc("Server Starting...")

    SocketServer.UDPServer.__init__(self, bind, DHTRequestHandler)
    self.last_tid = 0
    self.callbacks = {}
    self.config = config
    self.conn = SQLiteThread(self.config.get("torrent", "db"))
    self.conn.start()
    self.conn.executescript(open("db.sql","r").read())
    self.torrents = TorrentDB(self.conn)
    self.id = Hash(id)
    self.timeout_id = glib.timeout_add_seconds(REFRESH_CHECK,
                                               self._send_update)
    self.routingtable = DHTRoutingTable(self, self.conn)

    if self.logfunc:
      self.logfunc("Server Started.")
    self._update()
  def next_tid(self):
    self.last_tid += 1
    if (self.last_tid >= 2**16):
      self.last_tid = 0
    return chr(self.last_tid/(2<<8))+chr(self.last_tid%(2<<8))

  def send_query(self, to, name, args):
    query = {"y":"q", "t":self.next_tid(), "q":name, "a":args}
    self.send_msg(to, query)
    return query["t"]
  def send_response(self, to, tid, args):
    response = {"y":"r", "t":tid, "r": args}
    self.send_msg(to, response)
    return response["t"]
  def send_error(self, to, tid, args):
    error = {"t":"e", "t":tid, "e":args}
    self.send_msg(to, error)
    return error["t"]
  def send_msg(self, to, msg):
    if self.logfunc:
      self.logfunc("Sending message to "+str(to) +" - "+str(msg))
    enc_msg = bencode(msg)
    try:
      self.socket.sendto(enc_msg, to)
    except socket.error as (errno, strerror):
      if self.logfunc:
        self.logfunc("Error sending message to "+str(to))
      return
    if self.logfunc:
      self.logfunc("Message sent to "+str(to))

  def add_callback(self, tid, func):
    if self.callbacks.has_key(tid):
      self.callbacks[tid].append(func)
    else:
      self.callbacks[tid] = [func]
  def shutdown(self):
    if self.logfunc:
      self.logfunc("Server Stopping...")
    glib.source_remove(self.timeout_id)
    SocketServer.UDPServer.shutdown(self)
    self.torrents.close()
    self.routingtable.close()
    self.conn.close()
    if self.logfunc:
      self.logfunc("Server Stopped.")
  def add_nodes(self, nodes):
    while nodes:
      contact = nodes[0:26]
      nodes = nodes[26:]
      self.routingtable.add_node(ContactInfo(contact[20:26]),
                                 Hash(contact[0:20]))
  def handle_error(self, request, client_address):
    if self.logfunc:
      self.logfunc("Error with connection from "+str(client_address))
    traceback.print_exc() # XXX But this goes to stderr!

  def send_ping(self, to):
    if self.logfunc:
      self.logfunc("Sending ping to "+str(to))
    result = self.send_query(to, "ping", {"id": self.id.get_20()})
    self.add_callback(result, self._handle_ping_node)
    return result

  def _handle_ping_node(self, message):
    if (message["y"] == "r"):
      id = Hash(message["r"]["id"])
      self.routingtable._handle_ping_response(id, message)

  def send_find_node(self, to, hash):
    if self.logfunc:
      self.logfunc("Sending find_node to "+str(to)+" with hash "+hash)
    tid = Hash(hash)
    result = self.send_query(to, "find_node", {"id": self.id.get_20(),
                                               "target": tid.get_20()})
    self.add_callback(result, self._handle_find_node)
    return result
  def _handle_find_node(self, message):
    nodes = message["r"]["nodes"]
    self.add_nodes(nodes)
    id = Hash(message["r"]["id"])
    self.routingtable._handle_find_response(id, message)

  def send_get_peers(self, to, hash):
    if self.logfunc:
      self.logfunc("Sending get_peers to "+str(to)+" with hash "+hash)
    hash = Hash(hash)
    result = self.send_query(to, "get_peers", {"id": self.id.get_20(),
                                          "info_hash": hash.get_20()})
    self.add_callback(result, lambda x: self._handle_get_peers(x, hash))
    return result
  def _handle_get_peers(self, message, hash):
    if message["r"].has_key("values"):
      for n in message["r"]["values"]:
        self.torrents.add_peer(ContactInfo(n), hash)
    if message["r"].has_key("nodes"):
      self.add_nodes(message["r"]["nodes"])
    self.routingtable._handle_get_peers_response(Hash(message["r"]["id"]), message)

  def load_torrent(self, filename):
    f = open(filename, "r")
    dict = bdecode(f.read())[0]
    if not dict.has_key("nodes"):
      raise ValueError("torrent has no DHT Nodes")
    for n in dict["nodes"]:
      self.send_ping(tuple(n))

  def _update(self):
    if self.logfunc:
      self.logfunc("Updating routing table...")
    self.routingtable.refresh()
    if self.logfunc:
      self.logfunc("Routing table updated.")
    return True

  def _send_update(self):
#    msg = bencode({"y":"q", "q":"refresh", "t":"", "a":[]})
#    self.socket.sendto(msg, self.socket.getsockname()) 
    self.routingtable.refresh()
