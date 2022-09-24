#!/usr/bin/env python
#
# Functions to update the metadata of WebDC3
#
# Copyright (C) 2014-2019 Javier Quinteros, GEOFON team
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

"""Functions to update the metadata for WebDC3

   :Platform:
       Linux
   :Copyright:
       GEOFON, Helmholtz-Zentrum Potsdam - Deutsches GeoForschungsZentrum GFZ
       <geofon@gfz-potsdam.de>
   :License:
       GNU General Public License, Version 3, 29 June 2007

   This program is free software; you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by the Free
   Software Foundation; either version 3, or (at your option) any later
   version. For more information, see http://www.gnu.org/

.. moduleauthor:: Javier Quinteros <javier@gfz-potsdam.de>, GEOFON, GFZ Potsdam
"""

##################################################################
#
# First all the imports
#
##################################################################

import os
import glob
import datetime
import urllib2 as ul
from urlparse import urlparse
import xml.etree.cElementTree as ET
import logging
import argparse
import pickle
import csv
import json
from collections import deque


def makenetcode(net, year):
    if net[0] in '0123456789XYZ':
        return '%s_%d' % (net, year)
    return net


def makestationcode(sta, year):
    return '%s_%d' % (sta, year)


class ListChans(list):
    # __slots__ = ()

    def __init__(self):
        super(ListChans, self).__init__()
        self.keys = set()

    def extend(self, chas):
        for cha in chas:
            self.append(cha)

    def append(self, cha):
        logging.debug('Try to add channel: %s' % (cha,))
        if (cha[0], cha[1]) in self.keys:
            return
        # for ind, item in enumerate(self):
        #     # If network.station.location-year code is already in the list
        #     if (item[0] == cha[0]) and (item[1] == cha[1]):
        #         return

        # Add location if not present
        logging.debug('Added')
        self.keys.add((cha[0], cha[1]))
        super(ListChans, self).append(cha)


class ListLocs(list):
    __slots__ = ()

    def __init__(self):
        super(ListLocs, self).__init__()

    def extend(self, locs):
        for loc in locs:
            self.append(loc)

    def append(self, loc):
        logging.debug('Try to add location: %s' % loc)
        for ind, item in enumerate(self):
            # If network.station-year code is already in the list
            if (item[0] == loc[0]) and (item[4] == loc[4]):
                return

        # Add location if not present
        logging.debug('Added')
        super(ListLocs, self).append(loc)


class ListStats(list):
    __slots__ = ()

    def __init__(self):
        super(ListStats, self).__init__()

    def extend(self, stats):
        for sta in stats:
            self.append(sta)

    def append(self, sta):
        logging.debug('Try to add station: %s' % sta)
        for ind, item in enumerate(self):
            # If network code is already in the list
            # And also if the station code is the same
            if (item[0] == sta[0]) and (item[4] == sta[4]):
                # Check if it is a different network (temporary)
                # end1 is the end of the station already on the list
                end1 = item[9] if item[9] is not None else datetime.datetime(2999, 1, 1)
                # end2 is the end of the station to be added
                end2 = sta[9] if sta[9] is not None else datetime.datetime(2999, 1, 1)

                # If there is no overlap skip to the next item
                if max(sta[8], item[8]) > min(end1, end2):
                    continue
                # overlap = range(max(sta[8].year, item[8].year), min(end1.year, end2.year)+1)
                # # Find if there is an overlap in time between the two stations
                # if len(overlap):
                #     if len(overlap) == 1:
                #         # If there is no overlap skip to the next item
                #         if max(sta[8], item[8]) > min(end1, end2):
                #             continue

                    # There is an overlap and therefore we guess that it is
                    # the same station
                    logging.warning('<ValueError')
                    logging.warning(sta)
                    logging.warning(item)
                    logging.warning('ValueError>')
                    raise ValueError

        # Add network if not present
        logging.debug('Added')
        super(ListStats, self).append(sta)


class ListNets(list):
    __slots__ = ()

    def __init__(self):
        super(ListNets, self).__init__()

    def extend(self, nets):
        for net in nets:
            self.append(net)

    def append(self, net):
        for ind, item in enumerate(self):
            # If network code is already in the list
            if item[0] == net[0]:
                # Check if it is a different network (temporary)
                if (net[4] == item[4]) and (net[5] == item[5]):
                    # Network is already inserted, but consider if the
                    # archive should be added
                    if net[9] in item[9]:
                        return
                    else:
                        item[9] += ',%s' % net[9]
                        return

        # Add network if not present
        super(ListNets, self).append(net)


