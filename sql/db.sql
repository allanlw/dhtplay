/* This SQL script for SQLite generates the tables for DHTPlay.
 * It depends upon custom types that are registered by the python connection.
 * The types are as follows:
 *   * sha1hash corresponds to the Hash class in net.sha1hash. It is stored
 *     as a 20 byte binary BLOB.
 *   * contactinfo corresponds to the ContactInfo class in net.contactinfo.
 *     It is stored as a 6/20 byte binary BLOB depending on the IP version.
 *   * bloom corresponds to the Bloom class in net.bloom. It is stored as a
 *     256 byte binary BLOB.
 */
PRAGMA foreign_keys = on;

CREATE TABLE IF NOT EXISTS servers (
  id INTEGER PRIMARY KEY NOT NULL,
  hash sha1hash UNIQUE NOT NULL,
  bind contactinfo UNIQUE NOT NULL,
  host contactinfo NULL,
  upnp BOOLEAN NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS servers_hash ON servers(hash);
CREATE UNIQUE INDEX IF NOT EXISTS servers_bind ON servers(bind);

CREATE TABLE IF NOT EXISTS buckets (
  id INTEGER PRIMARY KEY NOT NULL,
  server_id INTEGER NOT NULL,
  start sha1hash NOT NULL,
  end sha1hash NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL,

  FOREIGN KEY(server_id) REFERENCES servers(id)
);
CREATE INDEX IF NOT EXISTS buckets_server_id ON buckets(server_id);

CREATE TABLE IF NOT EXISTS nodes (
  id INTEGER PRIMARY KEY NOT NULL,
  hash sha1hash NOT NULL,
  contact contactinfo NOT NULL,
  bucket_id INTEGER NOT NULL,
  good BOOLEAN NOT NULL,
  pending BOOLEAN NOT NULL,
  version BLOB NULL,
  received INTEGER NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL,

  FOREIGN KEY(bucket_id) REFERENCES buckets(id)
);
CREATE INDEX IF NOT EXISTS nodes_hash ON nodes(hash);
CREATE INDEX IF NOT EXISTS nodes_contact ON nodes(contact);
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
