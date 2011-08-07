class BloomFilter:
  K = 2
  M = 256 * 8
  def __init__(self):
    self.bloom = [0 for x in range(256)]
  def insert_host(self, host):
    hash = Hash(hashlib.sha1(socket.inet_pton(host.host)).digest()).get_20()

    index1 = ord(hash[0]) | ord(hash[1]) << 8
    index2 = ord(hash[2]) | ord(hash[3]) << 8

    index1 %= self.M
    index2 %= self.M

    self.bloom[index1 / 8] |= 0x01 << (index1 % 8)
    self.bloom[index2 / 8] |= 0x01 << (index2 % 8)
  def get_estimate(self):
    set_bits = 0
    for a in self.bloom:
      b = a & 0b01010101
      c = (a >> 1) & 0b01010101
      d = b+c
      e = d & 0b00110011
      f = (d >> 2) & 0b00110011
      g = e + f
      h = g & 0b00001111
      i = (g >> 4) & 0b00001111
      j = h + i
      set_bits += j
    count = float(min(M-1, M-set_bits))
    size = math.log(count/m) / (K * log(1-1./M))
    return size
  def get_hex(self):
    result = ""
    for b in self.bloom:
      result += "{0:x}".format(b)
    return result
  def get_bin(self):
    result = ""
    for b in self.bloom:
      result += chr(b)
