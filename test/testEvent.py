#!/usr/bin/env python
#
# Run unit tests on the event module of webinterface.
#
# Begun by Peter L. Evans, July 2013
# <pevans@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

import datetime
import math
import os
import sys
import tempfile
import time
import unittest
import urllib

sys.path.append(os.path.join('..', 'wsgi'))  # for wsgicomm
sys.path.append(os.path.join('..', 'wsgi', 'modules'))

#from event import *
import event
import wsgicomm

test_verbosity = 0   # How noisy should the *unittests* be?

from testHelpers import *

# ----------------------------------------------------------------------
class WebInterface(object):
    def __init__(self, appName):
        self.__action_table = {}
        self.server_folder = '..'
        self.__modules = []
        self.action_table = {}

    def registerAction(self, name, func, *multipar):
        self.__action_table[name] = (func, set(multipar))

    def getConfigTree(self, prefix):
        import eventconfig # for standalone testing
        return eventconfig.conf

    def __repr__(self):
        """Dump important information about me, including what URLs I handle."""

        s = ""

        s += "Server directory: " + str(self.server_folder)
        s += "\n\n"

        s += "Modules:\n"
        s += str(sorted(self.__modules))
        s += "\n\n"

        s += "Registered URLs:\n"
        for a in sorted(self.__action_table):
            s += a + ": " + str(self.__action_table[a]) + "\n"
        return s

wi = WebInterface(__name__)
mod = event.WI_Module(wi)
#print wi

start_response = ""

# ----------------------------------------------------------------------

class TestTinyThings(unittest.TestCase):
    def test_date_T_comcat(self):
        result = event.date_T('2013-06-15T10:39:43.000+00:00')
        self.assertEqual(result, '2013-06-15T10:39:43')

    def test_date_T_geofon(self):
        result = event.date_T('2013-07-15 09:09:33')
        self.assertEqual(result, '2013-07-15T09:09:33')

    def test_date_T_emsc(self):
        instr = '2013-07-15T09:09:39'
        outstr = event.date_T(instr)
        self.assertEqual(instr, outstr)

    def test_region_lookup_given(self):
        """Passes if lookupIfGiven == False so orig region is not replaced"""
        env = {'PATH_INFO': 'event/meteor', 'QUERY_STRING': 'minlat=54&maxlat=56&minlog=60&maxlon=62&format=json'}
        body = mod.getEvents(env, start_response)
        ed = event.EventData()
        ed.json_loads(body[0])
        #print ed.data
        self.assertEqual(ed.data[0][7], "Chelyabinsk")

    def test_region_lookup_empty(self):
        """Passes if lookupIfEmpty == True. Requires SC3 look-up.

        Based on an M5.3 event on 2013-06-18T23:02:09 at 54.2N, 96.1E.
        """
        params = ('minlat=54', 'maxlat=56',
                  'minlon=60', 'maxlon=120',
                  'start=2013-06-13',
                  'end=2013-06-20',
                  'format=json')
        qs = '&'.join(params)
        env = {'PATH_INFO': 'event/comcat', 'QUERY_STRING': qs}
        if not _offline:
            body = mod.getEvents(env, start_response)
            ed = event.EventData()
            ed.json_loads(body[0])

            if len(ed.data) == 1:
                dates = ed.column(0)
                lats = ed.column(3)
                lons = ed.column("longitude")
                regions = ed.column("region")
                #for ev in range(len(lats)):
                #    print "%3i | %s | %8.3g | %8.3g | %s" % (ev, dates[ev], lats[ev], lons[ev], regions[ev])
                self.assertEqual(ed.data[0][7], "Southwestern Siberia, Russia")

            else:
                print "Didn't get exactly one event, check request parameters."
                print "Query string was:", qs
                # FIXME: Should I flag this as a test failure?

class TestAreaCircle(unittest.TestCase):
    """Circlular regions.

    Kinda dumb that we have to prepare options and URL details here!
    """
    options = {}
    options['lookupIfEmpty'] = True
    options['lookupIfGiven'] = False
    options['defaultLimit'] = 400
    baseURL = 'http://geofon.gfz-potsdam.de/eqinfo/list.php'
    extraParams = 'fmt=csv'

    def test_bounding_rect_equator(self):
        """Point on the equator"""
        r = 30
        es = event.ESGeofon('Test', self.options, self.baseURL, self.extraParams)
        t = []
        for lon in range(-180, 180, 30):
            t.append((0,  lon, r, r, -r, lon+r, lon-r))
        for s in t:
            max_lat, min_lat, max_lon, min_lon = es._bounding_rect(s[0], s[1], s[2])
            self.assertEqual(max_lat, s[3])
            self.assertEqual(min_lat, s[4])
            # The following don't account for the date line very well,
            # but handle the common cases:
            if s[1] > 0 and max_lon > 0 and max_lon < 180:
                self.assertGreater(max_lon, s[5], 'lon=%g radius=%g got max_lon=%g expect >%g' % (s[1], s[2], max_lon, s[5]))
            if s[1] < 0 and min_lon < 0 and min_lon > -180:
                self.assertLess(min_lon, s[6], 'lon=%g radius=%g got min_lon=%g expect <%g' % (s[1], s[2], min_lon, s[6]))

    def test_bounding_rect_greenwich(self):
        """Point on the prime meridian"""
        r = 30
        es = event.ESGeofon('Test', self.options, self.baseURL, self.extraParams)
        t = []
        lon = 0
        for lat in range(-90, 90+15, 15):
            north = min(90, lat+r)
            south = max(-90, lat-r)
            if north == 90: north = None
            if south == -90: south = None
            t.append((lat,  lon, r, north, south, lon+r, lon-r))
        for s in t:
            max_lat, min_lat, max_lon, min_lon = es._bounding_rect(s[0], s[1], s[2])
            self.assertEqual(max_lat, s[3])
            self.assertEqual(min_lat, s[4])
            # The following don't account for the date line very well,
            # but handle the common cases:
            if s[1] > 0 and max_lon > 0 and max_lon < 180:
                self.assertGreater(max_lon, s[5], 'lon=%g radius=%g got max_lon=%g expect >%g' % (s[1], s[2], max_lon, s[5]))
            if s[1] < 0 and min_lon < 0 and min_lon > -180:
                self.assertLess(min_lon, s[6], 'lon=%g radius=%g got min_lon=%g expect <%g' % (s[1], s[2], min_lon, s[6]))



# ----------------------------------------------------------------------

