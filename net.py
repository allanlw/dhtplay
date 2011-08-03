import socket

class Hash:
  def __init__(self, id):
    self.id = id
    if isinstance(self.id, (basestring, buffer)):
      if len(self.id) > 20:
        self.id = int(self.id, 16)
      else:
        id = self.id
        while len(id) < 20:
          id = "\0" + id
        self.id = 0
        for c in id:
          self.id = self.id << 8
          self.id += ord(c)
    elif isinstance(self.id, Hash):
      self.id = id.id
  def get_hex(self):
    return "{0:x}".format(self.id)
  def get_20(self):
    id = self.id
    result = ""
    while id != 0:
      result = chr(id % 256) + result
      id = id >> 8
    while len(result) < 20:
      result = "\0" + result
    return buffer(result)
  def get_int(self):
    return self.id
  def __int__(self):
    return self.get_int()
  def __str__(self):
    return self.get_20()
  def __long__(self):
    return self.get_int()
  def distance(self, other):
    return self.get_int() ^ other.get_int()

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

