"""This module contains the default settings that the application needs."""

import ConfigParser
import io

DEFAULTS = """ 
[torrent]
db = :memory:

[view]

[last]
server_host = 0.0.0.0
server_bind_addr = 0.0.0.0
server_bind_port = 6881
server_port = 6881
server_hash = 991b2fa313d425258ae99b7a9841940c0a0bc998
server_upnp = False
ping_host = 
ping_port = 6881
find_host = 
find_port = 6881
find_hash = 
get_peers_host =
get_peers_port = 6881
get_peers_hash =
get_peers_scrape = False
multiple_servers_bind_addr = 0.0.0.0
multiple_servers_serv_addr = 0.0.0.0
multiple_servers_min_port = 6881
multiple_servers_max_port = 6890
multiple_servers_uniform = False
multiple_servers_upnp = False
"""

DEFAULT_CONFIG = ConfigParser.RawConfigParser()
DEFAULT_CONFIG.readfp(io.BytesIO(DEFAULTS))