def parseStationXML(invfile, archive='N/A'):
    ptNets = ListNets()
    ptStats = ListStats()
    ptLocs = ListLocs()
    ptChans = ListChans()

    try:
        context = ET.iterparse(invfile, events=("start", "end"))
    except IOError:
        msg = 'Error: could not parse the inventory file'
        logging.error(msg)
        raise Exception(msg)

    # turn it into an iterator
    context = iter(context)

    # get the root element
    event, root = context.next()

    # Check that it is really an inventory
    if root.tag[-len('FDSNStationXML'):] != 'FDSNStationXML':
        msg = 'The file parsed seems not to be a StationXML.'
        logging.error(msg)
        raise Exception(msg)

    # Extract the namespace from the root node
    namesp = root.tag[:-len('FDSNStationXML')]

    for event, netw in context:
        # Process only if the whole network was read
        if event != "end":
            continue

        # The tag of this node should be "Network"
        if not (netw.tag == namesp + 'Network'):
            continue

        if netw.get('startDate') is None:
            logging.error('Problem: ', netw.attrib)
        stnet = int(netw.get('startDate')[:4])
        try:
            etnet = int(netw.get('endDate')[:4])
        except Exception:
            etnet = None

        try:
            description = netw.find(namesp + 'Description').text
        except Exception:
            description = 'N/A'

        restricted = 2 if netw.get('restrictedStatus') == 'open' else 1
        netClass = 't' if netw.get('code')[0] in '0123456789XYZ' else 'p'
        institutions = ''

        ptNets.append([makenetcode(netw.get('code'), stnet), 0, None, None, stnet, etnet,
                       description, restricted, netClass, archive,
                       institutions])

        for stat in netw.findall(namesp + 'Station'):
            # logging.debug(stat.attrib)
            try:
                lat = float(stat.find(namesp + 'Latitude').text)
            except Exception:
                lat = None

            try:
                lon = float(stat.find(namesp + 'Longitude').text)
            except Exception:
                lon = None

            try:
                description = stat.find(namesp + 'Site').find(namesp + 'Name').text
            except Exception:
                description = None

            try:
                elevation = float(stat.find(namesp + 'Elevation').text)
            except Exception:
                elevation = None

            st = str2date(stat.get('startDate'))
            try:
                et = str2date(stat.get('endDate'))
            except Exception:
                et = None

            restricted = 2 if stat.get('restrictedStatus') == 'open' else 1

            try:
                ptStats.append([makenetcode(netw.get('code'), stnet),
                                0, None, None, makestationcode(stat.get('code'), st.year),
                                lat, lon, description, st, et,
                                elevation, restricted])
            except ValueError:
                continue

            for cha in stat.findall(namesp + 'Channel'):
                # if stat.get('code').startswith('Y01'):
                ptLocs.append(['%s.%s' % (makenetcode(netw.get('code'), stnet), makestationcode(stat.get('code'), st.year)),
                               0, None, None, cha.get('locationCode')])
                # SampleRateRatio: NumberSamples; NumberSeconds
                try:
                    denom = float(cha.find(namesp + 'SampleRateRatio').find(namesp + 'NumberSamples').text)
                    numer = int(cha.find(namesp + 'SampleRateRatio').find(namesp + 'NumberSeconds').text)
                except Exception:
                    try:
                        # Otherwise SampleRate
                        denom = float(cha.find(namesp + 'SampleRate').text)
                        numer = 1
                    except Exception:
                        denom = numer = 0

                # Datalogger: Description
                try:
                    datalogger = cha.find(namesp + 'DataLogger')
                    description = datalogger.find(namesp + 'Description').text
                except Exception:
                    description = ''

                ptChans.append(['%s.%s.%s' % (makenetcode(netw.get('code'), stnet), makestationcode(stat.get('code'), st.year),
                                                 cha.get('locationCode')),
                                cha.get('code'), None, denom, numer, description,
                                st, et, restricted])

                cha.clear()
            stat.clear()
        netw.clear()

    return ptNets, ptStats, ptLocs, ptChans


