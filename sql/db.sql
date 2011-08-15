/* This SQL script for SQLite generates the tables for DHTPlay.
 * It depends upon custom types that are registered by the python connection.
 */
PRAGMA foreign_keys = on;

CREATE TABLE IF NOT EXISTS buckets (
  id INTEGER PRIMARY KEY NOT NULL,
  start sha1hash NOT NULL,
  end sha1hash NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
  id INTEGER PRIMARY KEY NOT NULL,
  hash sha1hash UNIQUE NOT NULL,
  contact contactinfo UNIQUE NOT NULL,
  bucket_id INTEGER NOT NULL,
  good BOOLEAN NOT NULL,
  pending BOOLEAN NOT NULL,
  version BLOB NULL,
  received INTEGER NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL,

  FOREIGN KEY(bucket_id) REFERENCES buckets(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS nodes_hash ON nodes(hash);
CREATE UNIQUE INDEX IF NOT EXISTS nodes_contact ON nodes(contact);
CREATE INDEX IF NOT EXISTS nodes_bucket_id ON nodes(bucket_id);

CREATE TABLE IF NOT EXISTS peers (
  id INTEGER PRIMARY KEY NOT NULL,
  contact contactinfo UNIQUE NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS peers_contact ON peers(contact);

CREATE TABLE IF NOT EXISTS torrents (
  id INTEGER PRIMARY KEY NOT NULL,
  hash sha1hash UNIQUE NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL,
  seeds bloom NOT NULL,
  peers bloom NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS torrents_hash ON torrents(hash);

CREATE TABLE IF NOT EXISTS peer_torrents (
  id INTEGER PRIMARY KEY NOT NULL,
  peer_id INTEGER NOT NULL,
  torrent_id INTEGER NOT NULL,
  seed BOOLEAN NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL,

  FOREIGN KEY(peer_id) REFERENCES peers(id),
  FOREIGN KEY(torrent_id) REFERENCES torrents(id)
);
CREATE INDEX IF NOT EXISTS peer_torrents_peer_id ON peer_torrents(peer_id);
CREATE INDEX IF NOT EXISTS peer_torrents_torrent_id ON peer_torrents(torrent_id);
