#!/usr/bin/env python
#
# Run unit tests on the event/parse feature of webinterface.
#
# Begun by Peter L. Evans, August 2013
# <pevans@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

import datetime
import math
import os
import sys
import tempfile
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
        import eventconfig
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




class Leftovers():
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

    def normEvents(self, ev1, ev2):
        """Are two events close in space, time and magnitude?

        This is a weighted norm. One second in time should be about
        the same as a few km/sec in position.

        Move to testHelpers?

        """
        a = 6400.0
        deg2km = math.pi*a/180.0
        c = 4.0  # km/sec
        lat_scale = deg2km/c
        phi = 0.5*(ev1[2] + ev2[2])
        lon_scale = math.cos(phi)*lat_scale
        #      time, mag,  lat,       lon,    depth
        scales = [1, 0.2, lat_scale, lon_scale, 10]

        fmt = '%Y-%m-%dT%H:%M:%S'
        dt1 = datetime.datetime.strptime(ev1[0], fmt)
        dt2 = datetime.datetime.strptime(ev2[0], fmt)

        time_delta = (dt1 - dt2).total_seconds()

        return sum([ (time_delta/scales[0])**2,
grep                     ((ev1[1] - ev2[1])/scales[1])**2,
                    ((ev1[2] - ev2[2])/scales[2])**2,
                    ((ev1[3] - ev2[3])/scales[3])**2,
                    ((ev1[4] - ev2[4])/scales[4])**2  ])


##Tests of file upload should cover:
##
##- length: longer than 500 lines _
##- bad seraptors, unparsable
##- times aren't convertible
##- lats, longs aren't parseable
##- lats longs out of range
##- depths unparsable
##- depths implausible out of range
##- required column doesnt have any data
##- illegal characters!
##- special characters: <, >, &(?) ; ...
##- quote errors
##- comments interspersed? Not supported??
##TODO:
##    - text output format which is reloadable as CSV
##    - test of this too!
##

def inputParamFromFile(fname):
        """Hack needed because I can't send a POST request, so I shove this into QUERY_STRING???

        See "20.6.21. Examples" at <http://docs.python.org/2/library/urllib2> for how to do this better?
        """

        data = ''
        with open(fname, 'r') as fid:
            data = fid.read()
        return 'input='+urllib.quote_plus(data)

def inputParamFromString(s):
    return 'input='+urllib.quote_plus(s)

class TestFileServiceMisc(unittest.TestCase):
    """A mix of test cases that aren't tests of single events.

    Some user-supplied events are good, some are bad.
    We must deal with them appropriately.

    """
    colspec = 'time,latitude,longitude,depth'
    filenames = (os.path.join('samples', 'user0.csv'),
                 os.path.join('samples', 'user1.csv'),
                 )
    goodcount = (4,3,1)

    qs_0 = '&'.join(['format=json', 'columns=%s' % (colspec)])
    env = {'PATH_INFO': 'event/parse'}

    def testMixedEvents(self):
        self.env['QUERY_STRING'] = self.qs_0 + '&' + inputParamFromFile(self.filenames[0])
        body = mod.parse(self.env, cgi.parse_qs(self.env.get('QUERY_STRING')))
        #print_json_obj(body)
        self.assertEqual(count_json_obj2(body[0]), 7*(self.goodcount[0] + 1))

    def testBlankLines(self):
        self.env['QUERY_STRING'] = self.qs_0 + '&' + inputParamFromFile(self.filenames[1])
        body = mod.parse(self.env, cgi.parse_qs(self.env.get('QUERY_STRING')))
        #print_json_obj(body)
        self.assertEqual(count_json_obj2(body[0]), 7*(self.goodcount[1] + 1))

    def testSniff(self):
        """It would be nice to have more direct tests of auto-detection"""
        s = '2013-01-01T00:00:00,1,2,3'
        self.env['QUERY_STRING'] = self.qs_0 + '&' + inputParamFromString(s)
        body = mod.parse(self.env, cgi.parse_qs(self.env.get('QUERY_STRING')))
        self.assertEqual(count_json_obj2(body[0]), 7*(1 + 1))

    def testCommentLines(self):
        pass


