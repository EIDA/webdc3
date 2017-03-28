#!/usr/bin/env python
#
# Stand-alone manager for web interface testing.
#
# Begun by GEOFON team, July 2012
# <pevans@gfz-potsdam.de>
#
# Copyright (C) 2012 GEOFON team, Helmholtz-Zentrum Potsdam - Deutsches GeoForschungsZentrum GFZ
# ----------------------------------------------------------------------

import datetime
import os
import sys
import wsgiref

sys.path.append(os.path.join('..', 'wsgi'))  # for wsgicomm
sys.path.append(os.path.join('..', 'wsgi', 'module'))


import argparse   # New in Python version 2.7
parser = argparse.ArgumentParser(description="Start stand-alone web interface for testing.")
parser.add_argument("-p", "--port", type=int, nargs=1, dest="port", help="listen on PORT") 

try:
    import webinterface
    have_seiscomp3 = True
except ImportError:
    import webinterface_no_sc3 as webinterface
    have_seiscomp3 = False


if __name__ == '__main__':
    args = parser.parse_args()
    print args
    try:
    	port = int(args.port[0])
    except:
        port = 8008
    proto = "http://"
    host = 'localhost'
    hostport = '%s:%i' % (host, port)
    print "Starting wsgiref on port %(p)i" % {'p': port}

    print "About me:"
    print str(webinterface.wi)

    print "\nEVENTS"
    print "%s%s/event/catalogs" % (proto, hostport)
    print "%s%s/event/geofon?maxlat=-20" % (proto, hostport)
    print "%s%s/event/comcat?start=%s" % (proto, hostport, datetime.date.today())
    print "%s%s/event/meteor" % (proto, hostport)

    print "\nMETADATA"
    print "%s%s/metadata/networktypes" % (proto, hostport)
    print "%s%s/metadata/sensortypes" % (proto, hostport)

    from wsgiref.simple_server import make_server
    srv = make_server(host, port, webinterface.application)
    srv.serve_forever()