class TestDelAzi(unittest.TestCase):
    def setUp(self):
        # lat0 lon0 lat1 lon1 distance
        self.t = [
            (  0,  15,   40,  15,  40, "north from eq" ),
            (  0,  15,  -30,  15,  30, "south from eq" ),
            ( 10,  15,   22,  15,  12, "north from 10" ),
            ( 20,  15,   90,   0,  70, "north pole" ),
            ( 10,  12,  -90,   6, 100, "south pole" ),
            (-30,  44,   90,  60, 120, "north pole" ),
            (  0,   0,    0,  16,  16, "equator east"),
          ]
        self.fun = event._delazi

    def testSome(self):
        """A few unordered tests to start."""
        for s in self.t:
            d = self.fun(s[0], s[1], s[2], s[3])
            self.assertAlmostEqual(d, s[4], 5, msg=s[5] + ": got %g expected %g" % (d, s[4]))

    def testEquator(self):
        for lon_0 in range(-350, 400, 50):
            for lon_1 in range(lon_0, 400, 100):
                d_true = abs((lon_0 - lon_1) % 360)
                if d_true > 180:
                    d_true = 360 - d_true  # It's shorter the other way!

                t = [ (0, lon_0,  0, lon_1, d_true, "eq east (lon %g->%g)" % (lon_0, lon_1)),
                      (0, lon_1,  0, lon_0, d_true, "eq west (lon %g->%g)" % (lon_1, lon_0)), ]
                for s in t:
                    d = self.fun(s[0], s[1], s[2], s[3])
                    self.assertAlmostEqual(d, s[4], 5, msg=s[5] + ": got %g expected %g" % (d, s[4]))

    def testNorthSouth(self):
        """Tests along meridians"""

        for lon_0 in range(-350, 400, 50):
            for lat_0 in range(-90, 90, 15):
                t = [ (lat_0, lon_0,  90, 0, 90-lat_0, "north pole (%g,%g)" % (lat_0, lon_0)),
                      (lat_0, lon_0, -90, 0, 90+lat_0, "south pole (%g,%g)" % (lat_0, lon_0)), ]
                for s in t:
                    d = self.fun(s[0], s[1], s[2], s[3])
                    self.assertAlmostEqual(d, s[4], 5, msg=s[5] + ": got %g expected %g" % (d, s[4]))

    def testRotatePole(self):
        """Test invariant wrt pole longitude"""
        lon_0 = 57
        for lat_0 in range(-60, 60, 30):
            for lon_p in range(-210, 30, 210):
                t = [ (lat_0, lon_0,  90, lon_p, 90-lat_0, "north %d" % lon_p),
                      (lat_0, lon_0, -90, lon_p, 90+lat_0, "south %d" % lon_p),
                    ]
                for s in t:
                    d = self.fun(s[0], s[1], s[2], s[3])
                    self.assertAlmostEqual(d, s[4], 5, msg=s[5])

    def testSC3Delazi(self):
        """Are both delazi the same?"""
        import seiscomp3.Math

        for lat_0 in range(-90, 90, 30):
            for lon_0 in range(-180, 180, 60):
                for lat_1 in range(-15, 90, 15):
                    for lon_1 in range(-60, 180, 60):
                        d_1 = self.fun(lat_0, lon_0, lat_1, lon_1)
                        d_2 = seiscomp3.Math.delazi(lat_0, lon_0, lat_1, lon_1)[0]
                        self.assertAlmostEqual(d_1, d_2)

# ----------------------------------------------------------------------

class TestEventData(unittest.TestCase):
    columns = ('datetime', 'magnitude', 'magtype',
               'latitude', 'longitude', 'depth',
               'key', 'region')
    header = ','.join(columns)
    test_rows = [['1999-05-05T12:00:00', 4.5, 'Mb', 30, 60, 10, 'p101', 'Earth Somewhere'],
                 ['2001-01-01T12:00:00', 4, 'Mw', 15.0, 60, 10, 'p102', 'Europe'],
                 ['2002-02-02T12:00:00', 3.5, 'M', 89, 0, 100, 'p103', "Santa's village"],
                 ['2003-03-03T12:00:00', 3, 'Ml', -89, 180,  5, 'p104', 'South Pole']
                 ]

    def test_zero(self):
        ed = event.EventData()
        self.assertEqual(len(ed), 0)

    def test_one(self):
        ed = event.EventData(self.test_rows[0])
        self.assertEqual(len(ed), 1)

    def test_two(self):
        """Two copies of the same row, should be two items."""
        ed = event.EventData(self.test_rows[0])
        ed.append(self.test_rows[0])
        self.assertEqual(len(ed), 2)

    def test_many_json(self):
        ed = event.EventData()
        for ev in self.test_rows:
            ed.append(ev)
        for ev in self.test_rows:
            ed.append(ev)
        self.assertEqual(len(ed), 2*len(self.test_rows))
        lim = 5
        body = ed.write_all('json', lim)
        self.assertEqual(count_json_obj(body), lim+1)       # header row
        self.assertEqual(count_json_obj2(body), len(ed.column_names)*(lim+1))  # 8 cols
        #DEBUGprint body

    def test_csv(self):

        ed = event.EventData()
        ed.append(self.test_rows[0])
        body = ed.write_all('csv', 10)
        if test_verbosity > 0:
            print "test_csv:\n", body
        self.assertEqual(body.count('\n'), 3)
        self.assertEqual(body.count(','), 2*(len(self.columns)-1))
        self.assertEqual(body.split('\r')[0], self.header)

                                   
    def test_json(self):
        ed = event.EventData(self.test_rows[0])
        body = ed.write_all('json', 10)
        if test_verbosity > 0:
            print "test_json:\n", body
        self.assertTrue(isinstance(body, str))
        self.assertGreater(len(body), len(self.header)*2)  # Weak bound - body is a string.

    def test_json_loads(self):
        """Round-tripping via JSON string."""
        ed = event.EventData()
        for ev in self.test_rows:
            ed.append(ev)
        result = ed.write_all('json', len(self.test_rows))
        self.assertEqual(len(result), 373)

        ed2 = event.EventData()
        ed2.json_loads(result)
        #print "data:", ed2.data
        self.assertEqual(len(ed2), len(self.test_rows))
        for f in range(len(ed2)):
            self.assertEqual(len(ed2.data[f]), 8)

    def test_text(self):
        """FDSN-style text output"""
        fdsnws_header = "EventID|Time|Latitude|Longitude|Depth/km|Author|Catalog|Contributor|ContributorID|MagType|Magnitude|MagAuthor|EventLocationName"
        ed = event.EventData()
        for ev in self.test_rows:
            ed.append(ev)
        num_rows = len(self.test_rows)
        result = ed.write_all('text', num_rows)
        lines = result.split('\n')
        for line in lines:
            print line

        self.assertEqual(len(lines), num_rows + 2)  # Why not +1?
        self.assertEqual(lines[0].strip(), fdsnws_header)
        self.assertEqual(result.count('|'), (num_rows+1)*fdsnws_header.count('|'))


    def test_unimplemented(self):
        """Unimplemented 'fmt' option raises KeyError.

        Note: this occuring means the code using EventData is
        wrong. This is NOT something to send to the client, so
        don't raise WIError!

        """
        ed = event.EventData(self.test_rows[0])
        with self.assertRaises(KeyError):
            body = ed.write_all('unimplemented', 10)
            print "test_unimplemented:", body


