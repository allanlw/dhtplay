import SocketServer
import socket
import glib
import gobject
import traceback

from net.torrent import TorrentDB
from net.dht import DHTRoutingTable
from net.sql import SQLiteThread
from net.sha1hash import Hash
from net.contactinfo import ContactInfo
from net.bencode import *

REFRESH_CHECK = 30 # s

class DHTRequestHandler(SocketServer.DatagramRequestHandler):
  def handle(self):
    enc_message = self.rfile.read()
    if not enc_message:
      self.server._log("From "+str(self.client_address)+":None")
      return
    message = bdecode(enc_message)[0]
    if message.has_key("q") and message["q"] == "refresh":
      self.server._update()
      return
    c = ContactInfo(*self.client_address)
    if not self.server.got_incoming:
      if self.server.routingtable.get_node_row(c) == None:
        self.server.got_incoming = True
    self.server._log("From "+str(c)+":"+str(message))  
    try:
      self.server.routingtable.add_node(c,
                                        Hash(message["r"]["id"]))
    except KeyError:
      pass
    if self.server.callbacks.has_key(message["t"]):
      while self.server.callbacks[message["t"]]:
        self.server.callbacks[message["t"]].pop()(message)

class DHTServer(SocketServer.UDPServer, gobject.GObject):
  got_incoming = gobject.property(type=bool, default=False)

  allow_reuse_address = True
  def __init__(self, config, id, bind, serv, logfunc=None):
    self.logfunc = logfunc
    self._log("Server Starting...")

    gobject.GObject.__init__(self)
    SocketServer.UDPServer.__init__(self, bind.get_tuple(), DHTRequestHandler)
    self.last_tid = 0
    self.addr = serv
    self.callbacks = {}
    self.config = config
    self.conn = SQLiteThread(self.config.get("torrent", "db"))
    self.conn.start()
    self.conn.executescript(open("sql/db.sql","r").read())
    self.torrents = TorrentDB(self, self.conn)
    self.id = Hash(id)
    self.timeout_id = glib.timeout_add_seconds(REFRESH_CHECK,
                                               self._send_update)
    self.routingtable = DHTRoutingTable(self, self.conn)
    self.updatesocket = socket.socket(socket.AF_INET,
                                      socket.SOCK_DGRAM)

    self._log("Server Started.")
  def next_tid(self):
    self.last_tid += 1
    if (self.last_tid >= 2<<16):
      self.last_tid = 0
    return chr(self.last_tid/((2<<8)-1))+chr(self.last_tid%((2<<8)-1))

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
    self._log("Sending message to "+str(to) +" - "+str(msg))
    enc_msg = bencode(msg)
    try:
      self.socket.sendto(enc_msg, to)
    except socket.error as (errno, strerror):
      self._log("Error sending message to "+str(to))
      return
    if self.logfunc:
      self._log("Message sent to "+str(to))

  def add_callback(self, tid, func):
    if self.callbacks.has_key(tid):
      self.callbacks[tid].append(func)
    else:
      self.callbacks[tid] = [func]
  def shutdown(self):
    self._log("Server Stopping...")
    glib.source_remove(self.timeout_id)
    SocketServer.UDPServer.shutdown(self)
    self.torrents.close()
    self.routingtable.close()
    self.conn.close()
    self._log("Server Stopped.")
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
    self._log("Sending ping to "+str(to))
    result = self.send_query(to, "ping", {"id": self.id.get_20()})
    self.add_callback(result, self._handle_ping_node)
    return result

  def _handle_ping_node(self, message):
    if (message["y"] == "r"):
      id = Hash(message["r"]["id"])
      self.routingtable._handle_ping_response(id, message)

  def send_find_node(self, to, hash):
    self._log("Sending find_node to "+str(to)+" with hash "+hash)
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

  def send_get_peers(self, to, hash, scrape):
    self._log("Sending get_peers to "+str(to)+" with hash "+hash)
    hash = Hash(hash)
    result = self.send_query(to, "get_peers", {"id": self.id.get_20(),
                                          "info_hash": hash.get_20(),
                                               "scrape": scrape})
    self.add_callback(result, lambda x: self._handle_get_peers(x, hash))
    return result
  def _handle_get_peers(self, message, hash):
    if message["r"].has_key("values"):
      for n in message["r"]["values"]:
        self.torrents.add_torrent(ContactInfo(n), hash)
    if message["r"].has_key("nodes"):
      self.add_nodes(message["r"]["nodes"])
    if message["r"].has_key("BFsp"):
      self.torrents.add_filter(BloomFilter(message["r"]["BFsp"]), hash, True)
    if message["r"].has_key("BFpe"):
      self.torrents.add_filter(BloomFilter(message["r"]["BFpe"]), hash, False)
    self.routingtable._handle_get_peers_response(Hash(message["r"]["id"]), message)

  def load_torrent(self, filename):
    f = open(filename, "r")
    dict = bdecode(f.read())[0]
    if not dict.has_key("nodes"):
      raise ValueError("torrent has no DHT Nodes")
    for n in dict["nodes"]:
      self.send_ping(tuple(n))

  def _update(self):
    """Actually do an update from within the server thread."""
    self._log("Updating routing table...")
    self.routingtable.refresh()
    self._log("Routing table updated.")
    return True

  def _send_update(self):
    """Bootstrap an update from the main GUI thread by sending a UDP packet."""
    msg = bencode({"y":"q", "q":"refresh", "t":"", "a":[]})
    self.updatesocket.sendto(msg, self.socket.getsockname()) 
#    self.routingtable.refresh()
    return True

  def _log(self, msg):
    if self.logfunc:
      self.logfunc(msg)
