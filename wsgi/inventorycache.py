#!/usr/bin/env python
#
# InventoryCache for the Arclink web interface
#
# Begun by Javier Quinteros, GEOFON team, June 2013
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------


"""InventoryCache for the Arclink web interface

(c) 2013 GEOFON, GFZ Potsdam

Encapsulate and manage the information of networks,
stations, locations and streams read from an Arclink XML file inventory.


This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2, or (at your option) any later
version. For more information, see http://www.gnu.org/

"""

##################################################################
#
# First all the imports
#
##################################################################


import datetime
import os
###import tempfile
import math
import cPickle as pickle
import xml.etree.cElementTree as ET
import json
from collections import defaultdict

import wsgicomm
from seiscomp import logs
import seiscomp3.Math as Math

###tempdir = tempfile.gettempdir()


class InventoryCache(object):
    """Encapsulate and manage the information of networks,
    stations, locations and streams read from an Arclink XML file inventory.

    Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

    """

    def __init__(self, inventory):
        # Arclink inventory file in XML format
        self.inventory = inventory

        # Temporary file to store the internal representation of the cache
        # in pickle format
        ###self.cachefile = os.path.join(tempdir, 'webinterface-cache.bin')
        self.cachefile = os.path.join(os.path.dirname(inventory), 'webinterface-cache.bin')

        # Set how often the Cache should be updated (in seconds)
        self.time2refresh = 3600.0

        # Fake date to force an update the first time
        self.lastUpdated = datetime.datetime(2000, 1, 1)

        # Types of network. The columns are:
        # CODE, DESCRIPTION, PERMANENT, RESTRICTED (1: True; 2: False)
        self.nettypes = [("all", "All nets", None, None),
                         ("virt", "Virtual nets", None, None),
                         ("perm", "All permanent nets", True, None),
                         ("temp", "All temporary nets", False, None),
                         ("open", "All public nets", None, 2),
                         ("restr", "All non-public nets", None, 1),
                         ("permo", "Public permanent nets", True, 2),
                         ("tempo", "Public temporary nets", False, 2),
                         ("permr", "Non-public permanent nets", True, 1),
                         ("tempr", "Non-public temporary nets", False, 1)]

        # List of sensor types
        # Multiple sensortypes in the same line should be separated by space.
        self.senstypes = [('all', 'Any'),
                          ('VBB', 'Very broad band'),
                          ('BB', 'Broad band'),
                          ('VBB BB', 'Very Broad band and Broad band'),
                          ('BB SM', 'Broad band / Strong motion'),
                          ('SP', 'Short Period'),
                          ('SM', 'Strong motion'),
                          ('OBS', 'Ocean bottom seismometer')]

        self.phases = [('P', 'P/Pdiff'),
                       ('S', 'S/Sdiff')]

        # Create/load the cache the first time that we start
        self.update()

    def __indexStreams(self):
        self.streamidx = {}

        for stream in self.streams:
            sensorLoc = self.sensorsLoc[stream[0]]
            station = self.stations[sensorLoc[0]]
            network = self.networks[station[0]]

            # (net,sta,cha,loc)
            key = (network[0], station[4], stream[1], sensorLoc[4])

            try:
                obj = self.streamidx[key]

            except KeyError:
                obj = []
                self.streamidx[key] = obj

            obj.append(stream)

    def update(self):
        """Read the inventory file in XML format and store it in memory.

        All the information of the inventory is read into lists of
        networks, stations, sensor locations and streams. Only the
        necessary attributes are stored. This relies on the idea
        that some other agent should update the inventory file at
        a regular period of time.
        If the XML file have been already processed by other instance of
        this class, we could look for a temporary file containing a memory
        dump of the generated structures, avoiding the time invested in
        the construction.

        """

        # Calculate when the next update should take place
        nextUpdate = self.lastUpdated + datetime.timedelta(
            seconds=self.time2refresh)

        # If the cache is still valid
        if nextUpdate > datetime.datetime.now():
            return

        # Initialize lists
        self.networks = []
        self.stations = []
        self.sensorsLoc = []
        self.streams = []
        self.lastUpdated = datetime.datetime.now()

        start_time = datetime.datetime.now()

        # Look how old the two versions of inventory are.
        # First version: XML file
        xml_time = os.path.getmtime(self.inventory)
        # Second version: A pickle dump of the processed structures in memory
        try:
            pic_time = os.path.getmtime(self.cachefile)
        except:
            pic_time = 0

        lockfile = self.cachefile + '.lock'

        if pic_time > xml_time:
            try:
                if os.path.exists(lockfile):
                    # Go to the whole processing of the XML file because the
                    # pickle version is still being built.
                    raise Exception

                with open(self.cachefile) as cache:
                    self.networks, self.stations, self.sensorsLoc,\
                        self.streams, self.streamidx = pickle.load(cache)
                    logs.info('Inventory loaded from pickle version')
                    return
            except:
                pass

        logs.info('Processing XML: %s' % start_time)

        sensors = {}
        dataloggers = {}
        stationsDict = {}

        # Parse the inventory file
        # Two steps parser is defined. In the first one, a dictionary of
        # sensors and dataloggers is constructed. In the second one, the
        # networks/stations/sensors/streams tree structure is built.
        try:
            invfile = open(self.inventory)
        except IOError:
            msg = 'Error: Arclink-inventory.xml could not be opened.'
            logs.error(msg)
            raise wsgicomm.WIInternalError, msg

        for parsetype in ['SENSDAT', 'NET_STA']:

            # Traverse through the networks
            # get an iterable
            try:
                invfile.seek(0)
                context = ET.iterparse(invfile, events=("start", "end"))
            except IOError:
                msg = 'Error while trying to parse Arclink-inventory.xml.'
                logs.error(msg)
                raise wsgicomm.WIInternalError, msg

            # turn it into an iterator
            context = iter(context)

            # get the root element
            event, root = context.next()

            # Check that it is really an inventory
            if root.tag[-len('inventory'):] != 'inventory':
                msg = 'The file parsed seems not to be an inventory (XML).'
                logs.error(msg)
                raise wsgicomm.WIInternalError, msg

            # Extract the namespace from the root node
            namesp = root.tag[:-len('inventory')]

            for event, netw in context:
                # The tag of this node could actually be "network" or
                # "stationGroup". Now it is not being checked because
                # we need all the data, but if we need to filter, this
                # is the place.
                #
                if event == "end":
                    if parsetype == 'NET_STA' and \
                       netw.tag == namesp + 'network':

                        # Extract the year from start
                        try:
                            start_year = netw.get('start')
                            start_year = int(start_year[:4])
                        except:
                            start_year = None

                        # Extract the year from end
                        try:
                            end_year = netw.get('end')
                            end_year = int(end_year[:4])
                        except:
                            end_year = None

                        # Cast the attribute restricted
                        try:
                            if netw.get('restricted').lower() == 'true':
                                restricted = 1
                            elif netw.get('restricted').lower() == 'false':
                                restricted = 2
                            else:
                                restricted = None
                        except:
                            restricted = None

                        # Append the network to the list of networks
                        self.networks.append([netw.get('code'),
                                             len(self.stations), None, None,
                                             start_year, end_year,
                                             netw.get('description'),
                                             restricted, netw.get('netClass'),
                                             netw.get('archive'),
                                             netw.get('institutions')])

                        last_child_station = len(self.stations)

                        # Traverse through the stations
                        for stat in netw.findall(namesp + 'station'):
                            # Extract the year from start
                            try:
                                stat_start_string = stat.get('start')
                                stat_start_date = datetime.datetime.strptime(
                                    stat_start_string, '%Y-%m-%dT%H:%M:%S.%fZ')
                            except:
                                stat_start_date = None

                            # Extract the year from end
                            try:
                                stat_end_string = stat.get('end')
                                stat_end_date = datetime.datetime.strptime(
                                    stat_end_string, '%Y-%m-%dT%H:%M:%S.%fZ')
                            except:
                                stat_end_date = None

                            # Extract latitude
                            try:
                                lat = float(stat.get('latitude'))
                            except:
                                lat = None

                            # Extract longitude
                            try:
                                lon = float(stat.get('longitude'))
                            except:
                                lon = None

                            # Extract elevation
                            try:
                                elevation = float(stat.get('elevation'))
                            except:
                                elevation = None

                            stationsDict[stat.get('publicID')] = len(self.stations)

                            # Cast the attribute restricted
                            try:
                                if stat.get('restricted').lower() == 'true':
                                    restricted = 1
                                elif stat.get('restricted').lower() == 'false':
                                    restricted = 2
                                else:
                                    restricted = None
                            except:
                                restricted = None

                            # Only store a reference to the network in the
                            # first column
                            self.stations.append( [len(self.networks)-1, len(self.sensorsLoc), None, None, stat.get('code'), lat, lon, stat.get('description'), stat_start_date, stat_end_date, elevation, restricted] )
                            last_child_station += 1

                            last_child_sensor = len(self.sensorsLoc)
                            for sensor in stat.findall(namesp + 'sensorLocation'):
                                # A reference to the containing station is in the first column
                                self.sensorsLoc.append( [len(self.stations)-1, len(self.streams), None, None, sensor.get('code')] )
                                last_child_sensor += 1

                                last_child_stream = len(self.streams)
                                for stream in sensor.findall(namesp + 'stream'):
                                    sens_type = sensors.get(stream.get('sensor'))

                                    try:
                                        denom = float(stream.get('sampleRateDenominator'))
                                        numer = float(stream.get('sampleRateNumerator'))
                                    except:
                                        denom = None
                                        numer = None

                                    try:
                                        start_string = stream.get('start')
                                        start_date = datetime.datetime.strptime(start_string, '%Y-%m-%dT%H:%M:%S.%fZ')
                                    except:
                                        start_date = None

                                    try:
                                        end_string = stream.get('end')
                                        end_date = datetime.datetime.strptime(end_string, '%Y-%m-%dT%H:%M:%S.%fZ')
                                    except:
                                        end_date = None


                                    # Cast the attribute restricted
                                    try:
                                        if stream.get('restricted').lower() == 'true':
                                            restricted = 1
                                        elif stream.get('restricted').lower() == 'false':
                                            restricted = 2
                                        else:
                                            restricted = None
                                    except:
                                        restricted = None

                                    self.streams.append( (len(self.sensorsLoc)-1, stream.get('code'), sens_type, denom, numer, dataloggers.get(stream.get('datalogger')), start_date, end_date, restricted) )
                                    last_child_stream += 1
                                    stream.clear()

                                self.sensorsLoc[-1][2] = last_child_stream
                                sensor.clear()

                                # Check if there is at least one stream. Otherwise remove sensor.
                                # This case can happen when there are only auxStreams instead of streams
                                if self.sensorsLoc[-1][1] == self.sensorsLoc[-1][2]:
                                    del self.sensorsLoc[-1]
                                    last_child_sensor -= 1

                            self.stations[-1][2] = last_child_sensor
                            stat.clear()

                            # Check if there is at least one sensor. Otherwise remove station.
                            # This case can happen when there are only auxStreams instead of streams
                            if self.stations[-1][1] == self.stations[-1][2]:
                                del self.stations[-1]
                                last_child_station -= 1


                        self.networks[-1][2] = last_child_station
                        netw.clear()

                    if parsetype == 'SENSDAT' and netw.tag == namesp + 'sensor':
                        sensors[netw.get('publicID')] = netw.get('type')

                        netw.clear()

                    if parsetype == 'SENSDAT' and netw.tag == namesp + 'datalogger':
                        dataloggers[netw.get('publicID')] = netw.get('description')

                        netw.clear()

                    if parsetype == 'SENSDAT' and netw.tag == namesp + 'stationGroup':

                        # Extract the year from start
                        try:
                            start_year = netw.get('start')
                            start_year = int(start_year[:4])
                        except:
                            start_year = None

                        # Extract the year from end
                        try:
                            end_year = netw.get('end')
                            end_year = int(end_year[:4])
                        except:
                            end_year = None

                        # Fill a list with station ID's. To be replaced later with the index in self.stations
                        virtualStations = []
                        for statRef in netw.findall(namesp + 'stationReference'):
                            virtualStations.append( statRef.get('stationID') )

                        # Up to this moment virtual networks are always permanent
                        self.networks.append( [netw.get('code'), None, None, virtualStations, start_year, end_year, netw.get('description'), False, 'p', 'GFZ', 'GFZ'] )

                        netw.clear()


                    root.clear()

        invfile.close()

        # Resolving station references in virtual networks
        for netw in self.networks:
            if netw[1] is None and netw[2] is None:
                idxs = []
                for stat in netw[3]:
                    idxs.append( stationsDict[stat] )
                netw[3] = idxs


        end_time = datetime.datetime.now()
        logs.info('Done with XML:  %s' % (end_time))  # Python 2.7: (end_time - start_time).total_seconds())

        self.__indexStreams()

        if not os.path.exists(lockfile):
            try:
                lck = open(lockfile, 'w')
                os.chmod(lockfile, 0666)
                lck.close()
            except:
                logs.warning('Error while attempting to create a lockfile (%s). Check whether the inventory is parsed every %d seconds. This could potentialy make some requests slower.' % (lockfile, self.time2refresh))
                return

            with open(self.cachefile, 'wb') as cache:
                os.chmod(self.cachefile, 0666)
                pickle.dump( (self.networks, self.stations, self.sensorsLoc, self.streams, self.streamidx), cache)

            try:
                os.remove(lockfile)
            except:
                logs.error('Error by removing lockfile (%s). Remove it manually or the pickle version will be always skipped.' % lockfile)




    # Method to select networks from the parameters passed
    def __selectNetworks(self, params):
        """Select networks filtered by the input parameters.

        A list of indexes is returned. These indexes indicate the networks that
        satisfy the constraints indicated by the input parameters.

        """

        if self.lastUpdated + datetime.timedelta(seconds=self.time2refresh) < datetime.datetime.now():
            self.update()

        # Check parameters
        # Start year of the period in which the network should contain data
        if 'start' in params:
            try:
                start = int(params.get('start'))
            except:
                raise wsgicomm.WIClientError, 'Error while converting "start" (%s) to integer.' % params.get('start')
        else:
            start = None

        # Last year of the period in which the network should contain data
        try:
            end = int(params.get('end'))
        except:
            end = None

        # With any of these parameters I need to filter on time range
        if start or end:
            # Default values in case they are not provided
            if start is None:
                start = 1900

            if end is None:
                end = datetime.datetime.now().year

            # Swap values if they are in the wrong order
            if start > end:
               aux = start
               start = end
               end = aux


        # Look at the attributes associated with every network type
        try:
            networktype = params.get('networktype')
            if networktype is None:
                 raise Exception

            for nettype in self.nettypes:
                if networktype == nettype[0]:
                    permanent = nettype[2]
                    restricted = nettype[3]
                    break
            else:
                return set()

        except:
            networktype = None
            permanent = None
            restricted = None


        # Select only one network
        try:
            network = params.get('network')
            if network == 'all':
               network = None
        except:
            network = None



        # Filter and save indexes of networks in netsOK
        netsOK = set()
        for i, netw in enumerate(self.networks):
            # If there is a network selected look only at the codes
            if network:
                try:
                    # Extract the three parts of the network parameter
                    (netcode, netstart, netend) = network.split('-')
                    netstart = int(netstart)
                    if netend == 'None':
                        netend = None
                    else:
                        netend = int(netend)

                    # If any of the three parts does not coincide with the current network, skip it
                    if (netcode != netw[0]) or (netstart != netw[4]) or (netend != netw[5]) :
                        continue
                    else:
                        # Once I found the code, insert it in the lists and leave the loop
                        netsOK.add(i)
                        break

                except:
                    continue


            # Discard if start is after the end of the network operation
            if start and netw[5]:
                if netw[5] < start:
                    continue

            # Discard if end is previous than the start of the network operation
            if end and netw[4]:
                if end < netw[4]:
                    continue

            # Discard if the restricted attribute is not the same
            if restricted is not None:
                if netw[7] != restricted:
                    continue

            # Discard if the netClass/permanent attribute is not the same
            if permanent is not None:
                if permanent and (netw[8] == 't'):
                    continue

                if (not permanent) and (netw[8] == 'p'):
                    continue

            # Virtual networks have no pointers to first child (1) and last child (2).
            # They have a list of childs (3)
            if networktype == 'virt':
                if netw[1] is not None or netw[2] is not None:
                    continue

            # All checks have been done, so add the network index to the list
            netsOK.add(i)

        return netsOK





    def __selectStations(self, params):
        """Select stations filtered by the input parameters.

        Returns a set of indexes. These indexes indicate the
        stations that satisfy the constraints indicated by the
        input parameters.

        """

        if self.lastUpdated + datetime.timedelta(seconds=self.time2refresh) < datetime.datetime.now():
            self.update()

        # Check parameters
        # Start year of the period in which the network should contain data
        try:
            start = datetime.datetime(int(params.get('start')), 1, 1, 0, 0, 0)
        except:
            start = None

        # Last year of the period in which the network should contain data
        try:
            end = datetime.datetime(int(params.get('end')), 12, 31, 23, 59, 59)
        except:
            end = None

        # With any of these parameters I need to filter on time range
        if start or end:
            # Default values in case they are not provided
            if start is None:
                start = datetime.datetime(1900, 1, 1, 0, 0, 0)

            if end is None:
                end = datetime.datetime.now()

            # Swap values if they are in the wrong order
            if start > end:
               aux = start
               start = end
               end = aux



        # Select only one station
        try:
            # Split the list of stations if any
            stations = params.get('station').split(',')
            if stations[0] == 'all':
                stations = None
        except:
            stations = None

        # Filter and save indexes of networks in netsOK
        netsOK = self.__selectNetworks(params)
        # codesOK = set()

        statcodesOK = set()
        statsOK = set()

        for i in netsOK:
            # A normal network has pointers to first and last child
            if self.networks[i][1] is not None and self.networks[i][2] is not None:
                list_of_children = range(self.networks[i][1], self.networks[i][2])
            # A virtual network has a list of children
            else:
                list_of_children = self.networks[i][3]


            # Filter and add stations
            for s in list_of_children:

                # Take the real network in which the station is
                # That means, no virtual networks
                realParent = self.stations[s][0]

                # Discard if start is after the end of the network operation
                if start and self.stations[s][9]:
                    if self.stations[s][9] < start:
                        continue

                # Discard if end is previous than the start of the network operation
                if end and self.stations[s][8]:
                    if end < self.stations[s][8]:
                        continue

                # If there is a station selected look only at the codes
                if stations:
                    key = '%s-%s-%s-%s' % (self.networks[realParent][0], self.networks[realParent][4], self.networks[realParent][5], self.stations[s][4])
                    if key not in stations:
                        continue
                    else:
                        # Once I found the code, insert it in the lists and leave the loop
                        statsOK.add(s)


                # Filter duplicated stations
                if (self.networks[realParent][0], self.stations[s][4]) in statcodesOK:
                    continue



                statcodesOK.add( (self.networks[i][0], self.stations[s][4]) )
                statsOK.add(s)

        return statsOK



    def __buildStreamsList(self, statidx, streamFilter, sensortype=None, preferredsps=None, start=None, end=None):
        """Auxiliary function to build a list of streams based on a station index

        Inputs:
          statidx: Station index on self.stations
          streamFilter: a list of tuples with two
                        components. The first one is the location code, while
                        the second one is the two first letters of the
                        channel. For instance, ('00', 'BH')
          sensortype: as received in parameters
          preferredsps: the preferred sampla rate. At least one streams is selected from each station.
          start: start year in datetime format from parameters sent by web client
          end: end year in datetime format from parameters sent by web client

        """

        if sensortype is not None:
            sensortype = sensortype.strip().split(' ')

        first_child_sensor = self.stations[statidx][1]
        last_child_sensor = self.stations[statidx][2]

        loc_ch = []
        spslist = []
        restr = []
        for loc in range(first_child_sensor, last_child_sensor):
            first_child_stream = self.sensorsLoc[loc][1]
            last_child_stream = self.sensorsLoc[loc][2]

            for ch in range(first_child_stream, last_child_stream):

                if streamFilter is not None:
                    if self.streams[ch][1][:2] not in streamFilter:
                        continue

                if sensortype is not None:
                    if (self.streams[ch][2] not in sensortype):
                        continue

                if (self.streams[ch][7] is not None) and (start is not None):
                    if (self.streams[ch][7] < start):
                        continue

                if (self.streams[ch][6] is not None) and (end is not None):
                    if (end < self.streams[ch][6]):
                        continue

                loc_ch.append( '%s.%s' % (self.sensorsLoc[loc][4], self.streams[ch][1]) )
                # Calculate sps for the stream
                try:
                    spslist.append(float(self.streams[ch][4] / self.streams[ch][3]))
                except:
                    spslist.append(None)

                restr.append(self.streams[ch][8])

        # Extra processing to select only one stream per station if there is a preferred sampling rate
        if preferredsps is not None:
            selected = []
            # Find a proper initial value as the best sample rate found
            # In this case, the first sps that is not None
            best_sps = next((x for x in spslist if x is not None), None)

            for posit, sps in enumerate(spslist):
                if sps is not None:
                    # If the sampling rate is the same as the best one just add it to the list
                    if abs(best_sps - preferredsps) == abs(sps - preferredsps):
                        selected.append(posit)
                    # If it is the best one, create a new list containing it and reset best_sps
                    elif abs(best_sps - preferredsps) > abs(sps - preferredsps):
                        best_sps = sps
                        selected = [posit]

            # If there is no information to satisfy the request
            loc_ch = [loc_ch[i] for i in selected]
            restr = [restr[i] for i in selected]

        (loc_ch, restr) = zip(*sorted(zip(loc_ch, restr))) or ([],[])

        return (loc_ch, restr)


    # Visible function that only wraps an internal method that will be used also by "stations"
    def getNetworks(self, params):
        """Get a simple list of networks satisfying the constraints of the input parameters.

        This method is public and appends the necessary
        information to the networks actually selected by
        __selectNetworks. It contains only a couple of columns
        because it is used in the menus.

        """

        netsOK = self.__selectNetworks(params)

        netList = []
        for i in netsOK:
            netList.append( ('%s-%s-%s' % (self.networks[i][0], self.networks[i][4], self.networks[i][5]), '%s%s%s (%s) - %s [%s]' % (self.networks[i][0], '*' if self.networks[i][5] is not None else ' ', '+' if self.networks[i][7] == 1 else ' ', self.networks[i][4], self.networks[i][6], self.networks[i][9]) ) )

        netList.sort()
        netList.insert(0, ('all', 'All Networks'))
        return netList




    # Visible function that only wraps an internal method that will be used also by "stations"
    def getStations(self, params):
        """Get a simple list of stations satisfying the constraints of the input parameters.

        This method is public and appends the necessary
        information to the stations actually selected by
        __selectStations. It contains only a couple of columns
        because it is used in the menus.

        """

        statsOK = self.__selectStations(params)

        statsList = []
        for i in statsOK:
            netw = self.networks[self.stations[i][0]]
            stat = self.stations[i]
            statsList.append( ( '%s-%s-%s-%s' % (netw[0], netw[4], netw[5], stat[4]), '%-5s %s %s (%d)' % (stat[4], netw[0], stat[7], stat[8].year) ) )

        statsList.sort()
        statsList.insert(0, ('all', 'All Stations'))
        return statsList



    def getStreams(self, params):
        """Get a simple list of streams that satisfies the constraints of the input parameters.

        This method is public and appends the necessary
        information to the streams that belong to the stations
        actually selected by __selectStations. It contains only a
        couple of columns because it is used in the menus.

        """

        # Filter and save indexes of stations in statsOK
        statsOK = self.__selectStations(params)

        streamDict = defaultdict(int)

        # Browse the selected stations
        for statidx in statsOK:
            first_child_sensorLoc = self.stations[statidx][1]
            last_child_sensorLoc = self.stations[statidx][2]

            # Browse the children (sensors) of the current station
            for senLocidx in range(first_child_sensorLoc, last_child_sensorLoc):
                first_child_stream = self.sensorsLoc[senLocidx][1]
                last_child_stream = self.sensorsLoc[senLocidx][2]

                # Browse the children (streams) of the current sensor
                for stridx in range(first_child_stream, last_child_stream):
                    streamDict[self.streams[stridx][1][:2]] += 1

        streamList = []
        for w in sorted(streamDict, key=streamDict.get, reverse=True):
            streamList.append(w)

        return streamList



    def getQuery(self, params):
        """Get a list of streams that satisfies the constraints of the input parameters.

        This method is public and appends the necessary
        information to the streams that belong to the stations
        actually selected by __selectStations. It contains many
        columns, as it is the list to show in the construction of
        the request package.

        """

        try:
            start_year = int(params.get('start', 1980))
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error! Start year is invalid.'

        start_date = datetime.datetime(start_year, 1, 1, 0, 0, 0)


        # Build the end date in datetime format
        # Only year-wide windows are allowed here.
        try:
            end_year = int(params.get('end', datetime.datetime.now().year ))
        except:
            raise wsgicomm.WIClientError, 'Error! End year is invalid.'

        end_date = datetime.datetime(end_year, 12, 31, 23, 59, 59)

        # Get the network
        network = params.get('network')

        # Get the station
        station = params.get('station')

        # Get the sensortype
        sensortype = params.get('sensortype')
        if sensortype == 'all':
            sensortype = None

        # Get the preferred sample rate
        try:
            preferredsps = float(params.get('preferredsps'))
        except:
            preferredsps = None

        # Split the list of streams if any
        try:
            streams = params.get('streams').split(',')

        except wsgicomm.WIError:
            raise
        except:
            streams = None

        # Look at the attributes associated with every network type
        try:
            networktype = params.get('networktype')

            if(networktype == 'all') or (networktype is None):
                 networktype = None
            else:
                for nettype in self.nettypes:
                    if networktype == nettype[0]:
                        break
                else:
                    raise Exception

        except:
            msg = 'Wrong value in parameter "networktype"'
            raise wsgicomm.WIClientError, msg

        # Check for latitude and longitude parameters
        try:
            latmin = float(params.get('minlat')) if params.has_key('minlat') else None
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error: minlat must be a float number.'

        try:
            latmax = float(params.get('maxlat')) if params.has_key('maxlat') else None
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error: maxlat must be a float number.'

        try:
            lonmin = float(params.get('minlon')) if params.has_key('minlon') else None
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error: minlon must be a float number.'

        try:
            lonmax = float(params.get('maxlon')) if params.has_key('maxlon') else None
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error: maxlon must be a float number.'


        # Check for radius and azimuth parameters
        try:
            minradius = float(params.get('minradius')) if params.has_key('minradius') else None
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error: minradius must be a float number.'

        try:
            maxradius = float(params.get('maxradius')) if params.has_key('maxradius') else None
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error: maxradius must be a float number.'

        try:
            minazimuth = float(params.get('minazimuth')) if params.has_key('minazimuth') else None
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error: minazimuth must be a float number.'

        try:
            maxazimuth = float(params.get('maxazimuth')) if params.has_key('maxazimuth') else None
        except (TypeError, ValueError):
            raise wsgicomm.WIClientError, 'Error: maxazimuth must be a float number.'

        try:
            events = params.get('events', None)
        except:
            events = None


        # Try to check parameters for different modes of selecting stations
        # One or all stations have been selected and also lat/lon parameters
        if station and (latmin is not None or latmax is not None or lonmin is not None or lonmax is not None):
            raise wsgicomm.WIClientError, 'Error: station and lat/lon parameters are incompatible.'

        # One or all stations have been selected and also radius/azimuth parameters
        if station and (minradius is not None or maxradius is not None or minazimuth is not None or maxazimuth is not None):
            raise wsgicomm.WIClientError, 'Error: station and radius/azimuth parameters are incompatible.'

        # Lat/lon parameters have been selected and also radius/azimuth
        if (latmin is not None or latmax is not None or lonmin is not None or lonmax is not None) and (minradius is not None or maxradius is not None or minazimuth is not None or maxazimuth is not None):
            raise wsgicomm.WIClientError, 'Error: lat/lon and radius/azimuth parameters are incompatible.'


        # These are the two lists to return
        stats = []

        # Filter and save indexes of stations in statsOK
        statsOK = self.__selectStations(params)

        if ('station' in params):
            # Builds a list from the selected stations
            for st in statsOK:
                parent_net = self.stations[st][0]

                (loc_ch, restricted) = self.__buildStreamsList(st, streams, sensortype, preferredsps, start_date, end_date)

                if len(loc_ch):
                    stats.append( ( '%s-%s-%s-%s%s%s' % (self.networks[parent_net][0], self.networks[parent_net][4], self.stations[st][4], self.stations[st][8].year, self.stations[st][8].month, self.stations[st][8].day),  self.networks[parent_net][0], self.stations[st][4], self.stations[st][5], self.stations[st][6], self.networks[parent_net][7],  self.networks[parent_net][8],  self.networks[parent_net][9],  self.networks[parent_net][10], loc_ch, restricted ) )


        elif (latmin is not None and latmax is not None and lonmin is not None and lonmax is not None):

            # statsOK is a set and therefore, there will be no repetitions
            for st in statsOK:
                # Pointer to the parent network
                parent_net = self.stations[st][0]

                # Filter by latitude
                if(self.stations[st][5] < latmin) or (self.stations[st][5] > latmax):
                    continue

                # Filter by longitude
                if(lonmin <= lonmax):
                    if (self.stations[st][6] < lonmin) or (self.stations[st][6] > lonmax):
                        continue
                else:
                    if (self.stations[st][6] < lonmin) and (self.stations[st][6] > lonmax):
                        continue

                (loc_ch, restricted) = self.__buildStreamsList(st, streams, sensortype, preferredsps, start_date, end_date)

                if len(loc_ch):
                    stats.append( ( '%s-%s-%s-%s%s%s' % (self.networks[parent_net][0], self.networks[parent_net][4], self.stations[st][4], self.stations[st][8].year, self.stations[st][8].month, self.stations[st][8].day),  self.networks[parent_net][0], self.stations[st][4], self.stations[st][5], self.stations[st][6], self.networks[parent_net][7],  self.networks[parent_net][8],  self.networks[parent_net][9],  self.networks[parent_net][10], loc_ch, restricted ) )

        elif events is not None:

            events = json.loads(events)

            for st in statsOK:
                # Pointer to the parent network
                parent_net = self.stations[st][0]

                # Retrieve latitude and longitude of station
                slat = self.stations[st][5]
                slon = self.stations[st][6]

                for evt in events:
                    # Retrieve latitude and longitude of event
                    lat = evt[0]
                    lon = evt[1]

                    # Calculate radial distance and azimuth
                    (dist, azi, other) = Math.delazi(slat, slon, lat, lon)

                    if (minradius < dist) and (dist < maxradius) and (minazimuth < azi) and (azi < maxazimuth):
                        (loc_ch, restricted) = self.__buildStreamsList(st, streams, sensortype, preferredsps, start_date, end_date)

                        if len(loc_ch):
                            stats.append( ( '%s-%s-%s-%s%s%s' % (self.networks[parent_net][0], self.networks[parent_net][4], self.stations[st][4], self.stations[st][8].year, self.stations[st][8].month, self.stations[st][8].day),  self.networks[parent_net][0], self.stations[st][4], self.stations[st][5], self.stations[st][6], self.stations[st][11],  self.networks[parent_net][8],  self.networks[parent_net][9],  self.networks[parent_net][10], loc_ch, restricted ) )

                        # Stop the loop through events and go for the next station
                        break

        else:
            raise wsgicomm.WIClientError, 'Error: not enough parameters have been given.'

        stats.sort()
        stats.insert(0, ('key', 'netcode', 'statcode', 'latitude', 'longitude', 'restricted', 'netclass', 'archive', 'netoperator', 'streams', 'streams_restricted') )

        return stats


    def getStreamInfo(self, start_time, end_time, net, sta, cha, loc):
        try:
            stream_epochs = self.streamidx[(net, sta, cha, loc)]

        except KeyError:
            logs.error("%s,%s,%s,%s not found" % (net, sta, cha, loc))
            return None

        for stream in stream_epochs:
            try:
                station = self.stations[self.sensorsLoc[stream[0]][0]]

            except IndexError:
                logs.error("cache inconsistency")
                return None

            # stream_start = datetime.datetime(station[8], 1, 1)
            # stream_end = datetime.datetime(station[9], 1, 1) if station[9] \
            #         else datetime.datetime(2030, 1, 1)
            stream_start = stream[6]
            stream_end = stream[7] if stream[7] is not None else (datetime.datetime.now() + datetime.timedelta(days=365))

            if start_time >= stream_end or end_time <= stream_start:
                continue

            result = {'latitude': station[5],
                      'longitude': station[6],
                      'elevation': station[10]}

            if stream[3] != 0:
                tdiff = end_time - start_time
                tdiff = tdiff.days * 86400 + tdiff.seconds
                samp = float(stream[4]) / float(stream[3])

                # assuming approximately 1 bytes per sample (compressed), 512 bytes record size
                bytesper = 1
                recsize = 512
                result['size'] = int(recsize * math.ceil(float(tdiff * samp * bytesper) / recsize))

            else:
                result['size'] = 0

            return result

        return None