class TestEventService(unittest.TestCase):

    ruler = 5*"- --"

    def setUp(self):
        self.periodOfInterest = "start=2013-06-01&end=2013-06-10"

    #def tearDown(self):
    #    print "tear down"

    def test_catalog(self):
        body = mod.getEventsCatalog()
        self.assertIn('geofon', body)

    def test_select_geofon_default(self):
        env = {'PATH_INFO': 'event/geofon', 'QUERY_STRING': ''}
        if _offline:
            with self.assertRaises(wsgicomm.WIError):
                body = mod.getEvents(env, start_response)
            try:
                body = mod.getEvents(env, start_response)
            except wsgicomm.WIError as e:
                error_body = ''.join(e.body)
                print "Error body:", short_error_body(error_body)
                self.assertTrue(error_body.startswith("Error"))
        else:
            body = mod.getEvents(env, start_response)
            print "Body:", len(body[0]), "Lines:", count_lines(body)
            self.assertEqual(len(body), 1)
            self.assertGreater(len(body[0]), 50)
            self.assertGreater(count_lines(body), 2)

    def test_nomethod(self):
        """This web service has never heard of this method.

        But we can't test this by calling getEvents - this test must
        be done at the dispatcher level.

        """
        env = {'PATH_INFO': 'nosuchmethod', 'QUERY_STRING': ''}
        with self.assertRaises(AssertionError):
          body = mod.getEvents(env, start_response)

    def test_select_wrongservice(self):
        """Service 'nosuchservice' is not defined."""
        env = {'PATH_INFO': 'event/nosuchservice', 'QUERY_STRING': ''}
        body = mod.getEvents(env, start_response)
        self.assertTrue(body[0].find('Error 400:') > -1)

    def test_select_noservice(self):
        """No trailing slash on the URL."""
        env = {'PATH_INFO': 'event', 'QUERY_STRING': ''}
        body = mod.getEvents(env, start_response)
        self.assertTrue(body[0].find('Error 400:') > -1)

    def SKIPtest_select_file_default(self):
        """Call file service with default parameters - should raise
        an error because 'file' needs columns, input parameters.

        2013-07-25: This service is disabled, so 400, "Unknown service name" now.
        """
        env = {'PATH_INFO': 'event/file', 'QUERY_STRING': ''}
        with self.assertRaises(wsgicomm.WIError):
            body = mod.getEvents(env, start_response)

    def SKIPtest_select_parse_default(self):
        """Call 'parse' service with default parameters - should raise
        an error because 'parse' needs columns, input parameters.

        FIXME: This returns Error 400, "Unknown service name" but it should raise an error about missing parameters!

        """
        env = {'PATH_INFO': 'event/parse', 'QUERY_STRING': ''}

        with self.assertRaises(wsgicomm.WIError) as cm:
            body = mod.getEvents(env, start_response)
        error_body = ''.join(cm.exception.body)
        print "Error body:", short_error_body(error_body)

