"""Contains a class Hash for representing sha1 hashes."""
import math
import sqlite3

class Hash:
  """Represents a 160 byte (SHA1) hash."""
  def __init__(self, raw_hash):
    self.id = raw_hash
    if isinstance(self.id, (basestring, buffer)):
      if len(self.id) > 20:
        try:
          self.id = int(self.id, 16)
        except ValueError:
          raise ValueError("Invalid ID (len {0}, not hex)", len(self.id))
      else:
        while len(self.id) < 20:
          self.id = "\x00" + self.id
        raw_hash = self.id
        self.id = 0
        for char in raw_hash:
          self.id = self.id << 8
          self.id += ord(char)
    elif isinstance(self.id, Hash):
      self.id = self.id.id
  def get_hex(self):
    """Returns a 40 character lowercase hex representation of the hash."""
    return "{0:040x}".format(self.id)
  def get_20(self):
    """Returns a 20 character 'packed' binary representation of the hash."""
    raw_hash = self.id
    result = ""
    while raw_hash != 0:
      result = chr(raw_hash & 0xFF) + result
      raw_hash = raw_hash >> 8
    while len(result) < 20:
      result = "\x00" + result
    return buffer(result)
  def get_int(self):
    """Returns an integer representation of the hash."""
    return self.id
  def __int__(self):
    return self.get_int()
  def __str__(self):
    return self.get_hex()
  def __long__(self):
    return self.get_int()
  def distance(self, other):
    """Returns the exclusive or disteance between this and another hash."""
    return self.get_int() ^ other.get_int()
  def get_pow(self):
    """Returns log(hash)/log(2)."""
    try:
      return math.log(self.get_int(), 2)
    except ValueError:
      return 0
  def __conform__(self, protocol):
    if protocol is sqlite3.PrepareProtocol:
      return self.get_20()
