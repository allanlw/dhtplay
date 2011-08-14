"""This module contains the default settings that the application needs."""

import ConfigParser
import io

defaults = """ 
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
"""

default_config = ConfigParser.RawConfigParser()
default_config.readfp(io.BytesIO(defaults))