class TestEventServiceBadParams(unittest.TestCase):
    """These tests produce error pages, by raising WIError. They either
    (i)  specify bad parameter combinations ('400'), or
    (ii) are well-posed, but return no data from the target service ('204').

    """
    def setUp(self):
        self.env = {'PATH_INFO': 'event/geofon'}
        self.baseParams =  ('start=2013-05-01', 'end=2013-08-01', 'format=csv')

    def test_bad_dates(self):
        """Start date must be before end date."""
        params = ('start=2013-07-01', 'end=2012-01-01')
        self.env['QUERY_STRING'] = "&".join(params)
        if _offline:
            return
        with self.assertRaises(wsgicomm.WIError) as cm:
            body = mod.getEvents(self.env, start_response)
        #print "Obtained expected error:", cm.exception
        ebody = "".join(cm.exception.body)
        print short_error_body(ebody)
        self.assertTrue(ebody.startswith('Error 204'))

    def test_no_big_mag(self):
        """No recorded earthquake has M>9.5."""
        self.env['QUERY_STRING'] = 'minmag=9.5'
        if _offline:
            return
        with self.assertRaises(wsgicomm.WIError) as cm:
            body = mod.getEvents(self.env, start_response)
        #print "Obtained expected error:", cm.exception
        ebody = "".join(cm.exception.body)
        print short_error_body(ebody)
        self.assertTrue(ebody.startswith('Error 204'))

    def test_no_depth(self):
        """No earthquakes are deeper than 900 km.

        This test can't succeed until eqinfo implements depth
        filtering, or I do it here, so that no deep EQs are found.
        Today, the depth constraint is IGNORED.

        """
        self.env['QUERY_STRING'] = 'mindepth=900'
        with self.assertRaises(wsgicomm.WIError) as cm:
            body = mod.getEvents(self.env, start_response)
        print "Expected error:", cm.exception.body
        ebody = "".join(cm.exception.body)
        print short_error_body(ebody)
        self.assertTrue(ebody.startswith('Error 204'))

    def test_conflict_region(self):
        """Can't ask for an area-rectangle AND area-circle.

        NOTE: lat/lon are handled, latitude/longitude are PASSED ON!
        """
        E_BOTH_LATLON = "both 'lat' and 'lon' are required"
        E_BOTH_REGION_TYPES = "both area-rectangle and area-circle"

        testList = [ (('lat=0',), E_BOTH_LATLON),
                     (('lon=0',), E_BOTH_LATLON),
                     (('maxradius=30',),   E_BOTH_LATLON),
                     (('maxazimuth=300',), E_BOTH_LATLON),
                     (('maxlat=0', 'maxradius=30',),   E_BOTH_REGION_TYPES),
                     (('maxlat=0', 'maxazimuth=120',), E_BOTH_REGION_TYPES),
                     (('maxlat=0', 'minazimuth=120',), E_BOTH_REGION_TYPES),
                     (('maxlon=0', 'maxradius=30',), E_BOTH_REGION_TYPES),
                     (('maxlat=0', 'lat=-30',),      E_BOTH_REGION_TYPES),
                     (('maxlon=0', 'lon=-120',),     E_BOTH_REGION_TYPES),
                     (('minlat=0', 'minradius=30',), E_BOTH_REGION_TYPES),
                     (('minlon=0', 'minradius=30',), E_BOTH_REGION_TYPES),
                     ]
        for t in testList:
            params = t[0]
            self.env['QUERY_STRING'] = "&".join(params)
            if test_verbosity > 0:
                print "QUERY_STRING:", self.env['QUERY_STRING']
            with self.assertRaises(wsgicomm.WIError) as cm:
                body = mod.getEvents(self.env, start_response)
            #print "Expected error:", cm.exception
            ebody = "".join(cm.exception.body)
            if test_verbosity > 3:
                print short_error_body(ebody)
            self.assertTrue(ebody.startswith('Error 400'))
            self.assertGreater(ebody.find(t[1]), -1)

    def test_bad_param_values(self):
        """Some parameters must have specific types or values (bad cases)."""
        E_FLOAT = "must be floats"
        E_RADIUS_RANGE = "must be floats between 0.0 and 180.0"
        E_AZIMUTH_RANGE = "must be floats between 0.0 and 360.0"
        testList = [ (('lat=five', 'lon=6.0'),     E_FLOAT),
                     (('lat=5.0', 'lon=3.4.0',),   E_FLOAT),
                     (('lat=5.0', 'lon=6.0', 'maxradius=str'),   E_RADIUS_RANGE),
                     (('lat=5.0', 'lon=6.0', 'maxradius=-1.0'),  E_RADIUS_RANGE),
                     (('lat=5.0', 'lon=6.0', 'maxradius=181.0'), E_RADIUS_RANGE),
                     (('lat=5.0', 'lon=6.0', 'minradius=str'),   E_RADIUS_RANGE),
                     (('lat=5.0', 'lon=6.0', 'minradius=-1.0'),  E_RADIUS_RANGE),
                     (('lat=5.0', 'lon=6.0', 'minradius=181.0'), E_RADIUS_RANGE),
                     (('lat=5.0', 'lon=6.0', 'maxazimuth=str'),   E_AZIMUTH_RANGE),
                     (('lat=5.0', 'lon=6.0', 'maxazimuth=-1.0'),  E_AZIMUTH_RANGE),
                     (('lat=5.0', 'lon=6.0', 'maxazimuth=361.0'), E_AZIMUTH_RANGE),
                     (('lat=5.0', 'lon=6.0', 'minazimuth=str'),   E_AZIMUTH_RANGE),
                     (('lat=5.0', 'lon=6.0', 'minazimuth=-1.0'),  E_AZIMUTH_RANGE),
                     (('lat=5.0', 'lon=6.0', 'minazimuth=361.0'), E_AZIMUTH_RANGE),
                      ]
        for t in testList:
            params = t[0]
            self.env['QUERY_STRING'] = "&".join(params)
            if test_verbosity > 0:
                print "QUERY_STRING:", self.env['QUERY_STRING']
            with self.assertRaises(wsgicomm.WIError) as cm:
                body = mod.getEvents(self.env, start_response)
            #print "Expected error:", cm.exception
            ebody = "".join(cm.exception.body)
            if test_verbosity > 3:
                print short_error_body(ebody)
            self.assertTrue(ebody.startswith('Error 400'))
            self.assertGreater(ebody.find(t[1]), -1)

    def test_useless_param_values(self):
        """Some parameter combinations can never produce data, therefore must always give 400."""
        paramsList = [  ('lat=9.0', 'lon=2.0', 'minradius=80.0', 'maxradius=10.0'),
                      ]
        for params in paramsList:
            self.env['QUERY_STRING'] = "&".join(params)
            if test_verbosity > 0:
                print "QUERY_STRING:", self.env['QUERY_STRING']
            with self.assertRaises(wsgicomm.WIError) as cm:
                body = mod.getEvents(self.env, start_response)
            print "Expected error:", cm.exception
            ebody = "".join(cm.exception.body)
            print short_error_body(ebody)
            self.assertTrue(ebody.startswith('Error 400'))
            self.assertGreater(ebody.find('minradius'), -1)
            self.assertGreater(ebody.find('maxradius'), -1)

    def test_good_circle_values(self):
        """Some test cases for area-circle requests.

        Test coverage avoids dateline crossings for now."""
        paramsList = [  ('lat=5.0',  'lon=10.0', 'maxradius=30.0'),
                        ('lat=45.0', 'lon=10.0', 'maxradius=30.0'),
                        ('lat=55.0', 'lon=10.0', 'maxradius=30.0'),
                        ('lat=75.0', 'lon=10.0', 'maxradius=30.0'),
                        ('lat=85.0', 'lon=10.0', 'maxradius=30.0'),
                        ('lat=60.0', 'lon=10.0', 'maxradius=29.0'),
                        ('lat=60.0', 'lon=10.0', 'maxradius=30.0'),
                        ('lat=60.0', 'lon=10.0', 'maxradius=31.0'),
                        ('lat=15.0', 'lon=10.0', 'maxradius=90.0'),
                        ('lat=15.0', 'lon=10.0', 'maxradius=120.0'),
                        ('lat=-15.0', 'lon=10.0', 'maxradius=90.0'),
                        ('lat=-15.0', 'lon=10.0', 'maxradius=120.0'),
                        ('lat=90.0', 'lon=10.0', 'maxradius=90.0'),
                        ('lat=90.0', 'lon=80.0', 'maxradius=90.0'),
                        ('lat=-90.0', 'lon=0.0', 'maxradius=90.0'),
                     ]
        for params in paramsList:
            x = list(params)
            x.extend(self.baseParams)
            self.env['QUERY_STRING'] = '&'.join(x)
            if (test_verbosity > 0):
                print "\nQUERY_STRING:", self.env['QUERY_STRING']
            body = mod.getEvents(self.env, start_response)
            num_lines = count_lines(body)
            if (test_verbosity > 0):
                print "Lines:", num_lines
            self.assertGreater(num_lines, 1)
            #TODO self.assertEqual(num_lines, expected_lines)

    def test_good_param_values(self):
        """Some parameters must have specific types or values (good cases).

        TODO: Split this test - some is testing area-circle stuff.
        """
        paramsList = [  ('lat=5.0', 'lon=105.0'),
                        ('lat=-5.0', 'lon=-105.0'),
                        ('lat=5.0', 'lon=105.0', 'maxradius=20.0'),
                        ('lat=5.0', 'lon=105.0', 'maxradius=20'),
                        ('lat=5',   'lon=105.0', 'maxradius=20'),
                        ('lat=5.0', 'lon=105', 'maxradius=20'),
                        ('lat=5.0', 'lon=105.0', 'minradius=20.0'),
                        ('lat=5.0', 'lon=6.0', 'maxazimuth=90.0'),
                        ('lat=5.0', 'lon=6.0', 'maxazimuth=90.0', 'minazimuth=0.0'),
                        ('lat=5.0', 'lon=6.0', 'maxazimuth=90.0', 'minazimuth=0'),
                        ('lat=5.0', 'lon=6.0', 'maxazimuth=90.0', 'minazimuth=-0'),
                        ('lat=5.0', 'lon=6.0', 'maxazimuth=90.0', 'minazimuth=-0.0'),
                        ('lat=5.0', 'lon=6.0', 'minazimuth=90.0', 'maxazimuth=180.0'),
                        ('lat=5.0', 'lon=6.0', 'minazimuth=90.0', 'maxazimuth=180'),
                        ('lat=5.0', 'lon=6.0', 'minazimuth=180', 'maxazimuth=300.0'),
                        ('lat=5.0', 'lon=6.0', 'minazimuth=300'),
                        ('lat=5.0', 'lon=6.0', 'minazimuth=300', 'maxazimuth=360.0'),
                      ]
        for params in paramsList:
            x = list(params)
            x.extend(self.baseParams)
            self.env['QUERY_STRING'] = '&'.join(x)
            if test_verbosity > 0:
                print "\nQUERY_STRING:", self.env['QUERY_STRING']
            body = mod.getEvents(self.env, start_response)
            num_lines = count_lines(body)
            if test_verbosity > 0:
                print "Lines:", num_lines
            self.assertGreater(num_lines, 1)
            #TODO self.assertEqual(num_lines, expected_lines)

