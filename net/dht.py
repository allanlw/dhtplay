"""This module contains all of the DHT functions. In theory it could be used
as a standalone library. (still would be dependent on gobject though)."""

import gobject
import glib
import math
import random
from datetime import datetime

from net.bencode import *
from net.sha1hash import Hash
from net.contactinfo import ContactInfo
from net.sql import SQLiteThread

MAX_BUCKET_SIZE = 8
MAX_PENDING_PINGS = 2
IDLE_TIMEOUT = 15 * 60 # s

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
    r = self.conn.select_one("""SELECT COUNT(*) FROM buckets
                                WHERE server_id=?""", (self.server.id_num,))
    if r[0] == 0:
      lower = Hash(0)
      upper = Hash((1 << 160) - 1)
      now = datetime.now()
      self.conn.execute("""INSERT INTO buckets(id, start, end, created, updated,
                           server_id) VALUES(NULL, ?, ?, ?, ?, ?)""",
                        (lower, upper, now, now, self.server.id_num))
    glib.idle_add(self.emit, "changed")

  def _add_node(self, hash, contact, bucket, good, time, pending=False,
                version=None, received=False):
    received = int(received)
    id = self.conn.insert("""INSERT INTO nodes(id, hash, contact, bucket_id,
                             good, pending, version, received, created,
                             updated) VALUES (NULL, ?,?,?,?,?,?,?,?,?)""",
                          (hash, contact, bucket, good, pending,
                           version, received, time, time))
    glib.idle_add(self.emit, "node-added", hash)
    if not pending:
      self.conn.execute("UPDATE buckets SET updated=? WHERE id=?",
                        (time, bucket))
    glib.idle_add(self.emit, "bucket-changed", bucket)
    return id

  def _delete_node(self, id, hash):
    self.conn.execute("DELETE FROM nodes WHERE id=?", (id,))
    glib.idle_add(self.emit, "node-removed", hash)

  def _cull_bucket(self, now, bucket):
    rows = self.conn.select("""SELECT * FROM nodes
                               WHERE bucket_id=? AND NOT pending
                               ORDER BY updated ASC""",
                            (bucket,))
    if len(rows) < MAX_BUCKET_SIZE:
      return True
    culled = False
    for row in rows:
      if row["good"]:
        if (now - row["updated"]).seconds >= IDLE_TIMEOUT:
          self.server.send_ping(row["contact"].get_tuple())
      else:
        self._delete_node(row["id"], row["hash"])
        culled = True
        break
    return culled

  def _split_bucket(self, now, bucket_row, bstart, bend):
    bmid = bstart + (bend - bstart)/2
    self.conn.execute("UPDATE buckets SET end=?, updated=? WHERE id=?",
                      (Hash(bmid), now, bucket_row["id"]))
    newb = self.conn.insert("""INSERT INTO buckets(id, start, end, created,
                               updated, server_id) VALUES (NULL, ?, ?, ?, ?,
                               ?)""",
                            (Hash(bmid), bucket_row["end"], now, now,
                             self.server.id_num))
    oldb = bucket_row["id"]
    glib.idle_add(self.emit, "bucket-split", oldb, newb)

    rows = self.conn.select("""SELECT id,hash,pending FROM nodes
                               WHERE bucket_id=?""",
                            (oldb,))
    for row in rows:
      h = row[1]
      if h.get_int() >= bmid:
        self.conn.execute("UPDATE nodes SET bucket_id=? WHERE id=?",
                          (newb,row["id"]))
        glib.idle_add(self.emit, "node-changed", h)

  def add_node(self, contact, hash, version=None, received=False):
    if version is not None:
      version = buffer(version)
    now = datetime.now()

    node_row = self.conn.select_one("""SELECT nodes.* FROM nodes INNER JOIN
                                       buckets ON nodes.bucket_id=buckets.id
                                       WHERE nodes.hash=? AND
                                       buckets.server_id=?
                                       LIMIT 1""",
                                    (hash,self.server.id_num))
    if node_row is not None:
      received = int(received)
      self.conn.execute("""UPDATE nodes SET updated=?, version=?,
                           received=received+? WHERE id=?""",
                        (now, version, received, node_row["id"]))
      glib.idle_add(self.emit, "node-changed", hash)
      return

    bucket_row = self.conn.select_one("""SELECT * FROM buckets
                                         WHERE start<=? AND end>? AND
                                         server_id=?
                                         LIMIT 1""",
                                      (hash,hash, self.server.id_num))
    if bucket_row is None:
      raise ValueError("No bucket found???")

    count = self.conn.select_one("""SELECT COUNT(*) FROM nodes
                                    WHERE bucket_id=?""",
                                 (bucket_row["id"],))[0]

    bstart = bucket_row["start"].get_int()
    bend = bucket_row["end"].get_int()

    if count < MAX_BUCKET_SIZE:
      # add normally
      self._add_node(hash, contact, bucket_row["id"], True, now, False,
                     version, received)
    elif (bstart <= self.server.id.get_int() and
          self.server.id.get_int() < bend):
      # split bucket
      self._split_bucket(now, bucket_row, bstart, bend)
      self.add_node(contact, hash, version, received)
    else:
      # add pending
      culled = self._cull_bucket(now, bucket_row["id"])
      if culled:
        self.add_node(contact, hash, version, received)
      else:
        self._add_node(hash, contact, bucket_row["id"], True, now, True,
                       version, received)
  def get_node_row(self, n):
    if isinstance(n, ContactInfo):
      return self.conn.select_one("""SELECT nodes.* FROM nodes
                                     INNER JOIN buckets
                                     ON buckets.id=nodes.bucket_id
                                     WHERE nodes.contact=? AND
                                     buckets.server_id=? LIMIT 1""",
                                  (n,self.server.id_num))
    elif isinstance(n, Hash):
      return self.conn.select_one("""SELECT nodes.* FROM nodes
                                     INNER JOIN buckets
                                     ON buckets.id=nodes.bucket_id
                                     WHERE nodes.hash=? AND
                                     buckets.server_id=? LIMIT 1""",
                                  (n,self.server.id_num))
    else:
      raise TypeError("Unknown node identifier.")
  def get_bucket_row(self, id):
    return self.conn.select_one("SELECT * FROM buckets WHERE id=? LIMIT 1",
                                (id,))
  def get_node_rows(self):
    return self.conn.select("""SELECT nodes.* FROM nodes INNER JOIN buckets
                               ON buckets.id=nodes.bucket_id
                               WHERE buckets.server_id=?""",
                            (self.server.id_num,))
  def get_bucket_rows(self):
    return self.conn.select("SELECT * FROM buckets WHERE server_id=?",
                            (self.server.id_num,))
  def do_bucket_split(self, bucket1, bucket2):
    self.server._log("Bucket split ({0}, {1})".format(bucket1, bucket2))
    self.emit("changed")
  def do_bucket_changed(self, bucket):
    self.emit("changed")
  def do_node_added(self, node):
    self.server._log("Node added to db ({0})".format(node))
    self.emit("changed")
  def do_node_changed(self, node):
    self.emit("changed")
  def do_node_removed(self, node):
    self.server._log("Node removed from db ({0})".format(node))
    self.emit("changed")
  def refresh(self):
    now = datetime.now()
    rows = self.conn.select("""SELECT nodes.* FROM nodes INNER JOIN buckets
                               ON buckets.id=nodes.bucket_id
                               WHERE nodes.pending AND buckets.server_id=?""",
                            (self.server.id_num,))
    for row in rows:
      if not (now - row["updated"]).seconds < IDLE_TIMEOUT or not row["good"]:
        self._delete_node(row["id"], row["hash"])
      else:
        culled = self._cull_bucket(now, row["bucket_id"])
        if culled:
          self.conn.execute("""UPDATE nodes SET bucket_id=?, pending=?,
                               updated=? WHERE id=?""",
                            (row["bucket_id"], False, now, row["id"]))
          glib.idle_add(self.emit, "node-changed", row["hash"])
          self.conn.execute("UPDATE buckets SET updated=? WHERE id=?",
                            (now, row["bucket_id"]))
          glib.idle_add(self.emit, "bucket-changed",
                        row["bucket_id"])

    rows = self.conn.select("SELECT * FROM buckets WHERE server_id=?",
                            (self.server.id_num,))
    for r in rows:
      if (now - r["updated"]).seconds > IDLE_TIMEOUT:
        self._refresh_bucket(r["id"])

  def _refresh_bucket(self, bucket):
    r = self.conn.select_one("""SELECT contact FROM nodes WHERE bucket_id=?
                                AND NOT pending ORDER BY random() LIMIT 1""",
                             (bucket,))
    if r is not None:
      self.server.send_ping(r["contact"].get_tuple())
  def _handle_ping_response(self, hash, message):
    pass
  def _handle_find_response(self, hash, message):
    pass
  def _handle_get_peers_response(self, hash, message):
    pass
  def close(self):
    pass
  def get_closest(self, hash):
    r = self.conn.select("""SELECT nodes.* FROM nodes INNER JOIN buckets
                            ON buckets.id=nodes.bucket_id
                            WHERE buckets.server_id=?
                            ORDER BY xor(nodes.hash, ?) ASC
                            LIMIT ?""",
                         (self.server.id_num, hash, MAX_BUCKET_SIZE))
    return r
