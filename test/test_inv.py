#!/usr/bin/env python
# test_inv_load
#
# How big might a JSON file for our inventory be?
#
# Begun by Peter L. Evans, June 2013
# <pevans@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

import datetime
import doctest
import json
import os
import tempfile
import uuid  # just for some random strings

def nslc_str(net, sta="---", loc="--", cha="---"):
    """Fixed-width string for a stream"""
    return "%16s" % (".".join([net, sta, loc, cha]))


class InventoryLite():
  def __init__(self, nets, stas, locs, chas):
    """Prepare phony text-based inventory.

    Inputs:
      nets, stas, locs, chas - int, the number of each to create.

    >>> inv = InventoryLite(4, 3, 1, 3)
    >>> print inv
    InventoryLite with 4 net(s)

    >>> inv = InventoryLite(2, 2, 1, 3)
    >>> print len(inv.dump_json())
    Dump_json: InventoryLite with 2 net(s)
    2116
    
    """
    self.inventory = {}
    for n in range(nets):
        net_name = "N%i" % n
        net_attrs = "Network %s description archive shared restricted" % net_name
        s_dict = {}
        for s in range(stas):
            sta_name = "S%02i" % s
            sta_attrs = "Station %s begin end lat lon elev depth etc" % sta_name
            l_dict = {}
            for l in range(locs):
                loc_name = "%1i0" % l  # Don't use more than 10 locids!
                if l == locs-1:
                    # Make sure there's an empty location code:
                    loc_name = ""
                loc_attrs = "begin end lat lon elev depth"
                c_dict = {}
                for c in range(chas):
                    cha_name = "B%02i" % c
                    val1 = uuid.uuid4()
                    val2 = uuid.uuid4()
                    cha_attrs = "%s digitizer %s sensor %s sample rate type etc " % (cha_name, val1, val2)
                    c_dict[cha_name] = (cha_attrs, {})

                l_dict[loc_name] = (loc_attrs, c_dict)
            s_dict[sta_name] = (sta_attrs, l_dict)
        self.inventory[net_name] = (net_attrs, s_dict)

  def __repr__(self):
      return "InventoryLite with %i net(s)" % len(self.inventory)

  def count(self, level):
      """How many objects in inventory?

      >>> inv = InventoryLite(3, 4, 2, 6)
      >>> print inv.count('network')
      3
      >>> print inv.count('station')
      12
      >>> print inv.count('location')
      24
      >>> print inv.count('channel')
      144

      """
      sum = 0
      if level == 'network':
          return len(self.inventory)
      elif level == 'station':
          for n in self.inventory.keys():
            sum += len(self.inventory[n][1])
      elif level == 'location':
          for n in self.inventory.keys():
            s_dict = self.inventory[n][1]
            for s in s_dict.keys():
              sum += len(s_dict[s][1])
      elif level == 'channel':
          for n in self.inventory.keys():
            s_dict = self.inventory[n][1]
            for s in s_dict.keys():
              l_dict = s_dict[s][1]
              for l in l_dict.keys():
                sum += len(l_dict[l][1])
      return sum

  def dump_json(self, indent=None):
      print "Dump_json:", self.__repr__()
      return json.dumps(self.inventory, indent=indent)

  def load_json(self, fid):
      """Deserialise to inventory.

      Inputs:
         fid - file-like object containing a JSON document.
         
      No checking!
      """
      tmp = json.load(fid)
      if len(tmp) > 0:
        self.inventory = tmp
      return
    
  def dump(self):
      """Does lots of sorting."""

      result = ""
      crlf = "\n"
      for n in sorted(self.inventory.keys()):
          net = self.inventory[n]
          result += nslc_str(n) + "Network: " + net[0] + crlf
          s_dict = net[1]
          for s in sorted(s_dict.keys()):
              sta = s_dict[s]
              result += nslc_str(n, s) + "Station: " + sta[0] + crlf
              l_dict = sta[1]
              for l in sorted(l_dict.keys()):
                  loc = l_dict[l]
                  result += nslc_str(n, s, l) + "Location:" + loc[0] + crlf
                  c_dict = loc[1]
                  for c in sorted(c_dict.keys()):
                       cha = c_dict[c]
                       result += nslc_str(n, s, l, c) + "Channel:" + cha[0] + crlf
      return result


if __name__ == '__main__':
    doctest.testmod()
    inv = InventoryLite(150, 40, 3, 12)
    print inv
    print "Networks:", inv.count('network')
    print "Stations:", inv.count('station')
    print "Locations:", inv.count('location')
    print "Channels:", inv.count('channel')


    #fid = tempfile.TemporaryFile()

    filename = 'test_inv.json'

    # Write out...
    t_start = datetime.datetime.now()
    fid = open(filename, 'w')
    print >>fid, inv.dump_json(indent = None)
    fid.close()
    print "Dump took", datetime.datetime.now() - t_start
    print "Dump file is", os.stat(filename).st_size, "bytes."

    # Read back in...
    t_start = datetime.datetime.now()
    fid = open(filename, 'r')
    inv = InventoryLite(0, 0, 0, 0)
    inv.load_json(fid)
    print "Restore took", datetime.datetime.now() - t_start
    print "Networks:", inv.count('network')
    print "Stations:", inv.count('station')
    print "Locations:", inv.count('location')
    print "Channels:", inv.count('channel')

