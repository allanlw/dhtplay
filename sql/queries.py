"""Contains functions for doing all those pesky SQL queries."""

# DHT Queries (nodes/buckets)

def get_num_buckets(conn, id) :
  r = conn.select_one("""SELECT COUNT(*) FROM buckets
                         WHERE server_id=?""", (id,))
  return r[0]

def create_bucket(conn, start, end, time, server_id):
  return conn.insert("""INSERT INTO buckets(id, start, end, created, updated,
                        server_id) VALUES(NULL, ?, ?, ?, ?, ?)""",
                     (start, end, time, time, server_id))

def create_node(conn, hash, contact, bucket, good, pending, version, received,
                time):
  return conn.insert("""INSERT INTO nodes(id, hash, contact, bucket_id, good,
                        pending, version, received, created, updated) VALUES
                        (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (hash, contact, bucket, good, pending, version,
                       received, time, time))

def set_bucket_updated(conn, id, time):
  conn.execute("UPDATE buckets SET updated=? WHERE id=?",
               (time, id))

def delete_node(conn, id):
  conn.execute("DELETE FROM nodes WHERE id=?", (id,))

def get_num_nodes_in_bucket(conn, id):
  r = conn.select_one("SELECT COUNT(*) FROM nodes WHERE bucket_id=?", (id,))
  return r[0]

def get_nodes_in_bucket(conn, id):
  return conn.select("SELECT * FROM nodes WHERE bucket_id=?", (id,))

def get_non_pending_nodes_in_bucket(conn, id):
  return conn.select("""SELECT * FROM nodes WHERE bucket_id=? AND NOT pending
                        ORDER BY updated ASC""", (id,))

def set_bucket_end(conn, id, end, time):
  conn.execute("UPDATE buckets SET end=?, updated=? WHERE id=?",
               (end, time, id))

def set_node_bucket(conn, node_id, bucket_id):
  conn.execute("UPDATE nodes SET bucket_id=? WHERE id=?",
               (bucket_id, node_id))

def get_node_by_hash(conn, server_id, hash):
  return conn.select_one("""SELECT nodes.* FROM nodes INNER JOIN buckets ON
                            nodes.bucket_id=buckets.id WHERE nodes.hash=? AND
                            buckets.server_id=? LIMIT 1""", (hash, server_id))

def get_node_by_contact(conn, server_id, contact):
  return conn.select_one("""SELECT nodes.* FROM nodes INNER JOIN buckets ON
                            nodes.bucket_id=buckets.id WHERE nodes.contact=?
                            AND buckets.server_id=? LIMIT 1""",
                         (contact, server_id))

def set_node_updated(conn, id, time, version, received):
  conn.execute("""UPDATE nodes SET updated=?, version=?, received=received+?
                  WHERE id=?""", (time, version, received, id))

def get_bucket_for_hash(conn, server_id, hash):
  return conn.select_one("""SELECT * FROM buckets WHERE start<=? AND end>? AND
                            server_id=? LIMIT 1""", (hash, hash, server_id))

def get_bucket(conn, id):
  return conn.select_one("SELECT * FROM buckets WHERE id=? LIMIT 1", (id,))

def get_nodes_in_server(conn, id):
  return conn.select("""SELECT nodes.* FROM nodes INNER JOIN buckets ON
                        buckets.id=nodes.bucket_id WHERE
                        buckets.server_id=?""", (id,))

def get_buckets_in_server(conn, id):
  return conn.select("SELECT * FROM buckets WHERE server_id=?", (id,))

def get_pending_nodes_in_server(conn, id):
  return conn.select("""SELECT nodes.* FROM nodes INNER JOIN buckets ON
                        buckets.id=nodes.bucket_id WHERE nodes.pending AND
                        buckets.server_id=?""", (id,))

def set_node_pending(conn, id, pending, time):
  conn.execute("UPDATE nodes SET pending=?,updated=? WHERE id=?",
               (pending, time, id))

def get_random_node_in_bucket(conn, id):
  return conn.select_one("""SELECT * FROM nodes WHERE bucket_id=? AND NOT
                            pending ORDER BY random() LIMIT 1""", (id,))

def get_closest_nodes(conn, server_id, hash, number):
  return conn.select("""SELECT nodes.* FROM nodes INNER JOIN buckets ON
                        buckets.id=nodes.bucket_id WHERE buckets.server_id=?
                        ORDER BY xor(nodes.hash, ?) ASC LIMIT ?""",
                     (server_id, hash, number))

# TORRENT Queries (peers/torrents)

def get_peer(conn, id):
  return conn.select_one("SELECT * FROM peers WHERE id=? LIMIT 1", (id,))

def get_all_torrents(conn):
  return conn.select("SELECT * FROM torrents")

def get_all_peers(conn):
  return conn.select("SELECT * FROM peers")

def get_peer_by_contact(conn, contact):
  return conn.select_one("SELECT * FROM peers WHERE contact=? LIMIT 1",
                         (contact,))

def add_peer(conn, contact, time):
  return conn.insert("INSERT INTO peers VALUES (NULL, ?, ?, ?)",
                     (contact, time, time))

def set_peer_updated(conn, id, time):
  conn.execute("UPDATE peers SET updated=? WHERE id=?", (time, id))

def get_torrent_by_hash(conn, hash):
  return conn.select_one("SELECT * FROM torrents WHERE hash=? LIMIT 1",
                         (hash,))

def add_torrent(conn, hash, time, seed_bloom, peer_bloom):
  return conn.insert("INSERT INTO torrents VALUES (NULL, ?, ?, ?, ?, ?)",
                     (hash, time, time, seed_bloom, peer_bloom))

def set_torrent_filters(conn, id, time, seed_bloom, peer_bloom):
  conn.execute("UPDATE torrents SET updated=?,seeds=?,peers=? WHERE id=?",
               (time, seed_bloom, peer_bloom, id))

def add_torrent_filters(conn, id, time, seed_bloom, peer_bloom):
  conn.execute("""UPDATE torrents SET updated=?,seeds=seeds|?,peers=peers|?
                   WHERE id=?""", (time, seed_bloom, peer_bloom, id))

def get_peer_torrent_by_peer_and_torrent(conn, peer, torrent):
  return conn.select_one("""SELECT * FROM peer_torrents WHERE peer_id=? AND
                            torrent_id=? LIMIT 1""", (peer, torrent))

def add_peer_torrent(conn, peer, torrent, seed, time):
  return conn.insert("INSERT INTO peer_torrents VALUES(NULL,?,?,?,?,?)",
                     (peer, torrent, seed, time, time))

def set_peer_torrent_updated(conn, id, time):
  conn.execute("UPDATE peer_torrents SET updated=? WHERE id=?",
               (time, id))

def get_torrent_peers_noseed(conn, id):
  return conn.select("""SELECT peer_id FROM peer_torrents 
                        WHERE torrent_id=? AND NOT seed""", (id,))

def get_torrent_peers(conn, id):
  return conn.select("SELECT peer_id FROM peer_torrents WHERE torrent_id=?",
                     (id,))

def get_peer_torrents(conn, id):
  return conn.select("SELECT torrent_id FROM peer_torrents WHERE peer_id=?",
                     (id,))

# SERVER queries

def get_servers(conn):
  return conn.select("SELECT * FROM SERVERS")

def add_server(conn, hash, bind, host, upnp):
  return conn.insert("""INSERT INTO servers(hash, bind, host, upnp)
                        VALUES (?, ?, ?, ?)""",
                     (hash, bind, host, upnp))

def get_server_by_hash(conn, hash):
  return conn.select_one("SELECT * FROM servers WHERE hash=?", (hash,))

def get_server_by_bind(conn, bind):
  return conn.select_one("SELECT * FROM servers WHERE bind=?", (bind,))