class TestFileServiceEvents(unittest.TestCase):
    """For these tests the csv class has already performed
    splitting. Now we need valid time, latitude, longitude and
    depth parameters, or the web interface won't be able to plot,
    sort, or compute travel times."""

    sep = ','
    colspec_basic = "latitude,longitude,depth,time".split(sep)
    opts = {'defaultLimit': 10}

    def testGoodEvents(self):
        dataRows = ('45.0,135.0,10.0,2013-08-01T06:00:00',
                    ' 45.0 , 135.0 , 1.0 ,  2013-08-01T06:00:00 ',
                    '45,135.0,10.0,2013-08-01T06:00:00',
                    '45 N,135.0,10.0,2013-08-01T06:00:00',
                    '45 s,135.0,10.0,2013-08-01T06:00:00',
                    '45 s,210.0,10.0,2013-08-01T06:00:00',
                    '45 s,210.0,10,2013-08-01T06:00:00',
                    '45 s,210.0,0,2013-08-01T06:00:00',
                    '45 s,210.0,,2013-08-01T06:00:00',
                    '45 south,210.0,,2013-08-01T06:00:00',
                    '45 Sausages,210.0,,2013-08-01T06:00:00',
                    '90,115,,2013-08-01T06:00:00',
                    '-90,115,,2013-08-01T06:00:00',
                    '0,115,,2013-08-01T06:00:00',
                    '0,180.0,,2013-01-01T00:00:00',
                    '0,180,,2013-01-01T00:00:00',
                    '0,-180,,2013-01-01T00:00:00',
                    '0,-180.0,,2013-01-01T00:00:00',
                    '4.0,99.0,8.0,2013-08-01T06:00:00',
                    '4.0,99.0,8,2013-08-01T06:00:00',
                    '4.0,99.0,-1.0,2013-08-01T06:00:00',
                    '4.0,99.0,-1,2013-08-01T06:00:00',
                    '45,135,10,2013-08-01 06:00:00',
                    '45,135,10,2013-08-01  06:00:00',
                    )
        for row in dataRows:
            data = row.split(self.sep)  # all items are strings
            r = event.ESFile('file', self.opts).check_event(self.colspec_basic, data)
            self.assertTrue(r, 'Failed on \'%s\'' % (row))
        #print "good =", len(dataRows)

    def test_good_datetimes(self):
        """Many datetimes should be acceptable."""
        dataRows = ('2013-08-01T06:00:00',
                    '2013-08-01T06:01:00',
                    '2013-08-01T06:01:00 ',
                    '2013-08-01T06:02:00Z',
                    '2013-08-01T06:03:00.00+00:00',
                    '2013-08-01T06:04:00',
                    '2013-08-01T06:05:00',
                    '2013-08-01 06:06:00',
                    '2013-08-01  06:07:00',
                    '2013-08-01 \t 06:07:00',
                    )
        for row in dataRows:
            data = [3.0, 99.0, 10.0, row]
            r = event.ESFile('file', self.opts).check_event(self.colspec_basic, data)
            self.assertTrue(r, 'Failed on \'%s\'' % (row))
        #print "good =", len(dataRows)

    def testBadEvents(self):
        dataRows = ('x,135.0,10.0,2013-08-01T06:00:00',
                    '6.0,x,10.0,2013-08-01T06:00:00',
                    '6.0,99.0,x,2013-08-01T06:00:00',
                    '6.0,99.0,10.0,x',
                    '6.0 E,99.0,10.0,2013-08-01T06:00:00',
                    '99.0,6.0,10.0,2013-08-01T06:00:00',
                    )
        for row in dataRows:
            data = row.split(self.sep)
            r = event.ESFile('file', self.opts).check_event(self.colspec_basic, data)
            self.assertFalse(r, 'Failed to reject \'%s\'' % (row))
        #print "bad =", len(dataRows)


