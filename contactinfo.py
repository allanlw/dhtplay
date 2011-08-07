import socket

class ContactInfo:
  def __init__(self, host, port=None):
    if port is None and len(host) == 6:
      port = host[4:6]
      host = host[0:4]
    self.host = host
    if self.host and len(self.host) == 4:
      self.host = socket.inet_ntoa(self.host)
    self.port = port
    if isinstance(self.port, basestring):
      self.port = (ord(self.port[0]) << 8) + ord(self.port[1])
  def get_tuple(self):
    return self.host, self.port
  def get_packed(self):
    result = socket.inet_pton(socket.AF_INET, self.host)
    result += chr(self.port >> 8) + chr(self.port % 256)
    return buffer(result)
  def __str__(self):
    return "{0}:{1}".format(self.host, self.port)
