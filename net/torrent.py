# Copyright (c) 2011-2013 Allan Wirth <allan@allanwirth.com>
#
# This file is part of DHTPlay.
#
# DHTPlay is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gobject
import glib
from datetime import datetime

from util.bloom import BloomFilter
from sql import queries

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
  def __init__(self, conn, logfunc):
    gobject.GObject.__init__(self)
    self.conn = conn
    self._log = logfunc

  def do_torrent_added(self, torrent):
    self._log("Torrent added to db ({0})".format(torrent))

  def do_peer_added(self, peer):
    self._log("Peer added to db ({0})".format(peer))

  def add_torrent(self, peer, torrent, seed=False):
    now = datetime.now()

    peer_row = queries.get_peer_by_contact(self.conn, peer)
    if not peer_row:
      queries.add_peer(self.conn, peer, now)
      signal = "peer-added"
    else:
      queries.set_peer_updated(self.conn, peer_row["id"], now)
      signal = "peer-changed"

    peer_row = queries.get_peer_by_contact(self.conn, peer)
    glib.idle_add(self.emit, signal, peer)

    seed_bloom = BloomFilter()
    peer_bloom = BloomFilter()
    if seed:
      seed_bloom.insert_host(peer)
    else:
      peer_bloom.insert_host(peer)

    torrent_row = queries.get_torrent_by_hash(self.conn, torrent)
    if torrent_row is None:
      queries.add_torrent(self.conn, torrent, now, seed_bloom, peer_bloom)
      signal = "torrent-added"
    else:
      queries.add_torrent_filters(self.conn, torrent_row["id"], now,
                                  seed_bloom, peer_bloom)
      signal = "torrent-changed"

    torrent_row = queries.get_torrent_by_hash(self.conn, torrent)
    glib.idle_add(self.emit, signal, torrent)

    peer_torrent_row = queries.get_peer_torrent_by_peer_and_torrent(self.conn,
                                                 peer_row["id"],
                                                 torrent_row["id"])
    if peer_torrent_row is None:
      queries.add_peer_torrent(self.conn, peer_row["id"], torrent_row["id"],
                               seed, now)
      signal = "peer-torrent-added"
    else:
      queries.set_peer_torrent_updated(self.conn, peer_torrent_row["id"], now)
      signal = "peer-torrent-updated"

    peer_torrent_row = queries.get_peer_torrent_by_peer_and_torrent(self.conn,
                                                 peer_row["id"],
                                                 torrent_row["id"])
    glib.idle_add(self.emit, signal, peer, torrent)

  def close(self):
    pass

  def get_torrent_row(self, hash):
    return queries.get_torrent_by_hash(self.conn, hash)
  def get_peer_row(self, contact):
    return queries.get_peer_by_contact(self.conn, contact)
  def get_peer_by_id(self, id):
    return queries.get_peer(self.conn, id)
  def get_torrent_rows(self):
    return queries.get_all_torrents(self.conn)
  def get_peer_rows(self):
    return queries.get_all_peers(self.conn)
  def get_torrent_peers(self, id, noseed = False):
    if noseed:
      return queries.get_torrent_peers_noseed(self.conn, id)
    else:
      return queries.get_torrent_peers(self.conn, id)
  def get_peer_torrents(self, id):
    return queries.get_peer_torrents(self.conn, id)
  def add_filter(self, filter, hash, seed):
    now = datetime.now()
    row = self.get_torrent_row(hash)
    if row is None:
      return

    if seed:
      queries.add_torrent_filters(row["id"], now, filter, 0)
    else:
      queries.add_torrent_filters(row["id"], now, 0, filter)

    glib.idle_add(self.emit, "torrent-changed", hash)
  def get_magnet(self, hash):
    return "magnet:?urn:btih:{0}".format(hash.get_hex())
