"""Test for the bloom filter implementation."""
import unittest

from util.bloom import BloomFilter
from util.contactinfo import ContactInfo

class TestBloomFilter(unittest.TestCase):
  def setUp(self):
    self.b = BloomFilter()
    for i in range(255+1):
      self.b.insert_host(ContactInfo("192.0.2.{0}".format(i), 80))
    for i in range(0x3E7+1):
      self.b.insert_host(ContactInfo("2001:DB8::{0:x}".format(i), 80))
  def test_hex(self):
    self.assertEqual(self.b.get_hex().lower(),(
        "F6C3F5EAA07FFD91BDE89F777F26FB2BFF37BDB8FB2BBAA2FD3DDDE7BACFFF75" +
        "EE7CCBAEFE5EEDB1FBFAFF67F6ABFF5E43DDBCA3FD9B9FFDF4FFD3E9DFF12D1B" +
        "DF59DB53DBE9FA5B7FF3B8FDFCDE1AFB8BEDD7BE2F3EE71EBBBFE93BCDEEFE14" +
        "8246C2BC5DBFF7E7EFDCF24FD8DC7ADFFD8FFFDFDDFFF7A4BBEEDF5CB95CE81F" +
        "C7FCFF1FF4FFFFDFE5F7FDCBB7FD79B3FA1FC77BFE07FFF905B7B7FFC7FEFEFF" +
        "E0B8370BB0CD3F5B7F2BD93FEB4386CFDD6F7FD5BFAF2E9EBFFFFEECD67ADBF7" +
        "C67F17EFD5D75EBA6FFEBA7FFF47A91EB1BFBB53E8ABFB5762ABE8FF237279BF" +
        "EFBFEEF5FFC5FEBFDFE5ADFFADFEE1FB737FFFFBFD9F6AEFFEEE76B6FD8F72EF"
        ).lower())

if __name__ == "__main__":
  print unittest.main()
