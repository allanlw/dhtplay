import sqlite3
import gobject
import glib
from datetime import datetime

from net import ContactInfo, Hash

class TorrentDB(gobject.GObject):
  __gsignals__ = {
    "torrent-added":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "torrent-changed":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "peer-added":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "peer-changed":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "peer-torrent-added":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
       (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
    "peer-torrent-updated":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
       (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))
  }
  def __init__(self, server, conn):
    gobject.GObject.__init__(self)
    self.conn = conn
    self.server = server

  def do_torrent_added(self, torrent):
    self.server._log("Torrent added to db ({0})".format(torrent))

  def do_peer_added(self, peer):
    self.server._log("Peer added to db ({0})".format(peer))

  def add_torrent(self, peer, torrent, seed=False):
    now = datetime.now()
    c = self.conn

    peer_row = c.select_one("SELECT * FROM peers WHERE contact=? LIMIT 1",
                            (peer.get_packed(),))
    if not peer_row:
      c.execute("INSERT INTO peers VALUES (NULL, ?, ?, ?)",
                (peer.get_packed(), now, now))
      signal = "peer-added"
    else:
      c.execute("UPDATE peers SET updated=? WHERE id=?",
                (now, peer_row["id"]))
      signal = "peer-changed"

    peer_row = c.select_one("SELECT * FROM peers WHERE contact=? LIMIT 1",
                            (peer.get_packed(), ))
    glib.idle_add(self.emit, signal, peer)

    torrent_row = c.select_one("SELECT * FROM torrents WHERE hash=? LIMIT 1",
                               (torrent.get_20(), ))
    if torrent_row is None:
      c.execute("INSERT INTO torrents VALUES (NULL, ?, ?, ?)",
                (torrent.get_20(), now, now))
      signal = "torrent-added"
    else:
      c.execute("UPDATE torrents SET updated=? WHERE id=?",
                (now, torrent_row["id"]))
      signal = "torrent-changed"

    torrent_row = c.select_one("SELECT * FROM torrents WHERE hash=? LIMIT 1",
                               (torrent.get_20(),))
    glib.idle_add(self.emit, signal, torrent)

    peer_torrent_row = c.select_one("""SELECT * FROM peer_torrents
                                       WHERE peer_id=? AND torrent_id=?
                                       LIMIT 1""",
                                    (peer_row["id"], torrent_row["id"]))
    if peer_torrent_row is None:
      c.execute("INSERT INTO peer_torrents VALUES (NULL, ?, ?, ?, ?, ?)",
                (peer_row["id"], torrent_row["id"], seed, now, now))
      signal = "peer-torrent-added"
    else:
      c.execute("UPDATE peer_torrents SET updated=? WHERE id=?",
                (now, peer_torrent_row["id"]))
      signal = "peer-torrent-updated"

    peer_torrent_row = c.select_one("""SELECT * FROM peer_torrents
                                       WHERE peer_id=? AND torrent_id=?
                                       LIMIT 1""",
                                    (peer_row["id"], torrent_row["id"]))
    glib.idle_add(self.emit, signal, peer, torrent)

  def close(self):
    pass

  def get_torrent_row(self, hash):
    return self.conn.select_one("SELECT * FROM torrents WHERE hash=? LIMIT 1",
                                (hash.get_20(),))
  def get_peer_row(self, contact):
    return self.conn.select_one("SELECT * FROM peers WHERE contact=? LIMIT 1",
                                (contact.get_packed(),))
  def get_torrent_rows(self):
    return self.conn.select("SELECT * FROM torrents")
  def get_peer_rows(self):
    return self.conn.select("SELECT * FROM peers")