def downloadURL(url, params=None):
    req = ul.Request(url, params)
    try:
        u = ul.urlopen(req)
        # What is read has to be decoded in python3
        buf = u.read()
    except ul.URLError as e:
        logging.error('The URL does not seem to be a valid Routing-WS %s %s' % (url, params))
        if hasattr(e, 'reason'):
            logging.error('Reason: %s\n' % (e.reason))
        elif hasattr(e, 'code'):
            logging.error('The server couldn\'t fulfill the request.')
            logging.error('Error code: %s\n', e.code)
        raise Exception('URLError!')
    except Exception as e:
        logging.error('WATCH THIS! %s' % e)
        return None

    return buf


def parseRSinv(inv):
    routingTable = dict()
    dc = ''
    routes = list()
    for line in inv.splitlines():
        if not len(line):
            logging.info('Adding routes from %s' % urlparse(dc).hostname)
            routingTable[dc] = routes
            dc = ''
            routes = list()
            continue

        if not len(dc):
            dc = line.strip()
            continue

        routes.append(line)
    else:
        logging.info('Adding routes from %s' % urlparse(dc).hostname)
        routingTable[dc] = routes

    return routingTable


def getstaID(strnet, strsta, strstart, nets, stats):
    logs = logging.getLogger('getstaID')
    start = str2date(strstart)
    logs.debug('Looking for %s.%s %s' % (strnet, strsta, start.year))

    for auxidnet, net in enumerate(nets):
        if net[0] == strnet:
            logs.debug('%s %s %s: %s' % (net[4], start.year, net[5], (net[4] <= start.year <= net[5])))
            if (net[4] <= start.year) and (net[5] is None or start.year <= net[5]):
                idnet = auxidnet
                break
    else:
        raise Exception('Network %s not found!' % strnet)

    for auxidsta, sta in enumerate(stats):
        if sta[0] == idnet:
            logs.debug('%s %s' % (strsta, sta))
            if sta[4] == strsta:
                idsta = auxidsta
                break
    else:
        raise Exception('Station %s.%s not found!' % (strnet, strsta))

    return idsta


def parseVirtualNets(vntable, nets, stats):
    """Add the virtual networks to the network table.

    The definition of the virtual networks (vntable) looks like
    {"_MOST": [[["IV", "APEC", "*", "*"], ["2014-02-06T12:00:00", null]], [["IV", "CRM1", "*", "*"], ["2011-05-30T10:49:00", "2017-07-27T01:24:00"]], ...

    :param vntable: json object
    :param nets: network table
    :param stats: station table
    :return: nothing
    """
    for vnnet in vntable:
        idstats = set()
        minyear = 0
        for vnroute in vntable[vnnet]:
            try:
                idsta = getstaID(vnroute[0][0], vnroute[0][1], vnroute[1][0], nets, stats)
            except Exception as e:
                logging.error(e)
                continue
            minyear = min(stats[idsta][8].year, minyear)
            idstats.add(idsta)

        logging.info('Adding network %s' % vnnet)
        nets.append([vnnet, None, None, list(idstats), minyear, None, '%s virtual network' % vnnet, False, 'p', '', ''])

    return


def downloadInventory(routingserver='http://www.orfeus-eu.org/eidaws/routing/1',
                      level='station', foutput='inventory'):
    """Connects to a Routing Service to get routes and downloads the inventory
    from the Station-WS in StationXML format.
    The data is saved in the files with names starting as foutput. If old files
    exist they will be deleted.

    """

    # List with archives corresponding to the inventory downloaded
    # inv2rs = list()

    if foutput.endswith('.xml'):
        foutput = foutput[:-4]

    url = routingserver + '/query?format=post&service=station'
    logging.info('Getting routes from %s' % urlparse(routingserver).hostname)
    req = ul.Request(url)
    try:
        u = ul.urlopen(req)
        # Read 
        buf = u.read()

    except ul.URLError as e:
        logging.error('The URL does not seem to be a valid Routing-WS %s' % url)
        if hasattr(e, 'reason'):
            logging.error('Reason: %s\n' % (e.reason))
        elif hasattr(e, 'code'):
            logging.error('The server couldn\'t fulfill the request.')
            logging.error('Error code: %s\n', e.code)
        return None
    except Exception as e:
        logging.error('WATCH THIS! %s' % e)
        return None

    inv = parseRSinv(buf)

    # Remove old temp files
    for f in glob.glob('%s-*.xml' % (foutput)):
        os.remove(f)

    tmpfile = 0
    for dc in inv.keys():
        archive = url2archive(dc)

        idx = 0
        while idx < len(inv[dc]):
            last = idx+5 if idx+5 <= len(inv[dc]) else len(inv[dc])
            routebatch = '\n'.join(inv[dc][idx:last])
            idx += 5

            # Query StationWS
            postreq = 'level=%s\n%s' % (level, routebatch)
            try:
                buf = downloadURL(dc, postreq)
                logging.info('Writing to tmp file %d' % tmpfile)
                with open('%s-%s-%07d.xml' % (foutput, archive, tmpfile), 'wt') as fout:
                    fout.write(buf)
                    tmpfile += 1
            except Exception:
                pass

            # FIXME To make shorter the process
            # break
    return


