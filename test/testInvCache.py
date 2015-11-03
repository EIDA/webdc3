#!/usr/bin/env python
#
# Run unit tests on the inventorycache of webinterface.
#
# Begun by Javier Quinteros, GEOFON team, July 2013
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

import os
import sys
###import tempfile
import datetime
import unittest
from unittestTools import WITestRunner

sys.path.append(os.path.join('..', 'wsgi'))  # for wsgicomm
sys.path.append(os.path.join('..', 'wsgi', 'modules'))

import inventorycache


class InvCacheTests(unittest.TestCase):
    """Test the functionality of inventoryCache.py

    """

    @classmethod
    def setUp(cls):
        "Setting up test"
	if hasattr(cls, 'ic'):
            return

	###tempdir = tempfile.gettempdir()
	picklefile = os.path.join('..', 'data', 'webinterface-cache.bin')
	if os.path.exists(picklefile):
		os.remove(picklefile)
		#print "Removed pickfile %s" % (picklefile)
        cls.ic = inventorycache.InventoryCache(os.path.join('..', 'data', 'Arclink-inventory.xml'))

        print 'Networks: %d' % len(cls.ic.networks)
        print 'Stations: %d' % len(cls.ic.stations)
        print 'Sensors : %d' % len(cls.ic.sensorsLoc)
        print 'Streams : %d' % len(cls.ic.streams)

        cls.networks = 0
        cls.stations = 0
        cls.locations = 0
        cls.streams = 0

        with open('../data/Arclink-inventory.xml') as inv:
            for line in inv:
                if '<ns0:network ' in line:
                    cls.networks += 1
                if '<ns0:stationGroup ' in line:
                    cls.networks += 1
                if '<ns0:station ' in line:
                    cls.stations += 1
                if '<ns0:sensorLocation ' in line:
                    cls.locations += 1
                if '<ns0:stream ' in line:
                    cls.streams += 1


    def testNumberOfNetworksCreated(self):
        "number of networks created"
        self.assertEqual(self.networks, len(self.__class__.ic.networks), 'Wrong number of networks created.')


    def testNumberOfStationsCreated(self):
        "number of stations created"
        self.assertEqual(self.stations, len(self.__class__.ic.stations), 'More stations created (%d) than the ones present in the inventory (%d).' % (len(self.__class__.ic.stations), self.stations) )
        self.assertTrue( (self.stations-len(self.__class__.ic.stations)) < 10, '%d stations skipped from inventory. Check for stations with only auxStreams in the sensors.' % (self.stations-len(self.__class__.ic.stations)) )


    def testNumberOfLocationsCreated(self):
        "number of locations created"
        self.assertEqual(self.locations, len(self.__class__.ic.sensorsLoc), 'More sensors created (%d) than the ones present in the inventory (%d).' % (len(self.__class__.ic.sensorsLoc), self.locations) )
        self.assertTrue( (self.locations-len(self.__class__.ic.sensorsLoc)) < 10, '%d sensors skipped from inventory. Check for sensors with only auxStreams.' % (self.locations-len(self.__class__.ic.sensorsLoc)) )


    def testNumberOfStreamsCreated(self):
        "number of streams created"
        self.assertEqual(self.streams, len(self.__class__.ic.streams), 'Wrong number of streams created.')


    def testNetTypesType(self):
        "type of nettype attribute"
        self.assertEqual(type(self.__class__.ic.nettypes), type([]), 'Attribute nettypes is not a list.')

    def testNetTypesCols(self):
        "number of columns of nettype"
        if hasattr(self.__class__.ic, 'nettypes'):
            for nett in self.__class__.ic.nettypes:
                self.assertEqual(len(nett), 4, 'An instance of nettype does not have 4 columns.')


    def testNetTypesCol1(self):
        "type of columns in every type of net"
        if hasattr(self.__class__.ic, 'nettypes'):
            for nett in self.__class__.ic.nettypes:
                self.assertEqual(type(nett[0]), type(''), 'First column of nettype is not a string.')
                self.assertEqual(type(nett[1]), type(''), 'Second column of nettype is not a string.')
                self.assertTrue( (type(nett[2]) == type(True)) or (type(nett[2]) == type(None)), 'Third column of nettype is not a boolean.')
                self.assertTrue( (type(nett[3]) == type(True)) or (type(nett[3]) == type(None)), 'Fourth column of nettype is not a boolean.')


    def testNetworksType(self):
        "type of networks attribute"
        self.assertEqual(type(self.__class__.ic.networks), type([]), 'Attribute networks is not a list.')


    def testNetworksCols(self):
        "number of columns of networks"
        if hasattr(self.__class__.ic, 'networks'):
            for idx, netw in enumerate(self.__class__.ic.networks):
                self.assertEqual(len(netw), 11, 'An instance of networks does not have 11 columns. (Index: %d)' % idx)


    def testNetworksCol1(self):
        "type of columns in every network"
        if hasattr(self.__class__.ic, 'networks'):
            for idx, netw in enumerate(self.__class__.ic.networks):
                self.assertEqual(type(netw[0]), type(''), 'First column of networks is not a string. (Index: %d)' % idx)

                if netw[1] is not None:
                    self.assertEqual(type(netw[1]), type(1), 'Second column of networks is not an integer. (Index: %d)' % idx)

                if netw[2] is not None:
                    self.assertEqual(type(netw[2]), type(1), 'Third column of networks is not an integer. (Index: %d)' % idx)

                if netw[3] is not None:
                    self.assertEqual(type(netw[3]), type([]), 'Fourth column of networks is not a list. (Index: %d)' % idx)
                    self.assertEqual(type(netw[1]), type(None), 'Second column should be "None" in a virtual network. (Index: %d)' % idx)
                    self.assertEqual(type(netw[2]), type(None), 'Third column should be "None" in a virtual network. (Index: %d)' % idx)
                    # Check the stations in the virtual network
                    for statidx, stat in enumerate(netw[3]):
                        self.assertEqual(type(stat), type(1), 'Pointer to station (Idx: %d) in virtual network (Idx: %d) is not an integer.' % (statidx, idx) )
                else:
                    self.assertNotEqual(type(netw[1]), type(None), 'Second column cannot be "None" in a non-virtual network. (Index: %d)' % idx)
                    self.assertNotEqual(type(netw[2]), type(None), 'Third column cannot be "None" in a non-virtual network. (Index: %d)' % idx)

                self.assertEqual(type(netw[1]), type(netw[2]), 'Second and third columns of networks should be of the same type. (Index: %d)' % idx)

                self.assertEqual(type(netw[4]), type(1), 'Fifth column of networks is not an integer. (Index: %d)' % idx)

                if netw[5] is not None:
                    self.assertEqual(type(netw[5]), type(1), 'Sixth column of networks is not an integer. (Index: %d)' % idx)

                self.assertEqual(type(netw[6]), type(''), 'Seventh column of networks is not a string. (Index: %d)' % idx)

                if netw[7] is not None:
                    self.assertEqual(type(netw[7]), type(1), 'Eight column of networks is not an integer. (Index: %d)' % idx)

                if netw[8] is not None:
                    self.assertEqual(type(netw[8]), type(''), 'Ninth column of networks is not a string. (Index: %d)' % idx)

                self.assertEqual(type(netw[9]), type(''), 'Tenth column of networks is not a string. (Index: %d)' % idx)

                if netw[10] is not None:
                    self.assertEqual(type(netw[10]), type(''), 'Eleventh column of networks is not a string. (Index: %d)' % idx)



    def testNetworkPointersToStations(self):
        "pointers to stations in network metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'networks'):
            for netw in self.__class__.ic.networks:
                if netw[3] is None:
                    if (netw[1] >= netw[2]) or (netw[1] >= len(self.__class__.ic.stations)) \
                       or (netw[2] > len(self.__class__.ic.stations)):
                        errors.add(netw[9] + '.' + netw[0])
        self.assertTrue( len(errors) == 0, 'Wrong values in pointers to stations. Code(s): %s' % sorted(list(errors)))


    def testNetworkStart(self):
        "start year in network metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'networks'):
            for netw in self.__class__.ic.networks:
                if (netw[4] < 1980) or (netw[4] > datetime.datetime.now().year):
                    errors.add(netw[9] + '.' + netw[0])
        self.assertTrue( len(errors) == 0, 'Start years with anomalous values. Code(s): %s' % sorted(list(errors)))


    def testNetworkEnd(self):
        "end year in network metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'networks'):
            for netw in self.__class__.ic.networks:
                if (netw[5] is not None) and ((netw[5] < 1980) or \
                    (netw[4] > netw[5])):
                    errors.add(netw[9] + '.' + netw[0])
        self.assertTrue( len(errors) == 0, 'End years with anomalous values. Code(s): %s' % sorted(list(errors)))


    def testNetworkRestricted(self):
        "restriction in network metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'networks'):
            for netw in self.__class__.ic.networks:
                if not (netw[7] in [True, False]):
                    errors.add(netw[9] + '.' + netw[0])
        self.assertTrue( len(errors) == 0, 'Restricted attribute without information. Code(s): %s' % sorted(list(errors)))


    def testNetworkClass(self):
        "class in network metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'networks'):
            for netw in self.__class__.ic.networks:
                if not (netw[8] in ['p', 't']):
                    errors.add(netw[9] + '.' + netw[0])
        self.assertTrue( len(errors) == 0, 'Netclass attribute without information. Code(s): %s' % sorted(list(errors)))


    def testNetworkArchive(self):
        "archive in network metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'networks'):
            for netw in self.__class__.ic.networks:
                if(netw[9] is None) or (len(netw[9]) == 0):
                    errors.add(netw[0])
        self.assertTrue( len(errors) == 0, 'Archive attribute without information. Code(s): %s' % sorted(list(errors)))


    def testSensTypesType(self):
        "type of senstype attribute"

        self.assertEqual(type(self.__class__.ic.senstypes), type([]), 'Attribute senstypes is not a list.')


    def testSensTypesCols(self):
        "number of columns of senstype"

        if hasattr(self.__class__.ic, 'senstypes'):
            for sens in self.__class__.ic.senstypes:
                self.assertEqual( len(sens), 2, 'An instance of senstype does not have 2 columns.')


    def testSensTypesCol1(self):
        "type of columns in every type of sensor"

        if hasattr(self.__class__.ic, 'senstypes'):
            for sens in self.__class__.ic.senstypes:
                self.assertEqual(type(sens[0]), type(''), 'First column of senstype is not a string.')
                self.assertEqual(type(sens[1]), type(''), 'Second column of senstype is not a string.')


    def testStationsType(self):
        "type of stations attribute"

        self.assertEqual(type(self.__class__.ic.stations), type([]), 'Attribute stations is not a list.')


    def testStationsCols(self):
        "number of columns of stations"

        if hasattr(self.__class__.ic, 'stations'):
            for stat in self.__class__.ic.stations:
                self.assertEqual(len(stat), 11, 'An instance of stations does not have 11 columns.')


    def testStationsCol1(self):
        "type of columns in every stations"

        if hasattr(self.__class__.ic, 'stations'):
            for idx, stat in enumerate(self.__class__.ic.stations):
                self.assertEqual(type(stat[0]), type(1), 'First column of stations is not an integer. (Index: %d; Code: %s)' % (idx, stat[4]))
                self.assertEqual(type(stat[1]), type(1), 'Second column of stations is not an integer. (Index: %d; Code: %s)' % (idx, stat[4]))
                self.assertEqual(type(stat[2]), type(1), 'Third column of stations is not an integer. (Index: %d; Code: %s)' % (idx, stat[4]))
                self.assertEqual(type(stat[3]), type(None), 'Fourth column of stations should be an unused, reserved column. (Index: %d; Code: %s)' % (idx, stat[4]))
                self.assertEqual(type(stat[4]), type(''), 'Fifth column of stations is not a string. (Index: %d; Code: %s)' % (idx, stat[4]))
                self.assertEqual(type(stat[5]), type(1.1), 'Sixth column of stations is not a float. (Index: %d; Code: %s)' % (idx, stat[4]))
                self.assertEqual(type(stat[6]), type(1.1), 'Seventh column of stations is not a float. (Index: %d; Code: %s)' % (idx, stat[4]))
                self.assertEqual(type(stat[7]), type(''), 'Eighth column of stations is not a string. (Index: %d; Code: %s)' % (idx, stat[4]))
                self.assertEqual(type(stat[8]), type(datetime.datetime.now()), 'Ninth column of stations is not a datetime. (Index: %d; Code: %s)' % (idx, stat[4]))

                if stat[9] is not None:
                    self.assertEqual( type(stat[9]), type(datetime.datetime.now()), 'Tenth column of stations has is not a datetime. (Index: %d; Code: %s)' % (idx, stat[4]))

                if stat[10] is not None:
                    self.assertEqual(type(stat[10]), type(1.1), 'Eleventh column of stations is not a float. (Index: %d; Code: %s)' % (idx, stat[4]))


    def testStationPointerToNetwork(self):
        "pointer to network in station metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'stations'):
            for idx, stat in enumerate(self.__class__.ic.stations):
                if (stat[0] >= len(self.__class__.ic.networks)):
                    errors.add('%d/%s' % (idx, stat[4]))
        # Check there are no errors
        self.assertTrue( len(errors) == 0, 'Wrong pointer to parent network. Code(s): %s' % sorted(list(errors)))


    def testStationPointersToSensors(self):
        "pointers to sensors in station metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'stations'):
            for stat in self.__class__.ic.stations:
                if (stat[1] >= stat[2]) or (stat[1] >= len(self.__class__.ic.sensorsLoc)) \
                   or (stat[2] > len(self.__class__.ic.sensorsLoc)):
                    netw = self.__class__.ic.networks[stat[0]]
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4])
        # Check there are no errors
        self.assertTrue( len(errors) == 0, 'Wrong values in pointers to sensors. Code(s): %s' % sorted(list(errors)))


    def testStationLatitude(self):
        "latitude in station metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'stations'):
            for stat in self.__class__.ic.stations:
                if (stat[5] < -90.0) or (stat[5] > 90.0):
                    netw = self.__class__.ic.networks[stat[0]]
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4])
        self.assertTrue( len(errors) == 0, 'Latitude with anomalous values. Code(s): %s' % sorted(list(errors)))


    def testStationLongitude(self):
        "longitude in station metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'stations'):
            for stat in self.__class__.ic.stations:
                if (stat[6] < -180.0) or (stat[6] > 180.0):
                    netw = self.__class__.ic.networks[stat[0]]
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4])
        self.assertTrue( len(errors) == 0, 'Longitude with anomalous values. Code(s): %s' % sorted(list(errors)))


    def testStationStart(self):
        "start date in station metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'stations'):
            for stat in self.__class__.ic.stations:
                if (stat[8].year < 1980) or (stat[8] > datetime.datetime.now()):
                    netw = self.__class__.ic.networks[stat[0]]
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4])
        self.assertTrue( len(errors) == 0, 'Start dates with anomalous values. Code(s): %s' % sorted(list(errors)))


    def testStationEnd(self):
        "end date in station metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'stations'):
            for stat in self.__class__.ic.stations:
                if (stat[9] is not None) and ((stat[9].year < 1980) or \
                    (stat[8] >= stat[9])):
                    netw = self.__class__.ic.networks[stat[0]]
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4])
        self.assertTrue( len(errors) == 0, 'End dates with anomalous values. Code(s): %s' % sorted(list(errors)))


    def testStationDatesInNet(self):
        "timespan inclusion of station w.r.t. network metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'stations') and hasattr(self.__class__.ic, 'networks'):
            for stat in self.__class__.ic.stations:
                netw = self.__class__.ic.networks[stat[0]]
                if (stat[8].year < netw[4]) or ((netw[5] is not None) and (stat[8].year > netw[5])):
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4])
                if netw[5] is not None:
                    if (stat[9] is None) or (stat[9].year > netw[5]):
                        errors.add(netw[9] + '.' + netw[0] + '.' + stat[4])
        self.assertTrue( len(errors) == 0, 'Station operational timespan is not coherent with the network. Code(s): %s' % sorted(list(errors)))



    def testSensorsType(self):
        "type of sensorsLoc attribute"
        self.assertEqual(type(self.__class__.ic.sensorsLoc), type([]), 'Attribute sensorsLoc is not a list.')


    def testSensorsCols(self):
        "number of columns in every sensor"
        if hasattr(self.__class__.ic, 'sensorsLoc'):
            for sens in self.__class__.ic.sensorsLoc:
                self.assertEqual(len(sens), 5, 'An instance of sensorsLoc does not have 5 columns.')


    def testSensorsLocCol1(self):
        "type of columns in every sensor"
        if hasattr(self.__class__.ic, 'sensorsLoc'):
            for idx, sens in enumerate(self.__class__.ic.sensorsLoc):
                self.assertEqual(type(sens[0]), type(1), 'First column of sensors is not an integer. (Index: %d)' % idx)
                self.assertEqual(type(sens[1]), type(1), 'Second column of sensors is not an integer. (Index: %d)' % idx)
                self.assertEqual(type(sens[2]), type(1), 'Third column of sensors is not an integer. (Index: %d)' % idx)
                self.assertEqual(type(sens[3]), type(None), 'Fourth column of sensors should be an unused, reserved column. (Index: %d)' % idx)
                self.assertEqual(type(sens[4]), type(''), 'Fifth column of sensors is not a string. (Index: %d)' % idx)


    def testSensorPointerToStation(self):
        "pointer to station in sensor metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'sensorsLoc'):
            for idx, sens in enumerate(self.__class__.ic.sensorsLoc):
                if (sens[0] >= len(self.__class__.ic.stations)):
                    errors.add('%d/%s' % (idx, sens[4]))
        # Check there are no errors
        self.assertTrue( len(errors) == 0, 'Wrong pointer to parent station. Index(es)/Code(s): %s' % sorted(list(errors)))


    def testSensorsPointersToStreams(self):
        "pointers to streams in sensor metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'sensorsLoc'):
            for sens in self.__class__.ic.sensorsLoc:
                if (sens[1] >= sens[2]) or (sens[1] >= len(self.__class__.ic.streams)) \
                   or (sens[2] > len(self.__class__.ic.streams)):
                        stat = self.__class__.ic.stations[sens[0]]
                        netw = self.__class__.ic.networks[stat[0]]
                        errors.add(netw[9] + '.' + netw[0] + '.' + stat[4] + '.' + sens[4])
        # Check there are no errors
        self.assertTrue( len(errors) == 0, 'Wrong values in pointers to streams. Code(s): %s' % sorted(list(errors)))




    def testStreamsType(self):
        "type of streams attribute"
        self.assertEqual(type(self.__class__.ic.streams), type([]), 'Attribute streams is not a list.')


    def testStreamsCols(self):
        "number of columns in every stream"
        if hasattr(self.__class__.ic, 'streams'):
            for stre in self.__class__.ic.streams:
                self.assertEqual(len(stre), 8, 'An instance of streams does not have 8 columns.')


    def testStreamsCol1(self):
        "type of columns in every stream"
        if hasattr(self.__class__.ic, 'streams'):
            for idx, stre in enumerate(self.__class__.ic.streams):
                self.assertEqual(type(stre[0]), type(1), 'First column of stream is not an integer. (Index: %d)' % idx)
                self.assertEqual(type(stre[1]), type(''), 'Second column of stream is not a string. (Index: %d)' % idx)

                if stre[2] is not None:
                    self.assertEqual( type(stre[2]), type(''), 'Third column of stream is not a string. (Index: %d)' % idx)

                if stre[3] is not None:
                    self.assertEqual( type(stre[3]), type(1.1), 'Fourth column of stream is not a float. (Index: %d)' % idx)
                    self.assertNotEqual( stre[3], 0.0, 'Sample Rate is undefined because denominator=0. (Index: %d)' % idx)

                if stre[4] is not None:
                    self.assertEqual( type(stre[4]), type(1.1), 'Fifth column of stream is not a float. (Index: %d)' % idx)

                if stre[5] is not None:
                    self.assertEqual( type(stre[5]), type(''), 'Sixth column of stream is not a string. (Index: %d)' % idx)

                self.assertEqual(type(stre[6]), type(datetime.datetime.now()), 'Seventh column of stream is not a datetime. (Index: %d)' % idx)

                if stre[7] is not None:
                    self.assertEqual(type(stre[7]), type(datetime.datetime.now()), 'Eighth column of stream is not a datetime. (Index: %d)' % idx)


    def testStreamPointerToSensor(self):
        "pointer to sensor in stream metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'streams'):
            for idx, stre in enumerate(self.__class__.ic.streams):
                if (stre[0] >= len(self.__class__.ic.sensorsLoc)):
                    errors.add('%d/%s' % (idx, stre[4]))
        # Check there are no errors
        self.assertTrue( len(errors) == 0, 'Wrong pointer to parent sensor. Index(es)/Code(s): %s' % sorted(list(errors)))


    def testStreamStart(self):
        "start date in stream metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'streams'):
            for stre in self.__class__.ic.streams:
                if (stre[6].year < 1980) or (stre[6] > datetime.datetime.now()):
                    sens = self.__class__.ic.sensorsLoc[stre[0]]
                    stat = self.__class__.ic.stations[sens[0]]
                    netw = self.__class__.ic.networks[stat[0]]
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4] + '.' + sens[4] + '.' + stre[1] + '(' + str(stre[6].year) + ')')
        self.assertTrue( len(errors) == 0, 'Start dates with anomalous values. Code(s): %s' % sorted(list(errors)))


    def testStreamEnd(self):
        "end date in stream metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'streams'):
            for stre in self.__class__.ic.streams:
                if (stre[7] is not None) and ((stre[7].year < 1980) or \
                    (stre[6] >= stre[7])):
                    sens = self.__class__.ic.sensorsLoc[stre[0]]
                    stat = self.__class__.ic.stations[sens[0]]
                    netw = self.__class__.ic.networks[stat[0]]
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4] + '.' + sens[4] + '.' + stre[1] + '(' + str(stre[6].year) + ')')
        self.assertTrue( len(errors) == 0, 'End dates with anomalous values. Code(s): %s' % sorted(list(errors)))

    def testStreamDatesInStat(self):
        "timespan inclusion of stream w.r.t. station metadata"

        errors = set()
        if hasattr(self.__class__.ic, 'streams') and hasattr(self.__class__.ic, 'sensorsLoc') and hasattr(self.__class__.ic, 'stations'):
            for stre in self.__class__.ic.streams:
                sens = self.__class__.ic.sensorsLoc[stre[0]]
                stat = self.__class__.ic.stations[sens[0]]
                netw = self.__class__.ic.networks[stat[0]]
                if (stre[6] < stat[8]):
                    errors.add(netw[9] + '.' + netw[0] + '.' + stat[4] + '.' + sens[4] + '.' + stre[1])
                if stat[9] is not None:
                    if (stre[7] is not None) and (stre[7] > stat[9]):
                        errors.add(netw[9] + '.' + netw[0] + '.' + stat[4] + '.' + sens[4] + '.' + stre[1])
                    if (stre[6] > stat[9]):
                        errors.add(netw[9] + '.' + netw[0] + '.' + stat[4] + '.' + sens[4] + '.' + stre[1])
        self.assertTrue( len(errors) == 0, 'Stream operational timespan is not coherent with the station. Code(s): %s' % sorted(list(errors)))





# ----------------------------------------------------------------------
def usage():
    print 'testInvCache [-h] [-p]'


if __name__ == '__main__':

    # 0=Plain mode (good for printing); 1=Colourful mode
    mode = 1

    for ind, arg in enumerate(sys.argv):
        if arg in ('-p', '--plain'):
            del sys.argv[ind]
            mode = 0
        elif arg in ('-h', '--help'):
            usage()
            sys.exit(0)

    unittest.main(testRunner=WITestRunner(mode=mode))