class TestEventServiceOnline(unittest.TestCase):
    """Don't bother trying these tests if geofon is unavailable."""

    ruler = 5*"- --"

    def setUp(self):
        #if _offline:
        #    raise Exception("Are you connected to the internet?")
        self.periodOfInterest = "start=2013-06-01&end=2013-06-10"
        self.env = {'PATH_INFO': 'event/geofon',}

    def test_select_geofon_startend(self):
        env = {'HTTP_HOST': 'localhost',
               'PATH_INFO': 'event/geofon',
               'QUERY_STRING': 'start=2013-06-01&end=2013-06-15'}
        try:
            body = mod.getEvents(env, start_response)
            print "Lines:", count_lines(body)
            self.assertGreater(count_lines(body), 2)
        except wsgicomm.WIError as e:
            if _offline:
                error_body = "".join(e.body)
                self.assertTrue(error_body.startswith("Error"))
            else:
                print e
                self.fail("We shouldn't have gotten here!")

    def test_select_geofon_minmag(self):
        # FIXME: A bug is hiding here, for end=2013-06-15 there should be one event, on 2013-06-13
        # gfz2013lncg;"South of Java, Indonesia";6.7;M;"2013-06-13 16:47:25";-9.94;107.28;17;"xxl".
        # Seems to be because default output is 'text' somehow.
        
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': 'start=2013-06-01&end=2013-06-16&minmag=6.0&format=csv'}
        body = mod.getEvents(env, start_response)
        if _offline:
            self.assertTrue(body[0].startswith("Error"))
        else:
            print "Lines:", count_lines(body)
            self.assertGreater(count_lines(body), 2)

    def test_select_geofon_maxmag(self):
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': 'start=2013-06-01&end=2013-06-15&maxmag=4.5'}
        body = mod.getEvents(env, start_response)
        if _offline:
            self.assertTrue(body[0].startswith("Error"))
        else:
            print "Lines:", count_lines(body)
            self.assertGreater(count_lines(body), 2)

    def test_geofon_asia(self):
        """A simple region of interest"""
        region = {'maxlon': 170, 'minlon': 70, 'maxlat': 80, 'minlat': -10}
        assert(region['maxlon'] > region['minlon'])
        assert(region['maxlat'] > region['minlat'])
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': '&'.join(['start=2013-01-01',
                                         query_str(region),
                                         'format=json'])}
        body = mod.getEvents(env, start_response)
        if _offline:
            self.assertTrue(body[0].startswith("Error"))
            return

        ed = event.EventData()
        ed.json_loads(body[0])

        #print 'test_geofon_asia: len:', len(ed)

        lats = ed.column('latitude')
        self.assertGreaterEqual(min(lats), region['minlat'])
        self.assertLessEqual(max(lats), region['maxlat'])

        # The following assertions about longitude DO NOT hold if
        # the region crosses the Date Line:
        longs = ed.column('longitude')
        self.assertGreaterEqual(min(longs), region['minlon'])
        self.assertLessEqual(max(longs), region['maxlon'])

    def test_geofon_circle_north(self):
        """A circular region of interest.
        FAILS 2014-04-09: Returns events including Laptev Sea
        """
        region = {'lat': 80, 'lon': 90, 'maxradius': 5}
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': '&'.join(['start=2012-06-01',
                                         'end=2014-01-01',
                                         query_str(region),
                                         'format=csv'])}
        body = mod.getEvents(env, start_response)
        if _offline:
            self.assertTrue(body[0].startswith("Error"))
            return

        for line in body[0].splitlines():
            if line.startswith('#'):
                continue
            print "test_geofon_circle_north:", line
            self.assertTrue(line.endswith('Severnaya Zemlya') or line.endswith('region'))

    def test_geofon_dateline(self):
        """What happens when the region of interest crosses the dateline?"""
        region = {'maxlon': -150, 'minlon': 135, 'maxlat': 10, 'minlat': -60}
        assert(region['maxlon'] < region['minlon'])
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': '&'.join(['start=2013-01-01',
                                         query_str(region),
                                         'format=json'])}
        body = mod.getEvents(env, start_response)
        if _offline:
            self.assertTrue(body[0].startswith("Error"))
            return

        ed = event.EventData()
        ed.json_loads(body[0])

        longs = ed.column(4)
        #print "longs (sorted):", sorted(longs)
        westlongs = []
        eastlongs = []
        for lon in longs:
            if lon < 0:
                westlongs.append(lon)
            else:
                eastlongs.append(lon)

        # The following assertions about longitude DO NOT hold if the
        # region crosses both the Date Line AND the Prime Meridian:
        self.assertGreaterEqual(min(eastlongs), region['minlon'])
        self.assertLessEqual(max(westlongs), region['maxlon'])

    def test_depth_ranges(self):
        """Use depth filtering with the GEOFON eqinfo service."""
        params_0 = ('start=2013-01-01', 'end=2013-04-01',
                    'maxlat=0', 'minlon=135', 'minmag=5',
                    'format=csv')
        n_0 = 190  # All events found matching params_0 above
        z_1 = 35   # Depth in km
        n_1 = 163  # Number of events above z=z_1
        z_2 = 100
        n_2 = 180

        # The following assumes no events in the catalog have
        # depth < 0 or depth > 1000.
        #
        # You could check that assumption by using a first call
        # with no depth constraint, but that's overkill here.
        #
        #     min   max   number
        s = ((None, None, n_0),
             (0,    None, n_0),
             (0,    1000, n_0),
             (None, 1000, n_0),
             (None, z_1,  n_1),
             (0,    z_1,  n_1),
             (z_1,  None, n_0 - n_1),
             (z_1,  1000, n_0 - n_1),
             (None, z_2,  n_2),
             (z_2,  None, n_0 - n_2),
             (z_1,  z_2,  n_2 - n_1),
             (None, 0,    190) # <--- this is wrong! FIXME, should be No Content
             )
        # TODO: Tests with bad arguments:
        #(None, 0.5,    0),  [raise 204 No Content]
        #(1000, None, 0), [raise 204 No Content]
        #(z_2, z_1, 0)  # Need z_1 <= z_2, so No Content or bad args?
        #(None, 's', [raise bad args])
        #('s', None, [raise bad args])
        #
        # FIXME/WONTFIX: A subtle bug in eqinfo/list.php?: I would expect
        # (None, 0,    0)
        # or
        # (None, 0, 0) raises 204 No Content.
        # But visiting the target service at
        # http://geofon.gfz-potsdam.de/eqinfo/list.php?datemax=2013-04-01&lonmin=135&magmin=6.2&datemin=2013-01-01&depmax=0&latmax=0
        # gives lots of events with depth > 0 i.e. is wrong.


        for t in s:
            params = []
            params.extend(params_0)
            if t[0] != None:
                params.append('mindepth=%g' % (t[0]))
            if t[1] != None:
                params.append('maxdepth=%g' % (t[1]))
            expected = t[2]
            self.env['QUERY_STRING'] = '&'.join(params)
            body = mod.getEvents(self.env, start_response)
            num_lines = count_lines(body) -2 # Remove header for CSV output
            msg = 'mindepth=%s maxdepth=%s: got %g expected %g' % (t[0],t[1],num_lines,t[2])
            self.assertEqual(num_lines, expected, msg)

    def test_select_geofon_updatedafter(self):
        """Constraint 'updatedafter' is not allowed for service 'geofon'.

        TODO: Raise WIError, 40x
        """
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': 'updatedafter=2013-06-01'}
        with self.assertRaises(wsgicomm.WIError) as cm:
            body = mod.getEvents(env, start_response)
        ebody = "".join(cm.exception.body)
        self.assertTrue(ebody.startswith('Error 400:'))
        self.assertGreater(ebody.find('Unimplemented'), -1)

    def test_select_geofon_limit(self):
        """Add a limit constraint"""
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': 'start=2013-06-01&end=2013-06-16&minmag=6.0&limit=3'}
        body = mod.getEvents(env, start_response)
        if _offline:
            self.assertTrue(body[0].startswith("Error"))
        else:
            print "Lines:", count_lines(body)
            self.assertEqual(count_lines(body), 5)  # Header + limit events??

    def test_select_geofon_format_csv(self):
        """Add a format constraint"""
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': 'start=2013-06-01&end=2013-06-16&minmag=6.0&limit=4&format=csv'}
        body = mod.getEvents(env, start_response)
        num_lines = count_lines(body)
        #print "Lines:", num_lines
        self.assertEqual(num_lines, 6)   # 4 + 2 for header

    def test_select_geofon_format_text(self):
        """Request fdsnws-event text output. FIXME: QS needs to be 'format=text'!"""
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': 'start=2013-06-01&end=2013-06-16&minmag=6.0&limit=4&format=fdsnws-text'}
        body = mod.getEvents(env, start_response)
        num_lines = count_lines(body)
        print "geofon_format_text: body:", body, "(%i)" % len(body[0])
        #print "Lines:", num_lines
        self.assertEqual(num_lines, 5)   # 4 + 1 for header
        self.assertEqual(body[0].count('|'), num_lines*12)
                         
    def test_select_geofon_format_bad(self):
        """Reject an unsupported format constraint.

        Note: the WIError raised by EventData is okay. The WIError will be
        collected by the webinterface application(), and its body will be
        presented to the client. But using self.assertRaises(), there's no body,
        or exception, passed here for checking.

        """
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': self.periodOfInterest + '&format=XXX'}
        with self.assertRaises(wsgicomm.WIError):
            body = mod.getEvents(env, start_response)

        try:
            body = mod.getEvents(env, start_response)
        except wsgicomm.WIError as e:
            print "(Caught an expected WIError)"
            error_body = "".join(e.body)
        #print "Lines:", count_lines(error_body)
        self.assertGreater(error_body.find('Error 400:'), -1)
        self.assertGreater(error_body.find('output format'), -1)

    def test_select_geofon_format_json(self):
        """Add a format constraint to geofon"""
        env = {'PATH_INFO': 'event/geofon',
               'QUERY_STRING': self.periodOfInterest + '&minmag=5.5&limit=4&format=json-row'}
        body = mod.getEvents(env, start_response)
        if _offline:
            self.assertTrue(body[0].startswith("Error"))
        else:
            #print "Lines:", count_lines(body)
            self.assertEqual(count_lines(body), 0)
            #print "JSON objects:", count_json_obj(body[0])
            self.assertEqual(count_json_obj(body[0]), 5)  # Header + 4 events.


