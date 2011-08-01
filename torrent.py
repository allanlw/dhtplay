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
  def __init__(self, filename=":memory:"):
    gobject.GObject.__init__(self)
    self.conn = sqlite3.connect(filename)

    c = self.conn.cursor()
    c.executescript(""" 
      CREATE TABLE IF NOT EXISTS peers (
        id INTEGER PRIMARY KEY, contact TEXT UNIQUE,
        created timestamp, updated timestamp
      );
      CREATE TABLE IF NOT EXISTS torrents (
        id INTEGER PRIMARY KEY, hash TEXT UNIQUE,
        created timestamp, updated timestamp
      );
      CREATE TABLE IF NOT EXISTS peer_torrents (
        id INTEGER PRIMARY KEY, peer_id INTEGER, torrent_id INTEGER,
        seed BOOLEAN, created timestamp, updated timestamp
      );
    """)
  def add_torrent(self, peer, torrent, seed=False):
    now = datetime.now()
    c = self.conn.cursor()

    c.execute("SELECT * FROM peers WHERE contact=?", peer.get_packed())
    peer_row = c.fetchone()
    if peer_row is None:
      c.execute("INSERT INTO peers VALUES (NULL, ?, ?, ?)",
                (peer.get_packed(), now, now))      
      c.execute("SELECT * FROM peers WHERE contact=?", (peer.get_packed()))
      peer_row = c.fetchone()
      glib.idle_add(self.emit, "peer-added", peer_row)
    else:
      c.execute("UPDATE peers SET updated=? WHERE id=?",
                (now, peer_row["id"]))
      c.execute("SELECT * FROM peers WHERE contact=?", (peer.get_packed()))
      peer_row = c.fetchone()
      glib.idle_add(self.emit, "peer-updated", peer_row)

    c.execute("SELECT * FROM torrents WHERE hash=?", (torrent.get_20()))
    torrent_row = c.fetchone()
    if torrent_row is None:
      c.execute("INSERT INTO torrents VALUES (NULL, ?, ?, ?)",
                (torrent.get_id_20(), now, now))
      c.execute("SELECT * FROM torrents WHERE hash=?", (torrent.get_20()))
      torrent_row = c.fetchone()
      glib.idle_add(self.emit, "torrent-added", torrent_row)
    else:
      c.execute("UPDATE torrents SET updated=? WHERE id=?",
                (now, torrent_row["id"]))
      c.execute("SELECT * FROM torrents WHERE hash=?", (torrent.get_20()))
      torrent_row = c.fetchone()
      glib.idle_add(self.emit, "torrent-updated", torrent_row)

    c.execute("SELECT * FROM peer_torrents WHERE peer_id=? AND torrent_id=?",
              (peer_row["id"], torrent_row["id"]))
    peer_torrent_row = c.fetchone()
    if peer_torrent_row is None:
      c.execute("INSERT INTO peer_torrents VALUES (NULL, ?, ?, ?, ?, ?)",
                (peer_row["id"], torrent_row["id"], seed, now, now))
      c.execute("SELECT * FROM peer_torrents WHERE peer_id=? AND torrent_id=?",
                (peer_row["id"], torrent_row["id"]))
      peer_torrent_row = c.fetchone()
      glib.idle_add(self.emit, "peer-torrent-added", peer_torrent_row)
    else:
      c.execute("UPDATE peer_torrents SET updated=? WHERE id=?",
                (now, peer_torrent_row["id"]))
      c.execute("SELECT * FROM peer_torrents WHERE peer_id=? AND torrent_id=?",
                (peer_row["id"], torrent_row["id"]))
      peer_torrent_row = c.fetchone()
      glib.idle_add(self.emit, "peer-torrent-updated", peer_torrent_row)

    c.close()

  def close(self):
    self.conn.close()