def getNetworks(stationserver='http://localhost/fdsnws/station/1'):
    """Request a list of networks from a FDSN StationWS"""
    url = "%s/query?level=network&format=text" % stationserver
    try:
        buf = downloadURL(url)
    except Exception as e:
        logging.error('Problem reading list of networks from StationWS %s' % stationserver)
        raise Exception(str(e))

    # Parse and extract list of networks
    listnets = list()
    for line in buf.splitlines():
        if line.startswith('#'):
            continue
        listnets.append(line.split('|')[0])

    return listnets


def singlenodeInventory(stationserver='http://localhost/fdsnws/station/1',
                        level='station', foutput='inventory'):
    """Connects to a FDSN Station-WS download the inventory in StationXML format.
    The data is saved in the files with names starting as foutput. If old files
    exist they will be deleted.

    """

    if foutput.endswith('.xml'):
        foutput = foutput[:-4]

    # Remove old temp files
    for f in glob.glob('%s-*.xml' % (foutput)):
        os.remove(f)

    listnets = getNetworks(stationserver)

    tmpfile = 0

    for net in listnets:
        # Query StationWS
        url = '%s/query?level=%s&net=%s' % (stationserver, level, net)
        try:
            logging.debug('Requesting inventory from network %s' % net)
            buf = downloadURL(url)
            logging.info('Writing to tmp file %d' % tmpfile)
            with open('%s-singlenode-%07d.xml' % (foutput, tmpfile), 'wt') as fout:
                fout.write(buf)
                tmpfile += 1
        except Exception:
            pass

        # FIXME To make shorter the process
        # break
    return


def url2archive(url):

    o = urlparse(url)
    if o.hostname.endswith('gfz-potsdam.de'):
        return 'GFZ'
    elif o.hostname.endswith('orfeus-eu.org') or o.hostname.endswith('knmi.nl'):
        return 'ODC'
    elif o.hostname.endswith('ethz.ch'):
        return 'ETH'
    elif o.hostname.endswith('resif.fr'):
        return 'RESIF'
    elif o.hostname.endswith('ingv.it'):
        return 'INGV'
    elif o.hostname.endswith('bgr.de'):
        return 'BGR'
    elif o.hostname.endswith('uni-muenchen.de') or o.hostname.startswith('141.84.'):
        return 'LMU'
    elif o.hostname.endswith('infp.ro'):
        return 'NIEP'
    elif o.hostname.endswith('boun.edu.tr'):
        return 'KOERI'
    elif o.hostname.endswith('noa.gr'):
        return 'NOA'
    elif o.hostname.endswith('uib.no'):
        return 'UIB'
    elif o.hostname.endswith('icgc.cat'):
        return 'ICGC'
    elif o.hostname.endswith('iris.edu'):
        return 'IRIS'
    elif o.hostname.endswith('ncedc.org'):
        return 'NCEDC'

    raise Exception('Unknown data centre: %s' % o.hostname)


def str2date(dStr):
    """Transform a string to a datetime.

    :param dStr: A datetime in ISO format.
    :type dStr: string
    :return: A datetime represented the converted input.
    :rtype: datetime
    """
    # In case of empty string
    if not len(dStr):
        return None

    dateParts = dStr.replace('-', ' ').replace('T', ' ')
    dateParts = dateParts.replace(':', ' ').replace('.', ' ')
    dateParts = dateParts.replace('Z', '').split()
    return datetime.datetime(*map(int, dateParts))


