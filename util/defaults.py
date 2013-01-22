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
