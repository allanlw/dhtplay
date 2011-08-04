# FreeBencode v0.1
# 
# This is a simple bencode/bdecode python module that I wrote because
# I wasn't happy with the license of the official bittorrent one.
# There might be a newer version on my site at allanwirth.com.
# 
# Copyright (C) 2011 by Allan Wirth <allanlw@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""FreeBencode:A simple, lightweight bencode/bdecode library."""

class BencodeError(StandardError):
  pass

def bencode(obj):
  if isinstance(obj, (int, long)):
    return bencode_int(obj)
  elif isinstance(obj, (basestring, buffer)):
    return bencode_string(obj)
  elif isinstance(obj, (list, tuple)):
    return bencode_list(obj)
  elif isinstance(obj, dict):
    return bencode_dict(obj)
  else:
    raise BencodeError("not int, string, dict or list/tuple.")

def bencode_int(obj):
  return "i{0:-d}e".format(obj)

def bencode_string(obj):
  return "{0:d}:{1:s}".format(len(obj), obj)

def bencode_list(obj):
  return "l{0:s}e".format("".join((bencode(x) for x in obj)))

def bencode_dict(obj):
  keys = obj.keys()[:]
  keys.sort()
  return "d{0:s}e".format("".join((bencode(k)+bencode(obj[k]) for k in keys)))

def bdecode(str):
  if len(str) == 0:
    raise BencodeError("Empty String")
  c = str[0]
  if c == 'i':
    return bdecode_int(str)
  elif c == 'l':
    return bdecode_list(str)
  elif c == 'd':
    return bdecode_dict(str)
  elif c.isdigit():
    return bdecode_string(str)
  else:
     raise BencodeError("not bencoded int, string, dict or list.")

def bdecode_int(str):
  if str[0] != 'i':
    raise BencodeError("not bencoded int.")
  parts = str.partition("e")
  if not parts[2]:
    raise BencodeError("bencoded int doesn't terminate.")
  return int(parts[0][1:]), parts[2]

def bdecode_string(str):
  parts = str.partition(":")
  if not parts[2]:
    raise BencodeError("not bencoded str.")
  elif len(parts[2]) < int(parts[0]):
    raise BencodeError("too short bencoded str len.")
  return parts[2][0:int(parts[0])], parts[2][int(parts[0]):]

def bdecode_list(str):
  if str[0] != 'l':
    raise BencodeError("not bencoded list.")
  leftovers = str[1:]
  result = []
  while leftovers and leftovers[0] != 'e':
    res = bdecode(leftovers)
    result.append(res[0])
    leftovers = res[1]
  if not leftovers:
    raise BencodeError("list does not terminate.")
  return result, leftovers[1:]

def bdecode_dict(str):
  if str[0] != 'd':
    raise BencodeError("not bencoded dict.")
  leftovers = str[1:]
  result = {}
  while leftovers and leftovers[0] != 'e':
    res1 = bdecode(leftovers)
    res2 = bdecode(res1[1])
    if not isinstance(res1[0], basestring):
      raise BencodeError("dict key isn't string.")
    result[res1[0]] = res2[0]
    leftovers = res2[1]
  if not leftovers:
    raise BencodeError("dict doesn't terminate.")
  return result, leftovers[1:]