def main():
    desc = 'Script to update the metadata for the usage of WebDC3'
    parser = argparse.ArgumentParser(description=desc)

    defaultRS = 'http://www.orfeus-eu.org/eidaws/routing/1'
    parser.add_argument('-r', '--routing', default=defaultRS,
                        help='Routing Service from which the inventory should be read.')
    parser.add_argument('-o', '--output', default='Arclink-inventory.xml',
                        help='Filename where inventory should be saved.')
    parser.add_argument('-l', '--log', default='WARNING', choices=['DEBUG', 'WARNING', 'INFO', 'DEBUG'],
                        help='Increase the verbosity level.')
    parser.add_argument('-sd', '--skip-download', action='store_true',
                        help='Do not download inventory and re-use the available files.')
    parser.add_argument('-sp', '--skip-parse', action='store_true',
                        help='Do not parse the StationXML files downloaded from the endpoints.')
    parser.add_argument('--singlenode', default=None,
                        help='Get inventory from a single StationWS instead of a Routing Service.')
    args = parser.parse_args()

    logging.basicConfig(level=args.log)

    foutput = 'inventory'

    if args.skip_download:
        logging.warning('Skipping download of inventory from endpoints')
    else:
        if args.singlenode is None:
            downloadInventory(routingserver=args.routing, level='channel',
                              foutput=foutput)
        else:
            singlenodeInventory(stationserver=args.singlenode, level='channel',
                                foutput=foutput)
        logging.info('Inventory downloaded')

    # File with incomplete inventory (no virtual networks)
    auxfile = 'webinterface-novn.bin'

    if args.skip_parse:
        logging.warning('Skipping parse of downloaded inventory')
        # Read the temporary and incomplete version of the inventory
        with open(auxfile) as cache:
            ptNets, ptStats, ptLocs, ptChans, ptStreamIdx = pickle.load(cache)
    else:
        ptNets = ListNets()
        ptStats = ListStats()
        ptLocs = ListLocs()
        ptChans = ListChans()

        for filename in glob.glob('%s-*.xml' % (foutput)):
            basefn, archive, auxidx = filename[:-4].split('-')
            idx = int(auxidx)

            with open(filename) as fin:
                logging.info('Opening tmp file %s' % filename)
                nets2add, stats2add, locs2add, chans2add = parseStationXML(fin, archive=archive)
                ptNets.extend(nets2add)
                ptStats.extend(stats2add)
                ptLocs.extend(locs2add)
                ptChans.extend(chans2add)

        ptNets.sort()
        ptStats.sort()
        ptLocs.sort()
        ptChans.sort()

        fixIndexes(ptNets, ptStats, ptLocs, ptChans)

        ptStreamIdx = indexStreams(ptNets, ptStats, ptLocs, ptChans)

        # Save a temporary and incomplete version of the inventory
        with open(auxfile, 'wb') as cache:
            os.chmod(auxfile, 0o0664)
            pickle.dump((list(ptNets), list(ptStats), list(ptLocs), list(ptChans), ptStreamIdx),
                        cache)

    logging.info('%d networks' % len(ptNets))
    logging.info('%d stations' % len(ptStats))
    logging.info('%d locations' % len(ptLocs))
    logging.info('%d channels' % len(ptChans))

    # Skip virtual networks of reading inventory from a single node
    if args.singlenode is None:
        vnraw = downloadURL('%s/virtualnets' % args.routing)
        vnjson = json.loads(vnraw)

        parseVirtualNets(vnjson, ptNets, ptStats)

    logging.info('%d networks (including virtual networks)' % len(ptNets))

    # Recover the summary of the last run (#nets, #stations, etc)
    with open('history.csv', 'rb') as histo:
        q = deque(histo, 5)

    nnet = 0
    nsta = 0
    nloc = 0
    ncha = 0

    while True:
        try:
            last = csv.reader([q.pop()])
        except IndexError:
            logging.error('No statistics about previous runs available in history.csv!')
            break

        try:
            lastline = last.next()
        except StopIteration:
            logging.error('Error reading from the last lines of history.csv')
            raise Exception('Error reading from the last lines of history.csv')

        try:
            dt, strnnet, strnsta, strnloc, strncha = lastline
            print('Last: %s.%s.%s.%s' % (nnet, nsta, nloc, ncha))
        except ValueError:
            logging.error('Wrong formatted line in history.csv?\n%s' % lastline)
            continue

        try:
            nnet = int(strnnet)
            nsta = int(strnsta)
            nloc = int(strnloc)
            ncha = int(strncha)
            break
        except ValueError:
            logging.error('Wrong formatted line in history.csv?\n%s', lastline)

    # Check a safety threshold to decide if the inventory should be replaced or not
    # We accept it if it has up to 3% less stations
    if len(ptStats) < nsta * 0.97:
        raise Exception('Too few stations compared to the last update! %s vs %s' % (nsta, len(ptStats)))

    # Update the time series with the results from this run
    with open('history.csv', 'ab') as histo:
        logging.info('Writing results to history.csv')
        csvwriter = csv.writer(histo)
        csvwriter.writerow([datetime.datetime.now(), len(ptNets), len(ptStats),
                            len(ptLocs), len(ptChans)])

    # Save binary version of the inventory
    cachefile = 'webinterface-cache.bin'
    with open(cachefile, 'wb') as cache:
        os.chmod(cachefile, 0o0664)
        pickle.dump((list(ptNets), list(ptStats), list(ptLocs), list(ptChans), ptStreamIdx),
                    cache)

    for net in ptNets[:10]:
        logging.debug(net)

    for sta in ptStats[:10]:
        logging.debug(sta)

    for loc in ptLocs[:10]:
        logging.debug(loc)

    for cha in ptChans[:10]:
        logging.debug(cha)

    count = 0
    for cha in ptStreamIdx:
        logging.debug(cha)
        logging.debug(ptStreamIdx[cha])
        count += 1
        if count > 10:
            break

    return


