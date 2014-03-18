#!/usr/bin/env python
#
# Metadata module for the Arclink web interface
#
# Begun by Javier Quinteros, GEOFON team, June 2013
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------


"""Metadata module for the ArcLink web interface

(c) 2013, 2014 GEOFON team, GFZ Potsdam

Exports the functions needed by the Javascript running in the web-browser.
All the functions must be called via an URL with the following format
http://SERVER/[path/to/]wsgi/metadata/function?parameters
The most important thing about this module is the implementation of an
internal Cache of the inventory in order to avoid queries to an Arclink
server and to process the inventory XML file every time. All the information
is kept in memory.

The list of functions exported by this module is:
- networktypes: different network types
- sensortypes: different sensor types
- networks: list of networks for the menus based on parameters
- stations: list of stations for the menus based on parameters
- streams: list of streams for the menus based on parameters
- query: list of resulting streams to form a package
- phases: list of phases available to use in "Relative mode"
- export: downloads a file with the selected stations/streams
- timewindows: prepares time windows for each (event, stream)


This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2, or (at your option)
any later version. For more information, see http://www.gnu.org/

"""

##################################################################
#
# First all the imports
#
##################################################################

import datetime
import json

import wsgicomm
import seiscomp3.Seismology
import seiscomp3.Math as Math
from seiscomp import logs
from seiscomp.xmlparser import DateTimeAttr


class MyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return DateTimeAttr.toxml(obj)

        return json.JSONEncoder.default(self, obj)


