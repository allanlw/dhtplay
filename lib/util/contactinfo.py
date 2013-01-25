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

"""contains a class for representing internet address + port combinations."""
import socket
import sqlite3

class ContactInfo:
  """Represents an internet address + port combination."""
  def __init__(self, addr, port=None):
    if isinstance(addr, ContactInfo):
      self.host = addr.host
      self.port = addr.port
      return
    if port is None:
      if len(addr) == 6:
        port = addr[4:6]
        addr = addr[0:4]
      elif len(addr) == 18:
        port = addr[16:18]
        addr = addr[0:16]
      else:
        raise ValueError("Unknown combined addr+port format.")
    if len(addr) == 4:
      self.host = socket.inet_ntop(socket.AF_INET, addr)
    elif (len(addr) == 16 and
          not all(x.isdigit() and x == ":" for x in addr)):
      self.host = socket.inet_ntop(socket.AF_INET6, addr)
    else:
      self.host = addr
    if isinstance(port, (buffer, basestring)):
      self.port = (ord(port[0]) << 8) + ord(port[1])
    else:
      self.port = port
  def get_tuple(self):
    """Returns a tuple of (addr, port) (e.g. for raw socket communication)"""
    return self.host, self.port
  def get_packed(self):
    """Returns a BEP_0005 'packed' representation of the addr+port."""
    result = self.get_packed_host()
    result += chr(self.port >> 8) + chr(self.port % 256)
    return buffer(result)
  def get_packed_host(self):
    """Returns a BEP_0005 'packed' representation of the addr."""
    try:
      result = socket.inet_pton(socket.AF_INET, self.host)
    except (ValueError, socket.error):
      result = socket.inet_pton(socket.AF_INET6, self.host)
    return buffer(result)
  def __str__(self):
    return "{0}:{1}".format(self.host, self.port)
  def __conform__(self, protocol):
    if protocol is sqlite3.PrepareProtocol:
      return self.get_packed()