def indexStreams(networks, stations, sensorsLoc, streams):
    streamidx = {}

    for stream in streams:
        try:
            sensorLoc = sensorsLoc[stream[0]]
        except Exception:
            logging.error('Problem with stream: %s' % stream)
            return

        station = stations[sensorLoc[0]]
        network = networks[station[0]]

        # (net,sta,cha,loc)
        key = (network[0], station[4], stream[1], sensorLoc[4])

        try:
            obj = streamidx[key]

        except KeyError:
            obj = []
            streamidx[key] = obj

        obj.append(stream)

    return streamidx


def fixIndexes(ptNets, ptStats, ptLocs, ptChans):
    idxnet = 0
    idxsta = 0
    idxloc = 0
    idxcha = 0

    while idxnet < len(ptNets):
        net = ptNets[idxnet]
        net[1] = idxsta

        while idxsta < len(ptStats):
            sta = ptStats[idxsta]
            # logging.debug('%s ... %s' % (sta[0], net[0] + '-' + str(net[4])))
            # if sta[0] != net[0] + '-' + str(net[4]):
            logging.debug('%s ... %s' % (sta[0], net[0]))
            if sta[0] != net[0]:
                    break
            sta[0] = idxnet
            sta[1] = idxloc

            while idxloc < len(ptLocs):
                loc = ptLocs[idxloc]
                netcode, year = net[0], str(sta[8].year)
                logging.debug('%s ... %s' % (loc[0], netcode + '.' + sta[4]))
                if loc[0] != netcode + '.' + sta[4]:
                    break
                loc[0] = idxsta
                loc[1] = idxcha

                while idxcha < len(ptChans):
                    cha = ptChans[idxcha]
                    netsta = net[0] + '.' + sta[4]
                    logging.debug('%s ... %s' % (cha[0], netsta + '.' + loc[4]))
                    if cha[0] != netsta + '.' + loc[4]:
                        break
                    cha[0] = idxloc
                    idxcha += 1

                loc[2] = idxcha
                idxloc += 1

            sta[2] = idxloc
            # Remove the year from station code
            if '_' in sta[4]:
                sta[4] = sta[4].split('_')[0]

            idxsta += 1

        net[2] = idxsta
        # Remove the year from temporary networks
        if '_' in net[0]:
            net[0] = net[0].split('_')[0]

        idxnet += 1

    return


main()
