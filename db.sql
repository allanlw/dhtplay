PRAGMA foreign_keys = on;
CREATE TABLE IF NOT EXISTS buckets (
  id INTEGER PRIMARY KEY NOT NULL,
  start BLOB NOT NULL,
  end BLOB NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL
);
CREATE TABLE IF NOT EXISTS nodes (
  id INTEGER PRIMARY KEY NOT NULL,
  hash BLOB NOT NULL,
  contact BLOB NOT NULL,
  bucket_id INTEGER NOT NULL,
  good BOOLEAN NOT NULL,
  pending BOOLEAN NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL,

  FOREIGN KEY(bucket_id) REFERENCES buckets(id)
);
CREATE TABLE IF NOT EXISTS peers (
  id INTEGER PRIMARY KEY NOT NULL,
  contact BLOB UNIQUE NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL
);
CREATE TABLE IF NOT EXISTS torrents (
  id INTEGER PRIMARY KEY NOT NULL,
  hash BLOB UNIQUE NOT NULL,
  created timestamp NOT NULL,
  updated timestamp NOT NULL
);
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
