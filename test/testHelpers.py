#
# Useful routines for testing.
#
# Begun by Peter L. Evans, summer 2013 (old code was in test*.py)
# <pevans@gfz-potsdam.de>
#
# ----------------------------------------------------------------------
import cgi
import json
import urllib2

def offline():
    """Are we online now?"""
    url = "http://geofon.gfz-potsdam.de/"
    try:
        response = urllib2.urlopen(url)
        if response:
            return False
        else:
            print " *** got a non-True response from "+url
            return False
    except urllib2.URLError:
        return True


def short_error_body(b):
    for line in b.splitlines():
        if line.startswith("Service '") or line.startswith("Error ") or line.find("/event/") > -1:
            print line

def count_lines(s):
    """Body is typically a one-item list, containing a string."""
    if s:
        if len(s) == 1:
            return s[0].count('\n')
        else:
            return 'list of %i items' % len(s)
    else:
        return 'None'

def count_json_obj(s):
    """If this is a JSON string, how big is its object?"""
    assert(isinstance(s, str))

    verbose = False
    if (verbose):
        print "count_json_obj: (%i)" % len(s),
        if len(s) > 10:
            print s[0:10], "...", s[-10:-1]
        else:
            print

    try:
        obj = json.loads(s)  # (s[2:-2]) - if it is double-wrapped
        return len(obj)
    except ValueError:
        return 0
    except TypeError as e:
        print "count_json_obj: TypeError!", e
        print "String was:", "x%sx" % s
        return 0

def count_json_obj2(s):
    """If this is a JSON string, how many level-2 objects does it have?"""
    assert(isinstance(s, str))

    count = 0
    try:
        obj = json.loads(s)  # (s[2:-2]) - if it is double-wrapped
        for obj2 in obj:
            count += len(obj2)
        return count
    except ValueError:
        return 0

def print_json_obj(body):
    """Quick re-format of a JSON-formatted body"""
    for item in json.loads(body[0]):
            print item
            
def query_str(d):
    """Prepare a query string from a dictionary d."""
    return "&".join('%s=%i' % (x, y) for x, y in d.items())
