# This contains all of the DHT functions. In theory it could be used
# as a standalone library. (still would be dependent on GTK though)
import SocketServer
import time
import traceback
import socket
import gobject
import glib
import math
import hashlib
import random

from bencode import *
from net import Hash, ContactInfo
from torrent import TorrentDB

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
  def get_hash(self):
    return hashlib.sha1(self.host + str(self.port))

class DHTNode(gobject.GObject):
  __gsignals__ = {
    "changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
  }
  def __init__(self, server, host, port=None, id=None):
    gobject.GObject.__init__(self)

    if port is None and id is None:
      if len(host) != 26:
        raise ValueError("Invalid Compact Node Info!")
      id = host[0:20]
      host = host[20:26]

    self.contact = ContactInfo(host, port)
    self.id = Hash(id)
    self.bucket = None
    self.server = server
    self.last_good = time.time()
    self.first_seen = self.last_good
    self.pending_pings = 0
    self.good = True
    self.emit("changed")
  def is_valid(self):
    return self.is_good() and self.is_timely()
  def is_good(self):
    return self.good and self.pending_pings < MAX_PENDING_PINGS
  def is_timely(self):
    return (time.time() - self.last_good) < IDLE_TIMEOUT
  def send_ping(self):
    self.server.send_ping(self.contact.get_tuple())
  def _handle_ping_response(self, message):
    if message["y"] == "r" and message["r"]["id"] == self.get_id_20():
      self.good = True
      self.last_good = time.time()
    else:
      self.good = False
    glib.idle_add(self.emit, "changed")
    self.bucket.update()
  def _handle_find_response(self, message):
    self._handle_ping_response(message)
  def get_id_hex(self):
    return self.id.get_hex()
  def get_id_20(self):
    return self.id.get_20()
  def get_id_int(self):
    return self.id.get_int()

class DHTBucket(gobject.GObject):
  __gsignals__ = {
    "node-added": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (DHTNode,)),
    "node-removed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (DHTNode,)),
    "node-changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (DHTNode,)),
    "changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    "split": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (object,))
  }
  def __init__(self, start, end):
    gobject.GObject.__init__(self)
    self.id = -1
    self.start = start
    self.end = end
    self.nodes = []
    self.handlers = []
    self.last_changed = time.time()
    self.pending = []
    glib.idle_add(self.emit, "changed")
  def do_node_added(self, node):
    self.emit("changed")
  def do_node_removed(self, node):
    self.emit("changed")
  def do_changed(self):
    self.last_changed = time.time()
  def do_split(self, bucket):
    self.emit("changed")
  def do_node_changed(self, node):
    self.emit("changed")
  def node_in_range(self, node):
    return self.id_in_range(node.get_id_int())
  def id_in_range(self, id):
    return id >= self.start and id < self.end
  def is_full(self):
    return len(self.nodes) >= MAX_BUCKET_SIZE
  def refresh(self):
    try:
      random.choice(self.nodes).send_ping()
    except IndexError:
      pass
  def update(self):
    back = range(len(self.pending))
    back.reverse()
    for i in back:
      n = self.pending.pop(i)
      if n.is_valid():
        self.add_node(n)
    r = range(len(self.nodes))
    r.reverse()
    for i in r:
      if not self.nodes[i].is_good():
        self._remove_node(i)
    if time.time() - self.last_changed > IDLE_TIMEOUT:
      self.refresh()
  def split(self):
    half = self.start + ((self.end - self.start)/2)
    result = (DHTBucket(half, self.end), self.nodes[:])
    while self.nodes:
      self._remove_node(0)
    self.end = half
    glib.idle_add(self.emit, "split", result[0])
    return result
  def get_node(self, id):
    for n in self.nodes:
      if n.id.get_int() == id:
        return n
    return None
  def _add_node(self, node):
    node.bucket = self
    self.nodes.append(node)
    glib.idle_add(self.emit, "node-added", node)
    self.handlers.append(node.connect("changed", lambda w: glib.idle_add(self.emit, "node-changed", w)))
  def _remove_node(self, i):
    node = self.nodes.pop(i)
    node.bucket = None
    node.handler_disconnect(self.handlers.pop(i))
    glib.idle_add(self.emit, "node-removed", node)
  def add_node(self, node):
    if not self.node_in_range(node):
      raise ValueError("Adding node to invalid bucket!")
    if not node.is_valid():
      return
    if not self.is_full():
      self._add_node(node)
    else:
      added = False
      for i, n in enumerate(self.nodes):
        if n.is_good():
          if not n.is_timely():
            n.send_ping()
        else:
          self._remove_node(i)
          self._add_node(node)
          added = True
          break
      if not added:
        self.pending.append(node)
  def get_start_pow(self):
    try:
      return math.log(self.start, 2)
    except ValueError:
      return 0
  def get_end_pow(self):
    return math.log(self.end, 2)

