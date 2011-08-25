import gobject
import glib
import select
import Queue
import threading

from net.server import DHTServer
from net.sql import SQLiteThread
from net.torrents import TorrentDB
from net.upnp import UPNPManager
from net.contactinfo import ContactInfo

class ServerWrangler(gobject.GObject):
  __gsignals__ = {
    "server-added": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
      (DHTServer,)),
    "upnp-error": (gobject.SIGNAL_RUN_LASt, gobject.TYPE_NON,
      (ContactInfo, str))
  }
  timeout = 100
  def __init__(self, config, logfunc=None):
    gobject.GObject.__init__(self)

    self.logfunc = logfunc
    self.config = config
    self.servers = []
    self.pending = Queue.Queue()

    self.upnp = UPNPManager()
    self.upnp.connect("port-added", self._port_added)
    self.upnp.connect("add-port-error", self._add_port_error)

    self.conn = SQLiteThread(self.config.get("torrent", "db"))
    self.conn.start()
    self.conn.executescript(open("sql/db.sql","r").read())

    self.torrents = TorrentDB(self.conn, self._log)

    servers = self.conn.select("SELECT * FROM servers")
    for server in servers:
      self.add_server(server["hash"], server["bind"], server["host"],
                      server["upnp"], False)
  def add_server(self, hash, bind, host, upnp, insert=True):
    if upnp:
      if insert:
        self.conn.execute("""INSERT INTO servers(hash, bind, host, upnp)
                             VALUES (?, ?, ?, ?)""",
                          (hash, bind, None, True))
      self.upnp.add_udp_port(bind)
    else:
      if insert:
        server_id = self.conn.insert("""INSERT INTO servers(hash, bind, host,
                                        upnp) VALUES (?, ?, ?, ?)""",
                                   (hash, bind, host, False))
      self._do_add_server(hash, bind, host)
  def _do_add_server(self, hash, bind, host):
      new_server = DHTServer(self.config, server_id, hash, bind, host,
                             self.conn, self.torrents, self._log)
      self.pending.put(new_server)
      glib.idle_add(self.emit, "server-added", new_server)
  def _port_added(self, external, internal):
    row = self.conn.select_one("SELECT * FROM servers WHERE bind=?",
                               (internal,))
    self._do_add_server(row["hash"], internal, external)
  def _port_added_error(self, internal, error):
    glib.idle_add(self.emit, "upnp-error", internal, error)
  def _log(self, msg):
    if self.logfunc:
      self.logfunc(msg)
  def launch_dispatch(self):
    t = threading.Thread(target=self.dispatch)
    t.set_daemon(True)
    t.start()
  def dispatch(self):
    self.running = True
    poll = select.poll()
    while self.running:
      while True:
        try:
          a = self.pending.get(False)
        except Queue.Empty:
          break
        else:
          self.servers.append(a)
          poll.register(a, select.POLLIN)
      result = poll.poll(self.timeout)
      if result is not None:
        result[0].handle_request()