class TestEventServiceComcat(unittest.TestCase):
    def setUp(self):
        if _offline:
            raise Exception("Are you connected to the internet?")

    def DISABLEtest_select_comcat_default(self):
        """Output is big, and there's no need to hit their server all the time."""
        env = {'PATH_INFO': 'event/comcat',
               'QUERY_STRING': 'start=2013-06-01&end=2013-07-01'}
        body = mod.getEvents(env, start_response)
        print self.ruler
        print body
        print self.ruler
        self.assertEqual(count_lines(body), 54)  # Header + ??

    def test_select_comcat_format_json(self):
        """Add a format constraint to comcat"""
        periodOfInterest = "start=2013-06-01&end=2013-06-10"

        env = {'PATH_INFO': 'event/comcat',
               'QUERY_STRING': periodOfInterest + '&format=json-row'}
        body = mod.getEvents(env, start_response)
        print "Lines:", count_lines(body)
        self.assertEqual(count_lines(body), 0)  # No header for JSON


class TestEventServiceMeteor(unittest.TestCase):
    """Tests focussed on making sure the output formats are consistent."""

    ruler = 5*"- --"

    def test_meteor_default(self):
        env = {'PATH_INFO': 'event/meteor', 'QUERY_STRING': ''}
        body = mod.getEvents(env, start_response)

        print "test_meteor_default: default raw/text output?"
        print self.ruler
        print body[0]
        print self.ruler
        self.assertEqual(count_lines(body), 2)  # Header + one event

    def test_meteor_csv(self):
        env = {'PATH_INFO': 'event/meteor', 'QUERY_STRING': 'format=csv'}
        body = mod.getEvents(env, start_response)

        print "test_meteor_csv: CSV output"
        print self.ruler
        print body[0]
        print self.ruler

        self.assertEqual(count_lines(body), 3)  # Header + one event + final "# Lines: 1"

    def test_meteor_json(self):
        env = {'PATH_INFO': 'event/meteor', 'QUERY_STRING': 'format=json'}
        body = mod.getEvents(env, start_response)
        self.assertEqual(count_lines(body), 0)
        self.assertEqual(count_json_obj2(body[0]), 8*2)  # Header + 1 event.


