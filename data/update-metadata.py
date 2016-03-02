#!/usr/bin/env python
#
# Functions to update the metadata of WebDC3
#
# (c) 2014 Javier Quinteros, GEOFON team
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
import datetime
import telnetlib
import glob
from cStringIO import StringIO
import xml.etree.cElementTree as ET
from time import sleep
import logging
import socket
import argparse

try:
    import urllib.request as ul
except ImportError:
    import urllib2 as ul


def getNetworks(arclinkserver, arclinkport):
    """Connects via telnet to an Arclink server to get inventory information.
    The data is returned as a string.

    """

    tn = telnetlib.Telnet(arclinkserver, arclinkport)
    tn.write('HELLO\n')
    # FIXME The institution should be detected here. Shouldn't it?
    # Yes, it should -PLE.
    try:
        myhostname = socket.getfqdn()
    except:
        myhostname= "eida.invalid"
    logging.info(tn.read_until('GFZ', 5))
    tn.write('user webinterface@%s\n' % myhostname)
    logging.debug(tn.read_until('OK', 5))
    tn.write('request inventory\n')
    logging.debug(tn.read_until('OK', 5))
    tn.write('1980,1,1,0,0,0 %d,1,1,0,0,0 *\nEND\n' %
             (datetime.datetime.now().year + 1))

    reqID = 0
    while not reqID:
        text = tn.read_until('\n', 5).splitlines()
        for line in text:
            try:
                testReqID = int(line)
            except:
                continue
            if testReqID:
                reqID = testReqID

    myStatus = 'UNSET'
    while (myStatus in ('UNSET', 'PROCESSING')):
        sleep(1)
        tn.write('status %s\n' % reqID)
        stText = tn.read_until('END', 5)

        stStr = 'status='
        myStatus = stText[stText.find(stStr) + len(stStr):].split()[0]
        myStatus = myStatus.replace('"', '').replace("'", "")
        logging.debug(myStatus + '\n')

    if myStatus != 'OK':
        logging.error('Error! Request status is not OK.\n')
        return

    tn.write('download %s\n' % reqID)

    networksXML = ''

    start = None
    expectedLength = 1000
    totalBytes = 0
    while totalBytes < expectedLength:
        buffer = tn.read_until('END', 5)
        if start is None:
            start = buffer.find('<')
            expectedLength = int(buffer[:start])
            logging.info('Inventory length: %s\n' % expectedLength)
        else:
            start = 0

        if totalBytes + len(buffer) - start > expectedLength:
            endData = len(buffer) - 3
        else:
            endData = len(buffer)

        totalBytes += endData - start
        logging.debug('%d of %d' % (totalBytes, expectedLength))
        networksXML += buffer[start:endData]

    toDel = glob.glob('./webinterface-cache.*')
    for f2d in toDel:
        os.remove(f2d)
    logging.info('Inventory read from Arclink!\n')

    return networksXML


def genRoutingTable(networksXML, **kwargs):
    try:
        context = ET.iterparse(StringIO(networksXML),
                               events=("start", "end"))
    except IOError:
        msg = 'Error: %s could not be parsed. Skipping it!' % networksXML
        logging.error(msg)

    # turn it into an iterator
    context = iter(context)

    # get the root element
    # More Python 3 compatibility
    if hasattr(context, 'next'):
        event, root = context.next()
    else:
        event, root = next(context)

    # Check that it is really an inventory
    if root.tag[-len('inventory'):] != 'inventory':
        logging.debug(root)
        msg = '%s seems not to be an inventory file (XML). Skipping it!\n' \
            % networksXML
        logging.error(msg)

    # Extract the namespace from the root node
    namesp = root.tag[:-len('inventory')]

    header = """<?xml version="1.0" ?>
<arclink-network>
  <node address="%s" contact="%s" dcid="%s" email="%s" name="%s" port="%s">
""" % (kwargs.get('address', 'ARCLINKADDRESS'),
       kwargs.get('contact', 'No Name'),
       kwargs.get('dcid', 'NODCID'), kwargs.get('email', 'noreply@localhost'),
       kwargs.get('name', 'NN Datacentre'),
       kwargs.get('port', '18001'))

    with open('%s.xml' % kwargs.get('dcid', 'NODCID'), 'w') as fout:
        fout.write(header)
        for event, netw in context:
            # The tag of this node should be "network".
            # Now it is not being checked because
            # we need all the data, but if we need to filter, this
            # is the place.
            #
            if event == "end":
                if netw.tag != namesp + 'network':
                    continue

                if netw.tag == namesp + 'network':

                    # Extract the network code
                    try:
                        netCode = netw.get('code')
                    except:
                        logging.error('No network code at %s!' % netw)
                        raise Exception('No network code at %s!' % netw)

                    # Extract the start date of network
                    try:
                        netStart = netw.get('start')
                    except:
                        # Set a default start date
                        netStart = '1980-01-01 00:00:00'
                        msg = 'Setting a default start date for network %s.' \
                            % netCode
                        logging.warning(msg)

                    # Extract the end date of network
                    try:
                        netEnd = netw.get('end')
                        if len(netEnd):
                            netEnd = None
                    except:
                        netEnd = None

                    part1 = '<network code="%s" start="%s"' % \
                        (netCode, netStart)
                    part2 = ' end="%s"/>' % netEnd if netEnd is not None \
                        else '/>'
                    fout.write('    %s%s\n' % (part1, part2))

        fout.write('  </node>\n</arclink-network>\n')


def getMasterTable(foutput):
    try:
        u = ul.urlopen('http://eida.gfz-potsdam.de/arclink/table?group=eida')
    except:
        raise Exception('Error trying to download the master table from EIDA!')

    with open('%s.download' % foutput, 'w') as fo:
        fo.write(u.read())

    # Move the current file to the backup version
    try:
        os.rename(foutput, '%s.bck' % foutput)
    except:
        pass

    # Move the download file to the expected one
    try:
        os.rename('%s.download' % foutput, foutput)
    except:
        pass


