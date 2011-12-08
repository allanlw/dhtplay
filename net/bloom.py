"""This module contains the bloom filter implementation."""
import hashlib
import math
import sqlite3
import operator

from net.sha1hash import Hash

class BloomFilter:
  """Bloom filter implemented to BEP_0033 spec."""
  K = 2
  M = 256 * 8
  def __init__(self, filter1=None, filter2=None):
    if filter1 is None and filter2 is None:
      self.bloom = [0 for x in range(self.M/8)]
    elif filter2 is None:
      self.bloom = []
      if isinstance(filter1, BloomFilter):
        self.bloom[:] = filter1.bloom[:]
      elif len(filter1) == (self.M/8):
        for b in filter1:
          self.bloom.append(ord(b))
      elif len(filter1) == (self.M/8)*2:
        for x in range(0, 64, 2):
          self.bloom.append(int(filter1[x:x+1], 16))
    else:
      filter1 = BloomFilter(filter1)
      filter2 = BloomFilter(filter2)
      self.bloom = [filter1.bloom[x] | filter2.bloom[x]
                      for x in range(len(filter1.bloom))]
  def insert_host(self, host):
    hash = Hash(hashlib.sha1(host.get_packed_host()).digest()).get_20()

    index1 = ord(hash[0]) | (ord(hash[1]) << 8)
    index2 = ord(hash[2]) | (ord(hash[3]) << 8)

    index1 %= self.M
    index2 %= self.M

    self.bloom[index1 / 8] |= 0x01 << (index1 % 8)
    self.bloom[index2 / 8] |= 0x01 << (index2 % 8)

    self.bloom[index1 / 8] &= 0xFF
    self.bloom[index2 / 8] &= 0xFF
  def count_zero_bits(self):
    return reduce(operator.add,
                  ("{0:08b}".format(x).count('0') for x in self.bloom))
  def get_estimate(self):
    c = float(min(self.M-1, self.count_zero_bits()))
    try:
      size = math.log(c/self.M) / (self.K * math.log1p(-1./self.M))
    except ValueError:
      size = 0
    return size
  def get_hex(self):
    result = ""
    for b in self.bloom:
      result += "{0:02x}".format(b)
    return result
  def get_bin(self):
    return buffer("".join(chr(b) for b in self.bloom))
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
  for i in range(255+1):
    b.insert_host(ContactInfo("192.0.2.{0}".format(i)))
  for i in range(0x3E7+1):
    b.insert_host(ContactInfo("2001:DB8::{0:x}".format(i)))
  print b.get_hex()
  print b.get_estimate()

  print int(b.get_hex(),16) == int("""F6C3F5EAA07FFD91BDE89F777F26FB2BFF37BDB8FB2BBAA2FD3DDDE7BACFFF75EE7CCBAEFE5EEDB1FBFAFF67F6ABFF5E43DDBCA3FD9B9FFDF4FFD3E9DFF12D1BDF59DB53DBE9FA5B7FF3B8FDFCDE1AFB8BEDD7BE2F3EE71EBBBFE93BCDEEFE148246C2BC5DBFF7E7EFDCF24FD8DC7ADFFD8FFFDFDDFFF7A4BBEEDF5CB95CE81FC7FCFF1FF4FFFFDFE5F7FDCBB7FD79B3FA1FC77BFE07FFF905B7B7FFC7FEFEFFE0B8370BB0CD3F5B7F2BD93FEB4386CFDD6F7FD5BFAF2E9EBFFFFEECD67ADBF7C67F17EFD5D75EBA6FFEBA7FFF47A91EB1BFBB53E8ABFB5762ABE8FF237279BFEFBFEEF5FFC5FEBFDFE5ADFFADFEE1FB737FFFFBFD9F6AEFFEEE76B6FD8F72EF""", 16)
