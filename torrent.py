import sqlite3
import datetime
import gobject
import glib

from net import ContactInfo, Hash

class TorrentDB(gobject.GObject):
  __gsignals__ = {
    "torrent-added":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "torrent-updated":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "peer-added":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "peer-updated":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "peer-torrent-added":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    "peer-torrent-updated":
      (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
  }
  def __init__(self, conn):
    gobject.GObject.__init__(self)
    self.conn = conn

    self.conn.executescript(""" 
      CREATE TABLE IF NOT EXISTS peers (
        id INTEGER PRIMARY KEY, contact BLOB UNIQUE,
        created timestamp, updated timestamp
      );
      CREATE TABLE IF NOT EXISTS torrents (
        id INTEGER PRIMARY KEY, hash BLOB UNIQUE,
        created timestamp, updated timestamp
      );
      CREATE TABLE IF NOT EXISTS peer_torrents (
        id INTEGER PRIMARY KEY, peer_id INTEGER, torrent_id INTEGER,
        seed BOOLEAN, created timestamp, updated timestamp
      );
    """)
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
      signal = "peer-updated"

    peer_row = c.select_one("SELECT * FROM peers WHERE contact=? LIMIT 1",
                            (peer.get_packed(), ))
    glib.idle_add(self.emit, signal, peer_row)

    torrent_row = c.select_one("SELECT * FROM torrents WHERE hash=? LIMIT 1",
                               (torrent.get_20(), ))
    if torrent_row is None:
      c.execute("INSERT INTO torrents VALUES (NULL, ?, ?, ?)",
                (torrent.get_id_20(), now, now))
      signal = "torrent-added"
    else:
      c.execute("UPDATE torrents SET updated=? WHERE id=?",
                (now, torrent_row["id"]))
      signal = "torrent-updated"

    torrent_row = c.select_one("SELECT * FROM torrents WHERE hash=? LIMIT 1",
                               (torrent.get_20(),))
    glib.idle_add(self.emit, signal, torrent_row)

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
    glib.idle_add(self.emit, signal, peer_torrent_row)

  def close(self):
    pass