class TestEventServiceEMSC(unittest.TestCase):

    def setUp(self):
        if _offline:
            raise Exception("Are you connected to the internet?")
        self.periodOfInterest = "start=2013-07-01&end=2013-07-04"

    def test_emsc_default(self):
        """With no parameters, EMSC gives no events, only a header."""
        env = {'PATH_INFO': 'event/emsc', 'QUERY_STRING': ''}
        body = mod.getEvents(env, start_response)
        self.assertEqual(count_lines(body), 0)

    def test_emsc_default_json(self):
        env = {'PATH_INFO': 'event/emsc',
               'QUERY_STRING': self.periodOfInterest + '&limit=5&format=json'}
        body = mod.getEvents(env, start_response)
        #print "Lines:", count_lines(body)
        self.assertEqual(count_lines(body), 0)
        #print "JSON objects:", count_json_obj(body[0])
        self.assertEqual(count_json_obj(body[0]), 6)  # Header row, +limit objects
        #print "test_emsc_default_json: JSON sub-objects:", count_json_obj2(body[0])
        self.assertEqual(count_json_obj2(body[0]), 6*8)  # (Header row, +limit objects)*8 cols


class TestCompareServicesOnline(unittest.TestCase):
    """Compare all three major services

    Don't bother trying these tests if geofon is unavailable.
    Minimum magnitude in GEOFON/eqinfo is around 1.8.
    
    """

    def setUp(self):
        if _offline:
            raise Exception("Are you connected to the internet?")

        # About 21 events:        
        self.params_0 = ("start=2013-06-01", "end=2013-06-02",
                         "minlon=0", "minmag=3.5",
                         "format=json")

        # About 9 events:
        self.params_1 = ("start=2013-06-01", "end=2013-07-01",
                         "minlat=45", "minmag=5.0",
                         "format=json")

    def normEvents(self, ev1, ev2):
        """Are two events close in space, time and magnitude?

        This is a weighted norm. One second in time should be about
        the same as a few km/sec in position.
                
        """
        a = 6400.0
        deg2km = math.pi*a/180.0
        c = 4.0  # km/sec
        lat_scale = deg2km/c
        phi = 0.5*(ev1[3] + ev2[3])  # latitudes
        lon_scale = math.cos(phi)*lat_scale
        #      time, mag,  lat,       lon,    depth
        scales = [1, 0.2, lat_scale, lon_scale, 10]

        fmt = '%Y-%m-%dT%H:%M:%S'
        dt1 = datetime.datetime.strptime(ev1[0], fmt)
        dt2 = datetime.datetime.strptime(ev2[0], fmt)
        
        time_delta = (dt1 - dt2).total_seconds()
        
        return sum([ (time_delta/scales[0])**2,
                    ((ev1[1] - ev2[1])/scales[1])**2,
                    ((ev1[3] - ev2[3])/scales[2])**2,
                    ((ev1[4] - ev2[4])/scales[3])**2,
                    ((ev1[5] - ev2[5])/scales[4])**2  ])
                
    def testJune(self):
        qs = "&".join(self.params_0)
        ed = {}
        for service in 'geofon', 'comcat', 'emsc':
            env = {'PATH_INFO': 'event/%s' % (service),
                   'QUERY_STRING': qs}
            body = mod.getEvents(env, start_response)
            self.assertGreater(count_json_obj(body[0]), 1)
            ed[service] = event.EventData()
            ed[service].json_loads(body[0])
            count = 0
            for line in ed[service].data:
                count += 1
                print service, count, line

        # Really need a fuzzy sort of intersection here
        tab = ''
        print 'YYYY-mm-ddTHH:MM:SS',
        for v in ed['comcat'].data:
            print v[0].split('T')[1]+tab,
        print

        matched = []
        for u in ed['geofon'].data:
            print u[0],
            for v in ed['comcat'].data:
                d = self.normEvents(u, v)
                if d < 100.0:
                    stars = '%7.3f' % (d)
                    matched.append(u[0])
                else:
                    stars = '*'*int(min(7, math.log10(d/10.0)))
                print '%7s' % (stars) + tab,
            print  
        print "Matched %i/%i GEOFON events to %i ComCat events." % (len(matched),
                                                                    len(ed['geofon'].data),
                                                                    len(ed['comcat'].data))
        self.assertEqual(len(ed['geofon'].data), 15)
        self.assertEqual(len(ed['comcat'].data), 17)
        self.assertEqual(len(matched), 12)

# ----------------------------------------------------------------------