class WI_Module(object):
    def __init__(self, wi):
        wi.registerAction("/metadata/networktypes", self.networktypes)
        wi.registerAction("/metadata/sensortypes", self.sensortypes)
        wi.registerAction("/metadata/phases", self.phases)
        wi.registerAction("/metadata/networks", self.getNetworks)
        wi.registerAction("/metadata/stations", self.getStations)
        wi.registerAction("/metadata/streams", self.getStreams)
        wi.registerAction("/metadata/query", self.query)
        wi.registerAction("/metadata/import", self.upload_selection)
        wi.registerAction("/metadata/export", self.download_selection)
        wi.registerAction("/metadata/timewindows", self.timewindows)

        self.max_lines = wi.getConfigInt('js.request.totalLineLimit', 10000)

        self.ic = wi.ic
        self.ttt = seiscomp3.Seismology.TravelTimeTable()


    def networktypes(self, envir, params):
        """Returns the available types of networks.

        Input: nothing
        Output: list in JSON format. Every item in the list has four columns.
                CODE, DESCRIPTION, TEMPORARY, RESTRICTED

        Example:
        [["all", "All nets", null, null],
         ["virt", "Virtual nets", null, null],
         ["perm", "All permanent nets", true, null],
         ["temp", "All temporary nets", false, null],
         ["open", "All public nets", null, false],
         ["restr", "All non-public nets", null, true],
         ["permo", "Public permanent nets", true, false],
         ["tempo", "Public temporary nets", false, false],
         ["permr", "Non-public permanent nets", true, true],
         ["tempr", "Non-public temporary nets", false, true]]

        Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

        """

        return json.dumps(self.ic.nettypes)



    def sensortypes(self, envir, params):
        """Returns the available sensor types.

        Input: nothing
        Output: list in JSON format. Every item in the list has two columns.
                CODE, DESCRIPTION

        Example:
        [["all", "Any"],
         ["VBB", "Very broad band"],
         ["BB", "Broad band"],
         ["VBB BB", "Very Broad band and Broad band"],
         ["BB SM", "Broad band / Strong motion"],
         ["SP", "Short Period"],
         ["SM", "Strong motion"],
         ["OBS", "Ocean bottom seismometer"]]

        Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

        """

        return json.dumps(self.ic.senstypes)


    def phases(self, envir, params):
        """Returns the available types of phases.

        Input: nothing
        Output: list in JSON format. Every item in the list has two columns.
                CODE, DESCRIPTION

        Example:
        [["P", "P/Pdiff"],
         ["S", "S/Sdiff"]]

        Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

        """

        return json.dumps(self.ic.phases)


    def getNetworks(self, envir, params):
        """Returns the available networks which pass the filter criteria in params.

        Input: start={int}
               end={int}
               networktype={string}
        Output: list in JSON format. Every item in the list has two columns.
                The first row is fixed and contains the "all" option.
                CODE, DESCRIPTION

        Example:
        [["all", "All Networks"],
         ["3A-1980-None", "3A   (1980) - RESIF - SISMOB mobile antenna [RESIF]"],
         ["AB-1980-None", "AB   (1980) - National Seismic Network of Azerbaijan [ODC]"]]

        Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

        """

        return json.dumps( self.ic.getNetworks(params) )


    def getStations(self, envir, params):
        """Returns the available stations which pass the filter criteria in params.

        Input: start={int}
               end={int}
               networktype={string}
               [network={string}]
        Output: list in JSON format. Every item in the list has two columns.
                The first row is fixed and contains the "all" option.
                CODE, DESCRIPTION

        Example:
        [("all", "All Stations"),
         ("AB-1980-None-GANJ", "GANJ  AB Ganja, Azerbaijan (2003)"),
         ("AB-1980-None-QZX", "QZX   AB Qazah, Azerbaijan (2010)")]

        Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

        """

        return json.dumps( self.ic.getStations(params) )


    def getStreams(self, envir, params):
        """Returns the available streams which pass the filter criteria in params.

        Input: start={int}
               end={int}
               networktype={string}
               [network={string}]
               [station={string}]
        Output: list in JSON format. The stream code is considered to be formed
                by the first two letters, being the third one the orientation.
                Every item in the list has one column.
                STREAMCODE

        Example:
        ["BH",
         "LH",
         "HH",
         "VH"]

        Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

        """

        return json.dumps( self.ic.getStreams(params) )


    def query(self, envir, params):
        """Returns the stations/streams which pass the filter criteria in params.

           Input: start={int}
                  end={int}
                  [network={string}]
                  [networktype={string}]
                  [station={string}]
                  [sensortype={string}]
                  [streams={stream1,stream2,...}]
                  [minlat={float}]
                  [maxlat={float}]
                  [minlon={float}]
                  [maxlon={float}]
                  [minradius={float}]
                  [maxradius={float}]
                  [minazimuth={float}]
                  [maxazimuth={float}]
                  [preferedsps={int}]
                  [events=<event data sent as POST>]

        Output: list in JSON format. Every item in the list has ten columns.
                ID, NETCODE, STATIONCODE, LATITUDE, LONGITUDE, RESTRICTED,
                NETCLASS, ARCHIVE, NETOPERATOR, STREAMS.
                STREAMS is a list with the available channels in a
                two-characters format. e.g. ["BH","HH","LN"].

        """

        result = self.ic.getQuery(params)

        # If there is no data available send a 204 error.
        # There is always one line containing the headers
        if len(result) <= 1:
            raise wsgicomm.WIContentError('No stations were found.', 0)

        return json.dumps( result )


    def upload_selection(self, envir, params):
        """Returns the stations/streams which were received in the uploaded file

        Input: file={file}

        Output: list in JSON format. Every item in the list has ten columns.
                ID, NETCODE, STATIONCODE, LATITUDE, LONGITUDE, RESTRICTED,
                NETCLASS, ARCHIVE, NETOPERATOR, STREAMS.
                STREAMS is a list with the available channels in a
                two-characters format. e.g. ["BH","HH","LN"].

        """

        # result = self.ic.getFromUpload(params)

        # omit empty lines and lines containing only whitespace
        lines = [tuple(line.split()) for line in params['file'].splitlines() if line.strip()]
        # Remove duplicate lines
        nslcSet = set(lines)

        # Create a set of stations to call getQuery
        nsSet = set([(nslc[0], nslc[1]) for nslc in nslcSet])
        # and transform it to an ordered list
        nsList = sorted(nsSet)

        # Save stations already visited to avoid duplication by different
        # epochs
        stats = list()
        statsSet = set()

        while len(nsList):
            # Consumes all the stations
            n, s = nsList.pop(0)

            # To make notation shorter
            ptNets = self.ic.networks
            ptStats = self.ic.stations

            # Cycle through networks
            for net in ptNets:
                # Check if I found the network
                if n == net[0]:
                    # A normal network has pointers to first and last child
                    if((net[1] is not None) and (net[2] is not None)):
                        list_of_children = range(net[1], net[2])
                    # A virtual network has a list of children
                    else:
                        list_of_children = net[3]

                    # Cycle through children (stations)
                    for staIdx in list_of_children:
                        sta = ptStats[staIdx]
                        # Check if I found the station
                        if s == sta[4]:

                            # Build key to avoid duplicates due to different epochs! See GE.APE
                            statKey = '%s-%s-%s-%s' % (net[0], net[4], net[5], sta[4])
                            if statKey not in statsSet:
                                # Query for ALL the streams in the station
                                partial = self.ic.getQuery({'network': '%s-%s-%s' % (net[0], net[4], net[5]),
                                                            'station': '%s-%s-%s-%s' % (net[0], net[4], net[5], sta[4])})

                                # Filter by location and channel
                                # Remove header
                                partial = partial[1:]
                                # Loop through the results
                                for idx, parSta in enumerate(partial):
                                    filtStr = list()
                                    filtStrRestr = list()
                                    # Loop through all streams (LOC.CH)
                                    for chIdx, locCh in enumerate(parSta[9]):
                                        auxLoc, auxCh = locCh.split('.')
                                        # Take into account the empty location
                                        # case
                                        if auxLoc == '':
                                            auxLoc = '--'

                                        # Check if this stream is among the
                                        # requested ones
                                        if (net[0], sta[4], auxLoc, auxCh) in nslcSet:
                                            # And add it to the filtered
                                            # streams
                                            filtStr.append(locCh)
                                            # With the proper information about
                                            # restriction
                                            filtStrRestr.append(parSta[10][chIdx])

                                    # Replace the station in the results with a
                                    # new one with filtered streams
                                    if len(filtStr):
                                        partial[idx] = (parSta[0], parSta[1], parSta[2], parSta[3], parSta[4], parSta[5],
                                                        parSta[6], parSta[7], parSta[8], filtStr, filtStrRestr)
                                        # Add results
                                        statsSet.add(statKey)
                                        stats.append(partial[idx])

        # Add header
        stats.insert(0, ('key', 'netcode', 'statcode', 'latitude', 'longitude',
                         'restricted', 'netclass', 'archive', 'netoperator',
                         'streams', 'streams_restricted'))
        # If there is no data available send a 204 error.
        # There is always one line containing the headers
        if len(stats) <= 1:
            raise wsgicomm.WIContentError('No stations were found.', 0)

        return json.dumps(stats)


    def download_selection(self, envir, params):
        """Produce a text/plain file with the selected stations/streams in CSV format.

        Input: streams={list of stream keys in JSON format}
               Every stream key in the list is a tuple with four components. Namely,
               NETWORK_CODE, STATION_CODE, CHANNEL_CODE, LOCATION_CODE
        Output: Nothing.

        Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

        """

        try:
            streams = json.loads(params.get('streams'))
        except:
            raise wsgicomm.WIClientError, "invalid or inexistent values in parameter 'streams'"



        class DownFile(object):
            def __init__(self, text, filename, content_type):
                if not isinstance(text, basestring):
                    raise wsgicomm.WIError, 'Content to download is not of a valid type (string).'

                self.text = iter(text)
                self.size = len(text)
                self.content_type = content_type
                self.filename = filename

            def __iter__(self):
                return self.text

            def next(self):
                self.text.next()


        text = ''

        for nscl in streams:
            try:
                if len(nscl) != 4:
                    raise wsgicomm.WIClientError, "invalid stream: " + str(nscl)

                net = str(nscl[0])
                sta = str(nscl[1])
                cha = str(nscl[2])
                loc = str(nscl[3])

                # Take into account the empty location case
                if loc == '':
                    loc = '--'

            except (TypeError, ValueError):
                raise wsgicomm.WIClientError, "invalid stream: " + str(nscl)

            text += '%s %s %s %s\n' % (net, sta, loc, cha)

        # size = len(text)
        filename = 'stationSelection.csv'
        content_type = 'text/plain' ## + "; charset=us-ascii'  # try charset

        body = DownFile(text = text, filename = filename, content_type = content_type)
        return body


    def __timewindows_tw(self, streams, start_time, end_time):
        result = []

        for nscl in streams:
            try:
                if len(nscl) != 4:
                    raise wsgicomm.WIClientError, "invalid stream: " + str(nscl)

                net = str(nscl[0])
                sta = str(nscl[1])
                cha = str(nscl[2])
                loc = str(nscl[3])

            except (TypeError, ValueError):
                raise wsgicomm.WIClientError, "invalid stream: " + str(nscl)

            streamInfo = self.ic.getStreamInfo(start_time, end_time, net, sta, cha, loc)

            if streamInfo: # stream does exist in this time range
                result.append((start_time, end_time, net, sta, cha, loc, streamInfo['size']))

                if len(result) > self.max_lines:
                    raise wsgicomm.WIClientError, "maximum request size exceeded"

        return result


    def __isphase(self, ttphase, phase):

        # The list of phases P and S has been provided by Joachim per email on 14.08.2013
        # The case of P and a distance larger than 120 deg must be checked outside this function
        # as we do not have this information here.
        if phase == 'P':
            if ttphase in ('P', 'Pg', 'Pb', 'Pn', 'Pdif', 'Pdiff'):
                return True

        elif phase == 'S':
            if ( ttphase in ('S', 'Sg', 'Sb', 'Sn', 'Sdif', 'Sdiff') or ttphase.startswith('SKS') ):
                return True

        else:
            raise wsgicomm.WIClientError, 'Wrong phase received! Only "P" and "S" are implemented.'

        return False


    def __timewindows_ev(self, streams, events, startphase, startoffset, endphase, endoffset):
        """Helper function to calculate time windows related to events.

        Input: streams={list of stream keys}
               events={list of events} # [[lat, lon, depth, time],..]
               startphase={string}     # 'P' or 'S'
               startoffset={int}       # time in minutes to start time window.
                                       # POSITIVE if AFTER arrival of 'startphase' at station.
               endphase={string}       # 'P' or 'S'
               endoffset={int}         # time in minutes to end time window.
                                       # POSITIVE if AFTER arrival of 'endphase' at station.

	    Output: list of start and end times per channel, AND estimated data volume,
                (start_time, end_time, net, sta, cha, loc, streamInfo['size'])

	    NOTE 1: stream is a list of [net, sta, cha, loc] instead of nslc here!
	    NOTE 2: There are many redundant time window computations for multiple streams at the same location

        """

        result = []

        for ev in events:
            try:
                if len(ev) != 4:
                    raise wsgicomm.WIClientError, "invalid event: " + str(ev)

                ev_lat = float(ev[0])
                ev_lon = float(ev[1])
                ev_dep = float(ev[2])
                ev_time = DateTimeAttr().fromxml(ev[3])

            except (TypeError, ValueError):
                raise wsgicomm.WIClientError, "invalid event: " + str(ev)

            for nscl in streams:
                try:
                    if len(nscl) != 4:
                        raise wsgicomm.WIClientError, "invalid stream: " + str(nscl)

                    net = str(nscl[0])
                    sta = str(nscl[1])
                    cha = str(nscl[2])
                    loc = str(nscl[3])

                except (TypeError, ValueError):
                    raise wsgicomm.WIClientError, "invalid stream: " + str(nscl)

                # we don't have actual time window yet, just use ev_time to get the coordinates
                streamInfo = self.ic.getStreamInfo(ev_time, ev_time, net, sta, cha, loc)

                if streamInfo is None: # stream is not available
                    continue

                st_lat = streamInfo['latitude']
                st_lon = streamInfo['longitude']
                st_alt = streamInfo['elevation']

                start_time = None
                end_time = None

		# Assumption here is that compute() returns phases sorted by time.
		# Therefore breaking after the first gives the earliest phase in
		# the set defined in __isphase().
		# FIXME: Combine startphase and endphase logic into function+loop?

                # Compute in delta the distance between event and station
                delta = Math.delazi(ev_lat, ev_lon, st_lat, st_lon)[0]
                # Threshold distance in degrees at which PKP arrives earlier than P and friends
                # (see Joachim's email - 14.08.2013)
                delta_threshold = 120

		try:
                    ttlist = self.ttt.compute(ev_lat, ev_lon, ev_dep, st_lat, st_lon, st_alt)
                except Exception, e:
                    logs.error("/metadata/timewindows: exception from ttt.compute(): " + str(e))
                    continue

                try:
                    for tt in ttlist:
                        if (startphase == 'P') and (delta >= delta_threshold):
                            if tt.phase.startswith('PKP') or tt.phase.startswith('PKiKP'):
                                start_time = ev_time + datetime.timedelta(seconds=tt.time+startoffset*60)
                                break

                        elif (startphase == 'S') or ((startphase == 'P') and (delta < delta_threshold)):
                            if self.__isphase(tt.phase, startphase):
                                start_time = ev_time + datetime.timedelta(seconds=tt.time+startoffset*60)
                                break

                        else:
                            raise wsgicomm.WIClientError, 'Wrong startphase received! Only "P" and "S" are implemented.'

                    for tt in ttlist:
                        if (endphase == 'P') and (delta >= delta_threshold):
                            if tt.phase.startswith('PKP') or tt.phase.startswith('PKiKP'):
                                end_time = ev_time + datetime.timedelta(seconds=tt.time+endoffset*60)
                                break


                        elif (endphase == 'S') or ((endphase == 'P') and (delta < delta_threshold)):
                            if self.__isphase(tt.phase, endphase):
                                end_time = ev_time + datetime.timedelta(seconds=tt.time+endoffset*60)
                                break

                        else:
                            raise wsgicomm.WIClientError, 'Wrong endphase received! Only "P" and "S" are implemented.'

                except Exception, e:
                    logs.error("/metadata/timewindows: " + str(e))
                    continue

                if start_time is None:
                    logs.error("/metadata/timewindows: did not find startphase '%s' for %s" % (startphase, str((ev_lat, ev_lon, ev_dep, st_lat, st_lon, st_alt))))

                if end_time is None:
                    logs.error("/metadata/timewindows: did not find endphase '%s' for %s" % (endphase, str((ev_lat, ev_lon, ev_dep, st_lat, st_lon, st_alt))))

                if start_time is not None and end_time is not None:
                    # retry with actual time window
                    streamInfo = self.ic.getStreamInfo(start_time, end_time, net, sta, cha, loc)

                    if streamInfo:
                        result.append((start_time, end_time, net, sta, cha, loc, streamInfo['size']))

                        if len(result) > self.max_lines:
                            raise wsgicomm.WIClientError, "maximum request size exceeded"

        return result

    def __get_param(self, params, conv, name):
        try:
            return conv(params.get(name))

        except (TypeError, ValueError):
            raise ValueError, "invalid " + name


    def timewindows(self, envir, params):
        """ <wsgi root>/metadata/query<?parameters>     ## Metadata query for preparing
                                                     ## request
           Parameters:
               start={datetimestring}
               end={datetimestring}
               streams=JSON
           Response:   JSON

        """

        if 'streams' not in params:
            raise wsgicomm.WIClientError, "missing streams"

        tw_params = ('start', 'end')
        ev_params = ('events', 'startphase', 'startoffset', 'endphase', 'endoffset')

        tw_params_count = reduce(lambda a, b: a + (b in tw_params), params, 0)
        ev_params_count = reduce(lambda a, b: a + (b in ev_params), params, 0)

        if tw_params_count == len(tw_params) and ev_params_count == 0:
            mode = 'tw'

        elif ev_params_count == len(ev_params) and tw_params_count == 0:
            mode = 'ev'

        else:
            raise wsgicomm.WIClientError, "invalid set of parameters"

        try:
            streams = self.__get_param(params, json.loads, 'streams')

            if mode == 'tw':
                dta = DateTimeAttr()
                start_time = self.__get_param(params, dta.fromxml, 'start')
                end_time = self.__get_param(params, dta.fromxml, 'end')

            else:
                events = self.__get_param(params, json.loads, 'events')
                startphase = self.__get_param(params, str, 'startphase')
                startoffset = self.__get_param(params, float, 'startoffset')
                endphase = self.__get_param(params, str, 'endphase')
                endoffset = self.__get_param(params, float, 'endoffset')

        except ValueError, e:
            raise wsgicomm.WIClientError, str(e)

        if mode == 'tw':
            result = self.__timewindows_tw(streams, start_time, end_time)

        else:
            result = self.__timewindows_ev(streams, events, startphase, startoffset, endphase, endoffset)

        if isinstance(result, tuple):
            return result

        try:
            return json.dumps(result, cls=MyJSONEncoder, indent=4)

        except ValueError, e:
            raise wsgicomm.WIInternalError, str(e)
