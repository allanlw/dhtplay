import hashlib
import math
import sqlite3

from sha1hash import Hash

class BloomFilter:
  K = 2
  M = 256 * 8
  def __init__(self, filter1=None, filter2=None):
    if filter1 is None and filter2 is None:
      self.bloom = [0 for x in range(256)]
    elif filter2 is None:
      self.bloom = []
      if isinstance(filter1, BloomFilter):
        self.bloom = filter1.bloom[:]
      elif len(filter1) == 32:
        for b in filter1:
          self.bloom.append(ord(b))
      elif len(filter1) == 64:
        for x in range(0, 64, 2):
          self.bloom.append(int(filter1[x:x+1], 16))
    else:
      filter1 = BloomFilter(filter1)
      filter2 = BloomFilter(filter2)
      self.bloom = [filter1.bloom[x] | filter2.bloom[x] for x in range(256)]
  def insert_host(self, host):
    hash = Hash(hashlib.sha1(host.get_packed_host()).digest()).get_20()

    index1 = ord(hash[0]) | (ord(hash[1]) << 8)
    index2 = ord(hash[2]) | (ord(hash[3]) << 8)

    index1 %= self.M
    index2 %= self.M

    self.bloom[index1 / 8] |= 0x01 << (index1 % 8)
    self.bloom[index2 / 8] |= 0x01 << (index2 % 8)

    self.bloom[index1 / 8] %= 0xFF
    self.bloom[index2 / 8] %= 0xFF
  def count_zero_bits(self):
    zero_bits = 0
    for a in self.bloom:
      zero_bits += "{0:08b}".format(a).count('0')
    return zero_bits
  def get_estimate(self):
    c = float(min(self.M-1, self.count_zero_bits()))
    size = math.log(c/self.M) / (self.K * math.log(1 - 1./self.M))
    return size
  def get_hex(self):
    result = ""
    for b in self.bloom:
      result += "{0:02x}".format(b)
    return result
  def get_bin(self):
    result = ""
    for b in self.bloom:
      result += chr(b)
    return buffer(result)
  def __str__(self):
    return str(self.get_bin())
  def __or__(self, other):
    return BloomFilter(self, other)
  def __conform__(self, protocol):
    if protocol is sqlite3.PrepareProtocol:
      return self.get_bin()

if __name__ == "__main__":
  from contactinfo import ContactInfo
  b = BloomFilter()
  print b.get_hex()
  print b.count_zero_bits()
  print b.get_estimate()
  for i in range(255):
    b.insert_host(ContactInfo("192.0.2.{0}".format(i)))
  for i in range(0x3E7):
    b.insert_host(ContactInfo("2001:DB8::{0:x}".format(i)))
  print b.get_hex()
  print b.get_estimate()
