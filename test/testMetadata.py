import os
import sys
import unittest
#import urllib
import urllib2

sys.path.append(os.path.join('..', 'wsgi'))  # for wsgicomm
sys.path.append(os.path.join('..', 'wsgi', 'modules'))

import metadata
import webinterface  # Gets too much?? Should I reimplement WebInterface here???
import wsgicomm

from testHelpers import *

test_verbosity = 1   # How noisy should the *unittests* be?


# ----------------------------------------------------------------------
class TestMetadata(unittest.TestCase):
    def test_networktypes0(self):
        params = ""
        qs = '&'.join(params)
        env = {'PATH_INFO': 'metadata/networktypes', 'QUERY_STRING': qs}
        params = cgi.parse_qs(qs)
        nt = mod.networktypes(env, params)
        self.assertGreater(count_json_obj(nt), 0)

    def test_sensortypes0(self):
        params = ""
        qs = '&'.join(params)
        env = {'PATH_INFO': 'metadata/sensortypes', 'QUERY_STRING': ''}
        params = cgi.parse_qs(qs)
        st = mod.sensortypes(env, params)
        self.assertGreater(count_json_obj(st), 0)

    # TODO:
    # Test each function with no arguments.
    def test_networks0(self):
        pass

    def test_stations0(self):
        pass

    def test_streams0(self):
        pass

    def test_query0(self):
        pass


class TestMetadata2(unittest.TestCase):
    """Tests with a running service. You can use

    >>> python manage.py -p 8008

    to start the stand-alone server, but this is not ideal. The setUp
    method could do it, but then it would be started and stopped for
    each test ==> SLOW. Perhaps it could start only if not already running.

    """

    def setUp(self):
        self.service_url = 'http://localhost:8008/'
        fd = None
        try:
            print "Trying", self.service_url, '...',
            fd = urllib2.urlopen(self.service_url)
        except urllib2.HTTPError as err:
            if err.code == 404:
                print '404 is okay, service is running.'
                return

        except urllib2.URLError as err:
            if fd:
                code = fd.getcode()
                print 'Got', code
                if code == 404:
                    print '404 is okay, service is running.'
                else:
                    print 'Unexpected response at %s!' % (self.service_url)
                    raise err
            else:
                print 'No service found at %s!' % (self.service_url)
                raise err

    def test_sequence(self):
        """A typical sequence: find the channel types at GE.IMMV.

        This requires a running web service.
        """
        fd = urllib2.urlopen(self.service_url + 'metadata/networks')
        response = fd.read()
        # Expect a long JSON list.
        self.assertGreater(len(response), 10)

        fd = urllib2.urlopen(self.service_url + 'metadata/stations?network=GE-1980-None')
        response = fd.read()
        # Expect a long list of stations.
        self.assertGreater(len(response), 10)

        fd = urllib2.urlopen(self.service_url + 'metadata/streams?station=GE-1980-None-IMMV')
        response = fd.read()
        resp = json.loads(response)
        # Expect a list like this:
        expected = [".BH", ".HH", ".HN", ".LH", ".SH", ".VH"]
        self.assertListEqual(resp, expected)


# ----------------------------------------------------------------------

class TestMetadataTimewindows(unittest.TestCase):

    def test_timewindows0(self):
        params = ('start=2013-04-01', 'end=2013-04-30')
        qs = '&'.join(params)
        env = {'PATH_INFO': 'metadata/timewindows', 'QUERY_STRING': qs}
        params = cgi.parse_qs(qs)
        response = mod.timewindows(env, params)
        if test_verbosity:
            print response

        self.assertEqual(len(response), 2)
        self.assertEqual(response[0], '400 Bad Request')
        self.assertGreater(response[1].find('invalid streams'), -1)

    def test_timewindows1(self):
        params = ['start=2013-04-01 00:00:00', 'end=2013-04-30 00:00:00', ]
        ##params.append("streams=" + urllib.quote_plus(json.dumps(["GE","APE","","BHZ"])))
        params.append("streams=" + json.dumps(["GE","APE","","BHZ"]))
        qs = '&'.join(params)
        env = {'PATH_INFO': 'metadata/timewindows', 'QUERY_STRING': qs}
        params = cgi.parse_qs(qs)
        response = mod.timewindows(env, params)
        if test_verbosity:
            print "QS:", qs
            print "Response:", response

        self.assertGreater(count_json_obj(response), 0)
        if test_verbosity:
            print json.loads(response)

# ----------------------------------------------------------------------

#wi = webinterface.WebInterface(__name__)  # Would be nice, but needs config
wi = webinterface.WebInterface('webinterface')
mod = metadata.WI_Module(wi)

# ----------------------------------------------------------------------

if __name__ == '__main__':

    suite = None
    # Uncomment one of the following to test just that class:
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestMetadata2)

    if suite:
        result = unittest.TextTestRunner().run(suite)
    else:
        result = unittest.main().result

    num_run = result.testsRun
    num_failures = len(result.failures)
    num_errors = len(result.errors)

    if num_errors == 0 and num_failures == 0:
        print "Hooray, no errors or failures found. Have an early dinner!"
    else:
        print "%i Error(s) %i failure(s) found, %i run." % (num_errors, num_failures, num_run)
