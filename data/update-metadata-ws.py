import os
import glob
import datetime
import urllib2 as ul
from urlparse import urlparse
import xml.etree.cElementTree as ET
import logging
import argparse
import pickle


def makenetcode(net, year):
    if net[0] in '0123456789XYZ':
        return '%s_%d' % (net, year)
    return net


def makestationcode(sta, year):
    return '%s_%d' % (sta, year)


class ListChans(list):
    __slots__ = ()

    def __init__(self):
        super(ListChans, self).__init__()

    def extend(self, chas):
        for cha in chas:
            self.append(cha)

    def append(self, cha):
        logging.debug('Try to add channel: %s' % cha)
        for ind, item in enumerate(self):
            # If network.station.location-year code is already in the list
            if (item[0] == cha[0]) and (item[1] == cha[1]):
                # print('%s already present!' % cha[0])
                return

        # Add location if not present
        logging.debug('Added')
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
                # print('%s already present!' % loc[0])
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
                    # print('%s already present!' % sta[4])
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
                        # print('%s already present!' % net[0])
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

        restricted = 1 if netw.get('restrictedStatus') == 'open' else 2
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

            restricted = 1 if stat.get('restrictedStatus') == 'open' else 2

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
                    denom = int(cha.find(namesp + 'SampleRateRatio').find(namesp + 'NumberSamples').text)
                    numer = int(cha.find(namesp + 'SampleRateRatio').find(namesp + 'NumberSeconds').text)
                except Exception:
                    try:
                        denom = int(cha.find(namesp + 'SampleRate').text)
                        numer = 1
                    except Exception:
                        denom = numer = None

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
        print('The URL does not seem to be a valid Routing-WS %s %s' % (url, params))
        if hasattr(e, 'reason'):
            print('Reason: %s\n' % (e.reason))
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: %s\n', e.code)
        raise Exception('URLError!')
    except Exception as e:
        print('WATCH THIS! %s' % e)
        return None

    return buf


def parseRSinv(inv):
    routingTable = dict()
    dc = ''
    routes = list()
    for line in inv.splitlines():
        if not len(line):
            print('Adding routes from %s' % urlparse(dc).hostname)
            routingTable[dc] = routes
            dc = ''
            routes = list()
            continue

        if not len(dc):
            dc = line.strip()
            continue

        routes.append(line)
    else:
        print('Adding routes from %s' % urlparse(dc).hostname)
        routingTable[dc] = routes

    return routingTable


def downloadInventory(routingserver='http://www.orfeus-eu.org/eidaws/routing/1',
                      level='station', foutput='inventory'):
    """Connects to a Routing Service to get routes and downloads the inventory
    from the Station-WS in StationXML format.
    The data is saved in the files with names starting as foutput.

    """

    # List with archives corresponding to the inventory downloaded
    # inv2rs = list()

    if foutput.endswith('.xml'):
        foutput = foutput[:-4]

    url = routingserver + '/query?format=post&service=station'
    req = ul.Request(url)
    try:
        u = ul.urlopen(req)
        # Read 
        buf = u.read()

    except ul.URLError as e:
        print('The URL does not seem to be a valid Routing-WS %s' % url)
        if hasattr(e, 'reason'):
            print('Reason: %s\n' % (e.reason))
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: %s\n', e.code)
        return None
    except Exception as e:
        print('WATCH THIS! %s' % e)
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
                # print(buf)
                print('Writing to tmp file %d' % tmpfile)
                with open('%s-%s-%07d.xml' % (foutput, archive, tmpfile), 'wt') as fout:
                    fout.write(buf)
                    # inv2rs.append(archive)
                    tmpfile += 1
            except Exception:
                pass

            # FIXME This is only to make the process much shorter
            # FIXME and should be removed after these tests!
            break


    # return inv2rs
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

    parser.add_argument('-o', '--output', default='Arclink-inventory.xml',
                        help='Filename where inventory should be saved.')
    parser.add_argument('-l', '--log', default='WARNING', choices=['DEBUG', 'WARNING', 'INFO', 'DEBUG'],
                        help='Increase the verbosity level.')
    args = parser.parse_args()

    logging.basicConfig(level=args.log)

    foutput = 'inventory'
    # inv2rs = downloadInventory(level='channel', foutput=foutput)
    # downloadInventory(level='channel', foutput=foutput)

    logging.info('Inventory downloaded')

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

    # ptStreamIdx = indexStreams(ptNets, ptStats, ptLocs, ptChans)
    ptStreamIdx = dict()

    cachefile = 'webinterface-cache.bin'
    with open(cachefile, 'wb') as cache:
        os.chmod(cachefile, 0664)
        pickle.dump((list(ptNets), list(ptStats), list(ptLocs), list(ptChans), ptStreamIdx),
                    cache)

    logging.info('%d networks' % len(ptNets))
    logging.info('%d stations' % len(ptStats))
    logging.info('%d locations' % len(ptLocs))
    logging.info('%d channels' % len(ptChans))

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
        logging.info(cha)
        logging.info(ptStreamIdx[cha])
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
            print(stream)
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
            idxsta += 1

        net[2] = idxsta
        idxnet += 1

    return


main()
