import socket
import sqlite3

class ContactInfo:
  def __init__(self, host, port=None):
    if isinstance(host, ContactInfo):
      self.host = host.host
      self.port = host.port
      return
    if port is None:
      if len(host) == 6:
        port = host[4:6]
        host = host[0:4]
      elif len(host) == 18:
        port = host[16:18]
        host = host[0:16]
    self.host = host
    if len(self.host) == 4:
      self.host = socket.inet_ntop(socket.AF_INET, self.host)
    elif (len(self.host) == 16 and
          any(not x.isdigit() or x is not ":" for x in self.host)):
      self.host = socket.inet_ntop(socket.AF_INET6, self.host)
    self.port = port
    if isinstance(self.port, basestring):
      self.port = (ord(self.port[0]) << 8) + ord(self.port[1])
  def get_tuple(self):
    return self.host, self.port
  def get_packed(self):
    result = self.get_packed_host()
    result += chr(self.port >> 8) + chr(self.port % 256)
    return buffer(result)
  def get_packed_host(self):
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
