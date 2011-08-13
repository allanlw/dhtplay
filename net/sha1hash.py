import math
import sqlite3

class Hash:
  def __init__(self, id):
    self.id = id
    if isinstance(self.id, (basestring, buffer)):
      if len(self.id) > 20:
        try:
          self.id = int(self.id, 16)
        except ValueError:
          raise ValueError("Invalid ID (len {0}, not hex)", len(self.id))
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
    return "{0:040x}".format(self.id)
  def get_20(self):
    id = self.id
    result = ""
    while id != 0:
      result = chr(id % 256) + result
      id = id >> 8
    while len(result) < 20:
      result = "\x00" + result
    return buffer(result)
  def get_int(self):
    return self.id
  def __int__(self):
    return self.get_int()
  def __str__(self):
    return self.get_hex()
  def __long__(self):
    return self.get_int()
  def distance(self, other):
    return self.get_int() ^ other.get_int()
  def get_pow(self):
    try:
      return math.log(self.get_int(), 2)
    except ValueError:
      return 0
  def __conform__(self, protocol):
    if protocol is sqlite3.PrepareProtocol:
      return self.get_20()
