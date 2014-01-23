# ----------------------------------------------------------------------
#!/usr/bin/env python
#
# A script to query the webdc3 web service for events.
# This is a "back-door" sort of approach which we may
# not offer in future.
#
# Begun by Peter L. Evans, Dec 2013
# <pevans@gfz-potsdam.de>
#
# Do not redistribute yet.
#
# ----------------------------------------------------------------------
import argparse
import textwrap
import urllib


# Which event catalog should be used?
# Choose one of "geofon" or "emsc" or "comcat".
# The complete list is available at:
# http://eida.gfz-potsdam.de/webdc3/wsgi/event/catalogs

service = "geofon"
base_url = "http://eida.gfz-potsdam.de/webdc3/wsgi/event"

def show_usage():
    print "Usage: $sys.argv[0] "
    print "Query the webdc3 web service for events."
    print "Options: use '-h'."
    print "TBD"


def get_constraints():
    """Parse the command line args to set some restrictions."""

    epilog = textwrap.dedent('''\
A commandline front end to the web interface at
%s

Example: "./webinterfaceEvent.py --maxlon 150 --minlon 90 --maxlat -15 --minlat -45"
  requests some recent events near Australia.''' % base_url)

    parser = argparse.ArgumentParser(description='Query the webdc3 web service for events.',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=epilog)
    parser.add_argument('--maxlat', dest='maxlat', type=float, action='store', default=None,
                        help='Maximum latitude for events')
    parser.add_argument('--minlat', dest='minlat', type=float, action='store', default=None,
                        help='Minimum latitude for events')
    parser.add_argument('--maxlon', dest='maxlon', type=float, action='store', default=None,
                        help='Maximum longitude for events')
    parser.add_argument('--minlon', dest='minlon', type=float, action='store', default=None,
                        help='Minimum longitude for events')
    parser.add_argument('--maxmag', dest='maxmag', type=float, action='store', default=None,
                        help='Max magnitude for events')
    parser.add_argument('--minmag', dest='minmag', type=float, action='store', default=3.0,
                        help='Minimum magnitude for events')
    parser.add_argument('--limit', dest='limit', type=int, action='store', default=20,
                        help='Maximum number of events to obtain')
    args = parser.parse_args()
    #print args

    return vars(args)

def query(constraints, service):
    """Send the request to the server, and dump the response."""

    params = urllib.urlencode(constraints)
    f = urllib.urlopen(base_url + '/' + service + '?' + params)
    print f.read()

constraints = get_constraints()
query(constraints, service)

# ----------------------------------------------------------------------


