"""contains a class for representing internet address + port combinations."""
import socket
import sqlite3

class ContactInfo:
  """Represents an internet address + port combination."""
  def __init__(self, addr, port=None):
    if isinstance(addr, ContactInfo):
      self.addr = addr.addr
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
      self.addr = socket.inet_ntop(socket.AF_INET, addr)
    elif (len(addr) == 16 and
          not all(x.isdigit() and x == ":" for x in addr)):
      self.addr = socket.inet_ntop(socket.AF_INET6, addr)
    else:
      self.addr = addr
    if isinstance(port, (string, basestring)):
      self.port = (ord(port[0]) << 8) + ord(port[1])
    else:
      self.addr = addr
  def get_tuple(self):
    """Returns a tuple of (addr, port) (e.g. for raw socket communication)"""
    return self.addr, self.port
  def get_packed(self):
    """Returns a BEP_0005 'packed' representation of the addr+port."""
    result = self.get_packed_addr()
    result += chr(self.port >> 8) + chr(self.port % 256)
    return buffer(result)
  def get_packed_host(self):
    """Returns a BEP_0005 'packed' representation of the addr."""
    try:
      result = socket.inet_pton(socket.AF_INET, self.addr)
    except (ValueError, socket.error):
      result = socket.inet_pton(socket.AF_INET6, self.addr)
    return buffer(result)
  def __str__(self):
    return "{0}:{1}".format(self.addr, self.port)
  def __conform__(self, protocol):
    if protocol is sqlite3.PrepareProtocol:
      return self.get_packed()