class TestEventServiceFDSN(unittest.TestCase):
    """
    Tests of the fdsn-event handler.
    """
    service_base_url = "http://eida.rm.ingv.it/webinterface/wsgi"
    #service_base_url = "http://localhost:8008"  #  -- for manage.py
    catalog_url = service_base_url + "/event/catalogs"
    fdsn_url = service_base_url + "/event/fdsnws"

    # Header contents must match what JavaScript (request.js) expects,
    # as defined in its _event_format structure.
    expected_header = ("datetime", "magnitude", "magtype", "latitude", "longitude", "depth", "key", "region")

    # Header contents must match what JavaScript (request.js) expects,
    # as defined in its _event_format structure.
    expected_header = ("datetime", "magnitude", "magtype", "latitude", "longitude", "depth", "key", "region")

    def test_catalog(self):
        try:
            fd = urllib2.urlopen(self.catalog_url)
        except urllib2.HTTPError as err:
            if err.code == 404:
                print '404 Not Found'
                self.fail()
                return
        response = fd.read()
        self.assertGreater(len(response), 10)

        resp = json.loads(response)
        self.assertTrue(resp.has_key('fdsnws'))

    def test_events_no_qs(self):
        """Empty query string, should get SOMETHING.

        Probably defaultLimit events, as CSV or text.
        """
        url = self.fdsn_url
        try:
            fd = urllib2.urlopen(url)
        except urllib2.HTTPError as err:
            if err.code == 404:
                print '404 Not Found'
                self.fail()
                return
        response = fd.read()
        self.assertGreater(len(response), 5)

    def test_events_json(self):
        """Some unrestricted JSON output"""
        params = {'format': 'json'}

        qs = urllib.urlencode(params)
        try:
            fd = urllib2.urlopen(self.fdsn_url + '?' + qs)
        except urllib2.HTTPError as err:
            print err
            self.fail()

        response = fd.read()
        resp = json.loads(response)
        self.assertGreater(len(resp), 3)

        # Header contents must match what JavaScript (request.js) expects,
        # defined in its _event_format structure.
        header = resp[0]
        self.assertEqual(len(header), len(self.expected_header))
        self.assertEqual(header[0], 'datetime')
        self.assertEqual(header[1], 'magnitude')
        for k in range(0, len(self.expected_header)):
            self.assertEqual(header[k], self.expected_header[k])

    def test_events_limit(self):
        """Specify only a few events; CSV output"""
        num = 3
        params = {'limit': num, 'format': 'csv'}

        qs = urllib.urlencode(params)
        try:
            fd = urllib2.urlopen(self.fdsn_url + '?' + qs)
        except urllib2.HTTPError as err:
            print err
            self.fail()

        response = fd.read()
        self.assertEqual(len(response.split("\n")), num+3)

    def test_events_limit_json(self):
        """Specify only a few events; JSON output.
        """
        num = 3
        params = {'format': 'json',
                  'limit': num}

        qs = urllib.urlencode(params)
        try:
            fd = urllib2.urlopen(self.fdsn_url + '?' + qs)
        except urllib2.HTTPError as err:
            print err
            self.fail()

        response = fd.read()
        resp = json.loads(response)
        #print resp
        self.assertEqual(len(resp), num+1) # Extra row for the JSON header.


    def test_events_mindepth1(self):
        """Specify only deep events; CSV output"""
        params = {'mindepth': 15}

        qs = urllib.urlencode(params)
        try:
            fd = urllib2.urlopen(self.fdsn_url + '?' + qs)
        except urllib2.HTTPError as err:
            print err
            self.fail()

        response = fd.read()
        #print "Response:\n", response
        self.assertGreater(len(response.split("\n")), 2)

    def test_events_maxdepth1(self):
        """Specify only shallow events; CSV output"""
        z = 50
        params = {'maxdepth': z}

        qs = urllib.urlencode(params)
        try:
            fd = urllib2.urlopen(self.fdsn_url + '?' + qs)
        except urllib2.HTTPError as err:
            print err
            self.fail()

        response = fd.read()
        #print "Response:\n", response
        self.assertGreater(len(response.split("\n")), 2)

    def test_events_mindepthj(self):
        """Specify only deep events; JSON output"""
        z = 15
        params = {'format': 'json',
                  'mindepth': z}

        qs = urllib.urlencode(params)
        response = urllib2.urlopen(self.fdsn_url + '?' + qs).read()
        #print "Response:\n", response
        resp = json.loads(response)
        col = self.expected_header.index('depth')
        self.assertEqual(resp[0][col], 'depth')
        for ev in resp[1:]:
            self.assertGreaterEqual(ev[col], z)

    def test_events_maxdepthj(self):
        """Specify only shallow events; JSON output"""
        z = 50
        params = {'format': 'json',
                  'maxdepth': z}
        col = self.expected_header.index('depth')

        qs = urllib.urlencode(params)
        response = urllib2.urlopen(self.fdsn_url + '?' + qs).read()
        #print "Response:\n", response
        resp = json.loads(response)
        self.assertEqual(resp[0][col], 'depth')
        for ev in resp[1:]:
            self.assertLessEqual(ev[col], z)

    def test_events_minmaxlat(self):
        """Specify only northerly/southerly events; JSON output"""
        lat = 42.0
        col = self.expected_header.index('latitude')     # JSON output column for latitude

        for what in ('minlat', 'maxlat'):
            params = {'format': 'json'}
            params[what] = lat

            qs = urllib.urlencode(params)
            print "qs:", qs
            response = urllib2.urlopen(self.fdsn_url + '?' + qs).read()
            #print "Response:\n", response
            resp = json.loads(response)
            self.assertEqual(resp[0][col], 'latitude')
            for ev in resp[1:]:
                if what == 'minlat':
                    self.assertGreaterEqual(ev[col], lat)
                elif what == 'maxlat':
                    self.assertLessEqual(ev[col], lat)

    def test_events_minmaxlong(self):
        """Specify only easterly/westerly events; JSON output"""
        lon = 11.0
        col =  self.expected_header.index('longitude')     # JSON output column for longitude

        for what in ('minlon', 'maxlon'):
            params = {'format': 'json'}
            params[what] = lon

            qs = urllib.urlencode(params)
            print "qs:", qs
            response = urllib2.urlopen(self.fdsn_url + '?' + qs).read()
            #print "Response:\n", response
            resp = json.loads(response)
            self.assertEqual(resp[0][col], 'longitude')
            for ev in resp[1:]:
                if what == 'minlon':
                    self.assertGreaterEqual(ev[col], lon)
                elif what == 'maxlon':
                    self.assertLessEqual(ev[col], lon)

    def test_events_start(self):
        """As we increase time window, number of events must not decrease"""

        params = {'end': '2014-03-01',
                  'start': '2014-02-28',
                  'format': 'json'}
        qs = urllib.urlencode(params)
        response = urllib2.urlopen(self.fdsn_url + '?' + qs).read()
        resp = json.loads(response)
        num = len(resp)
        self.assertGreater(num, 0)
        for start_date in ('2014-02-27',
                           '2014-02-26',
                           '2014-02-25',
                           '2014-02-21',
                           '2014-02-14',
                           '2014-02-01',
                           '2014-01-15',):
            params['start'] = start_date
            qs = urllib.urlencode(params)
            response = urllib2.urlopen(self.fdsn_url + '?' + qs).read()
            resp = json.loads(response)
            num_new = len(resp)
            print "Start = %s; qs='%s'; num=%d" % (start_date, qs, num_new)
            self.assertGreaterEqual(num_new, num)
            num = num_new
            time.sleep(1)

    def test_events_minmag(self):
        """As we increase minmag, number of events must not increase"""

        params = {'start': '2014-01-01',
                  'format': 'json'}
        qs = urllib.urlencode(params)
        response = urllib2.urlopen(self.fdsn_url + '?' + qs).read()
        resp = json.loads(response)
        num = len(resp)
        for mag in (4.0, 5.0, 6.0, 7.0):
            params['minmag'] = mag
            qs = urllib.urlencode(params)
            response = urllib2.urlopen(self.fdsn_url + '?' + qs).read()
            resp = json.loads(response)
            num_new = len(resp)
            print "Mag = %d; qs='%s'; num=%d" % (mag, qs, num_new)
            self.assertLessEqual(num_new, num)
            num = num_new

# ----------------------------------------------------------------------

if __name__ == '__main__':
    _offline = offline()
    if _offline:
        print " *********************************"
        print " *  testEvents.py is *offline*   *"
        print " *********************************"

    suite = None
    # Uncomment one of the following to test just that class:
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestEventData)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestEventService)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestEventServiceMeteor)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestDelAzi)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestEventServiceOnline)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestEventServiceBadParams)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestTinyThings)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestAreaCircle)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestCompareServicesOnline)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestEventServiceFDSN)
    if suite:
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    else:
        result = unittest.main(verbosity=1, exit=False).result  # Requires Python 2.7?

    num_run = result.testsRun
    num_failures = len(result.failures)
    num_errors = len(result.errors)

    if num_errors == 0 and num_failures == 0:
        print "Hooray, no errors or failures found. Have an early lunch!"
    else:
        print "%i Error(s) %i failure(s) found, %i run." % (num_errors, num_failures, num_run)