class DHTRoutingTable(gobject.GObject):
  __gsignals__ = {
    "changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    "bucket-split": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (DHTBucket, DHTBucket)),
    "bucket-changed" : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (DHTBucket,)),
    "node-added": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (DHTBucket, DHTNode)),
    "node-removed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (DHTBucket, DHTNode)),
    "node-changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (DHTNode,))
  }
  def __init__(self):
    gobject.GObject.__init__(self)
    self.last_id = -1
    self.buckets = [DHTBucket(0l, 1l << 160)]
    self._bind_bucket(self.buckets[0])
    glib.idle_add(self.emit, "changed")
  def add_node(self, node, test=True):
    if test and self.get_node(node.get_id_int()) is not None:
      return
    for i, b in enumerate(self.buckets):
      if not b.node_in_range(node):
        continue
      if not b.is_full() or not b.id_in_range(node.server.id.get_int()):
        b.add_node(node)
      else:
        b2, nodes = b.split()
        self._bind_bucket(b2)
        self.buckets.insert(i+1, b2)
        nodes.append(node)
        for n in nodes:
          self.add_node(n, False)
      break
  def get_node(self, id):
    for b in self.buckets:
      if not b.id_in_range(id):
        continue
      return b.get_node(id)
  def do_bucket_split(self, bucket1, bucket2):
    self.emit("changed")
  def do_bucket_changed(self, bucket):
    self.emit("changed")
  def do_node_added(self, bucket, node):
    self.emit("changed")
  def do_node_changed(self, node):
    self.emit("changed")
  def do_node_removed(self, bucket, node):
    self.emit("changed")
  def _bind_bucket(self, bucket):
    self.last_id += 1
    bucket.id = self.last_id

    bucket.connect("split", lambda x, y: glib.idle_add(self.emit, "bucket-split", x, y))
    bucket.connect("changed", lambda b: glib.idle_add(self.emit, "bucket-changed", b) )
    bucket.connect("node-added", lambda b,n: glib.idle_add(self.emit, "node-added",b,n))
    bucket.connect("node-removed", lambda x, y: glib.idle_add(self.emit, "node-removed", x, y))
    bucket.connect("node-changed", lambda b, n: glib.idle_add(self.emit, "node-changed", n))
  def refresh(self):
    for bucket in self.buckets:
      bucket.update()

class DHTRequestHandler(SocketServer.DatagramRequestHandler):
  def handle(self):
    if self.server.logfunc:
      self.server.logfunc("Client connected:"+str(self.client_address))
    enc_message = self.rfile.read()
    if not enc_message:
      if self.server.logfunc:
        self.server.logfunc("From "+str(self.client_address)+":None")
      return
    message = bdecode(enc_message)[0]
    if self.server.logfunc:
      self.server.logfunc("From "+str(self.client_address)+":"+str(message))
    if message["y"] == "r":
      self.server.routingtable.add_node(DHTNode(self.server,
                                                self.client_address[0],
                                                self.client_address[1],
                                                message["r"]["id"]))
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
    self.torrents = TorrentDB(self.config.get("torrent", "db"))
    self.id = Hash(id)
    self.timeout_id = glib.timeout_add_seconds(REFRESH_CHECK, self._update)
    self.routingtable = DHTRoutingTable()
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
    if self.logfunc:
      self.logfunc("Server Stopped.")
  def add_nodes(self, nodes):
    while nodes:
      contact = nodes[0:26]
      nodes = nodes[26:]
      node = DHTNode(self, contact)
      self.routingtable.add_node(node)
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
      self.routingtable.get_node(id.get_int())._handle_ping_response(message)

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
    self.routingtable.get_node(id.get_int())._handle_find_response(message)

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
