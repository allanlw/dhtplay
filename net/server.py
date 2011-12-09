import SocketServer
import socket
import glib
import gobject
import traceback
import hashlib
import random

from net.dht import DHTRoutingTable
from net.sha1hash import Hash
from net.contactinfo import ContactInfo
from net.bencode import *
from net.bloom import BloomFilter
import version

REFRESH_CHECK = 30 # s
NUM_SECRETS = 20 # s

class DHTRequestHandler(SocketServer.DatagramRequestHandler):
  """Handler for DHT packets over UDP."""
  def handle(self):
    """Handle a new DHT packet."""
    enc_message = self.rfile.read()
    if not enc_message:
      return
    error = False
    try:
      message = bdecode(enc_message)[0]
    except BencodeError:
      self.send_error(self.client_address, 0,
                      [203,"Malformed DHT Packet!"])
      return
    if (message.has_key("q") and message["q"] == "refresh" and
        message.has_key("a") and message["a"].has_key("secret") and
        message["a"]["secret"] in self.server.secrets):
      self.server._update()
      return
    c = ContactInfo(*self.client_address)
    self.server._log("From "+str(c)+":"+str(message))  
    if message["y"] == "q":
      self.handle_query(c, message)
    else:
      self.handle_response(c, message)

  def handle_query(self, contact, message):
    """Handle a Query packet."""
    if not self.server.incoming:
      if self.server.routingtable.get_node_row(contact) == None:
        self.server.incoming = True

    try:
      version = message["v"]
    except KeyError:
      version = None
    try:
      self.server.routingtable.add_node(contact, Hash(message["a"]["id"]),
                                        version, True)
    except KeyError:
      pass

    response = {"id": self.server.id.get_20()}
    if message["q"] == "ping":
      pass
    elif message["q"] == "find_node":
      nodes = ""
      for row in self.server.routingtable.get_closest(Hash(message["a"]
                                                      ["target"])):
        nodes += str(row["hash"].get_20()) + str(row["contact"].get_packed())
      response["nodes"] = nodes
    elif message["q"] == "get_peers":
      nodes = ""
      for row in self.server.routingtable.get_closest(Hash(message["a"]
                                                      ["info_hash"])):
        nodes += str(row["hash"].get_20()) + str(row["contact"].get_packed())
      response["nodes"] = nodes

      trow = self.server.torrents.get_torrent_row(Hash(message["a"]
                                                  ["info_hash"]))
      if trow is not None:
        values = []
        ids = self.server.torrents.get_torrent_peers(trow["id"],
                                           (message["a"].has_key("noseed") and
                                            message["a"]["noseed"]))
        for id in ids:
          row = self.server.torrents.get_peer_by_id(id[0])
          values.append(row["contact"].get_packed())
        if values:
          response["values"] = values
        if message["a"].has_key("scrape") and message["a"]["scrape"]:
          response["BFsd"] = trow["seeds"].get_bin()
          response["BFpe"] = trow["peers"].get_bin()
      response["token"] = self.get_token(contact)
    elif message["q"] == "announce_peer": 
      if self.server.check_token(message["a"]["token"]):
        seed = False
        if message["a"].has_key("seed") and message["a"]["seed"]:
          seed = True
        self.server.torrents.add_torrent(ContactInfo(contact.host,
                                                     message["a"]["port"]),
                                         Hash(message["a"]["info_hash"]),
                                         seed)
      else:
        pass # TODO send error
    self.server.send_response(contact.get_tuple(), message["t"], response)
  def handle_response(self, contact, message):
    """Handle a response packet."""
    try:
      version = message["v"]
    except KeyError:
      version = None
    try:
      self.server.routingtable.add_node(contact,
                                        Hash(message["r"]["id"]), version, True)
    except KeyError:
      pass
    if self.server.callbacks.has_key(message["t"]):
      while self.server.callbacks[message["t"]]:
        self.server.callbacks[message["t"]].pop()(message)

class DHTServer(SocketServer.ThreadingUDPServer, gobject.GObject):
  incoming = gobject.property(type=bool, default=False)

  allow_reuse_address = True
  daemon_threads = True
  def __init__(self, config, id_num, id, bind, serv, conn, torrents,
               logfunc=None):
    self.logfunc = logfunc
    self._log("Server Starting...")

    gobject.GObject.__init__(self)
    SocketServer.UDPServer.__init__(self, bind.get_tuple(), DHTRequestHandler)
    self.last_tid = 0
    self.addr = serv
    self.bind = bind
    self.callbacks = {}
    self.config = config
    self.secrets = [hashlib.sha1(str(random.random())).digest()]
    self.conn = conn
    self.torrents = torrents
    self.id = Hash(id)
    self.id_num = id_num
    self.timeout_id = glib.timeout_add_seconds(REFRESH_CHECK,
                                               self._send_update)
    self.routingtable = DHTRoutingTable(self, self.conn)
    self.updatesocket = socket.socket(socket.AF_INET,
                                      socket.SOCK_DGRAM)

    self._log("Server Started.")
  def next_tid(self):
    self.last_tid += 1
    if (self.last_tid > 0xFFFF):
      self.last_tid = 0
    return chr((self.last_tid & 0xFF00) >> 8) + chr(self.last_tid & 0x00FF)

  def send_query(self, to, name, args):
    query = {"y":"q", "t":self.next_tid(), "q":name, "a":args,
             "v":version.four_byte}
    self.send_msg(to, query)
    return query["t"]
  def send_response(self, to, tid, args):
    response = {"y":"r", "t":tid, "r": args, "v":version.four_byte}
    self.send_msg(to, response)
    return response["t"]
  def send_error(self, to, tid, args):
    error = {"t":"e", "t":tid, "e":args, "v":version.four_byte}
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
    self.routingtable.close()
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
    self.routingtable._handle_get_peers_response(Hash(message["r"]["id"]),
                                                 message)

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
    self.secrets.insert(0, hashlib.sha1(str(random.random())).digest())
    while len(self.secrets) > NUM_SECRETS:
      self.secrets.pop()
    self._log("Routing table updated.")
    return True

  def _send_update(self):
    """Bootstrap an update from the main GUI thread by sending a UDP packet."""
    self.send_query(self.socket.getsockname(), "refresh",
                    {"secret": self.secrets[0]})
    return True

  def _log(self, msg):
    if self.logfunc:
      self.logfunc(msg)

  def check_token(self, contact, token):
    return any(token == self.get_token(contact, x) for x in self.secrets)

  def get_token(self, contact, secret=None):
    if secret is None:
      secret = self.secrets[0]
    return hashlib.sha1(contact.get_packed()+secret).digest()