def downloadInventory(arclinkserver, arclinkport, foutput):
    """Connects via telnet to an Arclink server to get inventory information.
    The data is saved in the file specified by the third parameter.

    """

    tn = telnetlib.Telnet(arclinkserver, arclinkport)
    tn.write('HELLO\n')
    # FIXME The institution should be detected here. Shouldn't it?
    logging.info(tn.read_until('GFZ', 5))
    tn.write('user webinterface@eida\n')
    logging.debug(tn.read_until('OK', 5))
    tn.write('request inventory instruments=true\n')
    logging.debug(tn.read_until('OK', 5))
    tn.write('1980,1,1,0,0,0 %d,1,1,0,0,0 * * * *\nEND\n' %
             (datetime.datetime.now().year + 1))

    reqID = 0
    while not reqID:
        text = tn.read_until('\n', 5).splitlines()
        for line in text:
            try:
                testReqID = int(line)
            except:
                continue
            if testReqID:
                reqID = testReqID

    myStatus = 'UNSET'
    while (myStatus in ('UNSET', 'PROCESSING')):
        sleep(1)
        tn.write('status %s\n' % reqID)
        stText = tn.read_until('END', 5)

        stStr = 'status='
        myStatus = stText[stText.find(stStr) + len(stStr):].split()[0]
        myStatus = myStatus.replace('"', '').replace("'", "")
        logging.debug(myStatus + '\n')

    if myStatus != 'OK':
        logging.error('Error! Request status is not OK.\n')
        return

    tn.write('download %s\n' % reqID)

    here = os.path.dirname(__file__)
    try:
        os.remove(os.path.join(here, '%s.download' % foutput))
    except:
        pass

    with open(os.path.join(here, '%s.download' % foutput), 'w') as fout:
        start = None
        expectedLength = 1000
        totalBytes = 0
        while totalBytes < expectedLength:
            buffer = tn.read_until('END', 5)
            if start is None:
                start = buffer.find('<')
                try:
                    expectedLength = int(buffer[:start])
                except:
                    logging.error('Unable to parse answer from Arclink: %s'
                                  % buffer)
                    raise ValueError('Unable to parse answer from Arclink: %s'
                                     % buffer)

                logging.info('Inventory length: %s\n' % expectedLength)
            else:
                start = 0

            if totalBytes + len(buffer) - start > expectedLength:
                endData = len(buffer) - 3
            else:
                endData = len(buffer)

            totalBytes += endData - start
            logging.debug('%d of %d' % (totalBytes, expectedLength))
            fout.write(buffer[start:endData])

    try:
        os.rename(os.path.join(here, './%s' % foutput),
                  os.path.join(here, './%s.bck' % foutput))
    except:
        pass

    try:
        os.rename(os.path.join(here, './%s.download' % foutput),
                  os.path.join(here, './%s' % foutput))
    except:
        pass

    toDel = glob.glob('./webinterface-cache.*')
    for f2d in toDel:
        os.remove(os.path.join(here, f2d))
    logging.info('Inventory read from Arclink!\n')


def main():
    desc = 'Script to update the metadata for the usage of WebDC3'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-a', '--address', default='eida.gfz-potsdam.de',
                        help='Address of the Arclink Server.')
    parser.add_argument('-p', '--port', default='18002',
                        help='Port of the Arclink Server.')
    parser.add_argument('-o', '--output', default='Arclink-inventory.xml',
                        help='Filename where inventory should be saved.')
    parser.add_argument('-v', '--verbosity', action="count", default=0,
                        help='Increase the verbosity level')

    subparsers = parser.add_subparsers()

    # create the parser for the "eida" command
    parser_e = subparsers.add_parser('eida',
                                     help='Get master table from EIDA')

    # create the parser for the "singlenode" command
    singlehelp = 'Create master table based on local inventory.\n' + \
        'Type "%(prog)s singlenode -h" to get detailed help.'
    parser_s = subparsers.add_parser('singlenode', help=singlehelp)

    dcidhelp = 'Short ID of your data centre. Up to 5 letters, no spaces.'
    parser_s.add_argument('dcid', help=dcidhelp)
    parser_s.add_argument('-c', '--contact', default='No Name',
                          help='Name of the person responsible for this instance of WebDC3.')
    parser_s.add_argument('-e', '--email', default='noreply@localhost',
                          help='Email address of the person responsible for this instance of WebDC3.')
    parser_s.add_argument('-n', '--name', default='Name of Datacentre',
                          help='Official name of Datacentre.')
    args = parser.parse_args()

    # Limit the maximum verbosity to 3 (DEBUG)
    verbNum = 3 if args.verbosity >= 3 else args.verbosity
    lvl = 40 - verbNum * 10
    logging.basicConfig(level=lvl)

    if 'dcid' in args:
        # Check for spaces in DCID
        if len(args.dcid) > 5:
            logging.error('DCID too long')
            parser_s.print_help()
            return

        dcid = args.dcid.upper().replace(' ', '')
        if not all(c.isalpha() for c in dcid):
            logging.error('Only letters are allowed in DCID')
            parser_s.print_help()
            return

    downloadInventory(args.address, args.port, args.output)

    # Check for mandatory argument in case of a single node
    if 'dcid' not in args:
        getMasterTable('eida.xml')
    else:
        nets = getNetworks(args.address, args.port)
        genRoutingTable(nets, address=args.address, port=args.port,
                        contact=args.contact, email=args.email, dcid=dcid,
                        name=args.name)

if __name__ == '__main__':
    main()