class TestFileService(unittest.TestCase):
    """Are input arguments acceptable to event.parse(),
    does the column spec make sense, etc.
    These tests don't seriously assess whether the 'input' content
    is acceptable as event data - for that see TestFileServiceEvents.

    """
    tempdir = tempfile.gettempdir()
    filenames = []
    colspecs = []
    filelengths = []

    def setUp(self):
        self.filenames.append(os.path.join(self.tempdir, 'test1.csv'))
        fid = open(self.filenames[0], 'w')
        # No quotes around cols 5 and 6 confused Sniffer!
        print >>fid, """Latitude,Longitude,Depth,Mag,name,evid,datetime
30,60,10.0,5.0,'fred','p101','2001-01-01 12:00:00'
45,60,5,5,'north','p102','2002-02-02 12:00:00'
45,65,5,5,'east','p103','2003-03-03 12:00:00'
"""
        fid.close()
        self.colspecs.append("latitude,longitude,depth,ignore,ignore,ignore,time")
        self.filelengths.append(4)

    def inputParamFromFile(self, fname):
        """Hack needed because I can't send a POST request,
        so I'm shove this into the QUERY_STRING???

        See "20.6.21. Examples" at <http://docs.python.org/2/library/urllib2> for how to do this better?
        """
        import urllib

        data = ''
        with open(fname, 'r') as fid:
            data = fid.read()
        return 'input='+urllib.quote_plus(data)

    def tearDown(self):
        os.unlink(self.filenames[0]) ## os.path.join(self.tempdir, 'test1.csv'))
        #for f in self.filenames:
        #    os.unlink(f) ## os.path.join(self.tempdir, 'test1.csv'))

    def test_columns_spec(self):
        for columns in [ self.colspecs[0] ]:
            column_spec = "columns=" + columns
            env = {'PATH_INFO': 'event/parse',
                   'QUERY_STRING': '&'.join(['format=csv',
                                             self.inputParamFromFile(self.filenames[0]),
                                             column_spec])}
            params = cgi.parse_qs(env.get('QUERY_STRING', ''))
            body = mod.parse(env, params)

    def test_columns_bad_spec(self):
        """Mandatory columns longitude,latitude,time are required."""
        E_LONGITUDE = "Exactly one 'longitude' is required"
        E_LATITIUDE = "Exactly one 'latitude' is required"
        E_TIME = "Exactly one 'time' is required"
        E_EXTRA = "Improper name in the 'columns' specifier"
        testList = [ ("latitude,depth,ignore,ignore,time", E_LONGITUDE),
                     ("ignore,longitude,ignore,time",      E_LATITIUDE),
                     ("longitude,latitude,time,extra",     E_EXTRA),
                     ("ignore",                            E_LATITIUDE),
                     ("nosuchname,ignore",                 E_EXTRA),
                     ("longitude,latitude,time,time",      E_TIME),
                     ("latitude,latitude,longitude,time",  E_LATITIUDE),
                     ("longitude,longitude,latitude,time", E_LONGITUDE),
                     ("depth,depth",                       E_LATITIUDE),
                     ]
        for t in testList:
            column_spec = "columns=" + t[0]
            env = {'PATH_INFO': 'event/parse',
                   'QUERY_STRING': '&'.join(['format=csv',
                                             self.inputParamFromFile(self.filenames[0]),
                                             column_spec])}
            if test_verbosity > 3:
                print column_spec
            params = cgi.parse_qs(env.get('QUERY_STRING', ''))
            with self.assertRaises(wsgicomm.WIError) as cm:
                body = mod.parse(env, params)
            ebody = "".join(cm.exception.body)
            if test_verbosity > 1:
                print short_error_body(ebody)
            self.assertTrue(ebody.startswith('Error 400:'))
            self.assertGreater(ebody.find(t[1]), -1, 'Expected error string "'+t[1]+'" not found')

    def test_file_good_csv(self):
        """Good input file and parameters, CSV output"""
        column_spec = "columns=" + self.colspecs[0]
        env = {'PATH_INFO': 'event/parse',
               'QUERY_STRING': 'format=csv&' + self.inputParamFromFile(self.filenames[0]) + '&' + column_spec}
        params = cgi.parse_qs(env.get('QUERY_STRING', ''))
        body = mod.parse(env, params)
        #print "test_file_good_csv body", body
        self.assertEqual(count_lines(body), self.filelengths[0] + 1)  # +1 for the final "# Lines: 3".

    def test_file_good_json(self):
        """Good input file and parameters, JSON output"""
        column_spec = "columns=" + self.colspecs[0]
        env = {'PATH_INFO': 'event/parse',
               'QUERY_STRING': 'format=json&'+ self.inputParamFromFile(self.filenames[0]) + '&' + column_spec}
        params = cgi.parse_qs(env.get('QUERY_STRING', ''))
        body = mod.parse(env, params)
        #print "test_file_good_json body", body
        self.assertEqual(count_json_obj2(body[0]), 7*self.filelengths[0])

    def test_file_samples_eqinfo(self):
        for fname in ['eqinfo_sample.csv']:
            env = {'PATH_INFO': 'event/parse',
                   'QUERY_STRING': '&'.join(['format=csv',
                                             'columns=ignore,ignore,ignore,ignore,time,latitude,longitude,depth,ignore',
                                             self.inputParamFromFile(os.path.join('samples', fname))])}
        params = cgi.parse_qs(env.get('QUERY_STRING', ''))
        body = mod.parse(env, params)
        self.assertEqual(count_lines(body), 28)  # 26 events


# ----------------------------------------------------------------------

if __name__ == '__main__':
    _offline = offline()
    if _offline:
        print " *************************************"
        print " *  testEventParse.py is *offline*   *"
        print " ************************************"

    suite = None
    # Uncomment one of the following to test just that class:
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestFileService)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestFileServiceEvents)
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestFileServiceMisc)
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
