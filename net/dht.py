"""This module contains all of the DHT functions. In theory it could be used
as a standalone library. (still would be dependent on gobject though)."""

import gobject
import glib
from datetime import datetime

from net.bencode import *
from net.sha1hash import Hash
from net.contactinfo import ContactInfo
from sql import queries

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
    if queries.get_num_buckets(self.conn, self.server.id_num) == 0:
      lower = Hash(0)
      upper = Hash((1 << 160) - 1)
      now = datetime.now()
      queries.create_bucket(self.conn, lower, upper, now, self.server.id_num)
    glib.idle_add(self.emit, "changed")

  def _add_node(self, hash, contact, bucket, good, time, pending=False,
                version=None, received=False):
    received = int(received)
    queries.create_node(self.conn, hash, contact, bucket, good, pending,
                        version, received, time)
    glib.idle_add(self.emit, "node-added", hash)
    if not pending:
      queries.set_bucket_updated(self.conn, bucket, time)
    glib.idle_add(self.emit, "bucket-changed", bucket)
    return id

  def _delete_node(self, id, hash):
    queries.delete_node(self.conn, id)
    glib.idle_add(self.emit, "node-removed", hash)

  def _cull_bucket(self, now, bucket):
    queries.get_non_pending_nodes_in_bucket(self.conn, bucket)
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
    queries.set_bucket_end(self.conn, bucket_row["id"], Hash(bmid), now)
    newb = queries.create_bucket(Hash(bmid), bucket_row["end"], now,
                                 self.server.id_num)
    oldb = bucket_row["id"]
    glib.idle_add(self.emit, "bucket-split", oldb, newb)

    rows = queries.get_nodes_in_bucket(self.conn, oldb)
    for row in rows:
      h = row[1]
      if h.get_int() >= bmid:
        queries.set_node_bucket(row["id"], newb)
        glib.idle_add(self.emit, "node-changed", h)

  def add_node(self, contact, hash, version=None, received=False):
    if version is not None:
      version = buffer(version)
    now = datetime.now()

    node_row = queries.get_node_by_hash(self.conn, self.server.id_num, hash)
    if node_row is not None:
      received = int(received)
      queries.set_node_updated(self.conn, node_row["id"], now, version,
                               received)
      glib.idle_add(self.emit, "node-changed", hash)
      return

    bucket_row = queries.get_bucket_for_hash(self.conn, self.server.id_num,
                                             hash)
    if bucket_row is None:
      raise ValueError("No bucket found???")

    count = queries.get_num_nodes_in_bucket(self.conn, bucket_row["id"])

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
      return queries.get_node_by_contact(self.conn, self.server.id_num, n)
    elif isinstance(n, Hash):
      return queries.get_node_by_hash(self.conn, self.server.id_num, n)
    else:
      raise TypeError("Unknown node identifier.")
  def get_bucket_row(self, id):
    return queries.get_bucket(self.conn, id)
  def get_node_rows(self):
    return queries.get_nodes_in_server(self.conn, self.server.id_num)
  def get_bucket_rows(self):
    return queries.get_buckets_in_server(self.conn, self.server.id_num)
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
    rows = queries.get_pending_nodes_in_server(self.conn, self.server.id_num)
    for row in rows:
      if not (now - row["updated"]).seconds < IDLE_TIMEOUT or not row["good"]:
        self._delete_node(row["id"], row["hash"])
      else:
        culled = self._cull_bucket(now, row["bucket_id"])
        if culled:
          queries.set_node_pending(self.conn, row["id"], False, now)
          glib.idle_add(self.emit, "node-changed", row["hash"])
          queries.set_bucket_updated(self.conn, row["bucket_id"], now)
          glib.idle_add(self.emit, "bucket-changed",
                        row["bucket_id"])

    rows = quries.get_buckets_in_server(self.conn, self.server.id_num)
    for r in rows:
      if (now - r["updated"]).seconds > IDLE_TIMEOUT:
        self._refresh_bucket(r["id"])

  def _refresh_bucket(self, bucket):
    r = queries.get_random_node_in_bucket(self.conn, bucket)
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
    return queries.get_closest_nodes(self.conn, self.server.id_num, hash,
                                  MAX_BUCKET_SIZE)
