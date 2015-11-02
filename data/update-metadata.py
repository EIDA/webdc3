#!/usr/bin/env python
#
# Routing WS prototype
#
# (c) 2014 Javier Quinteros, GEOFON team
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

"""Classes to be used by the Routing WS for EIDA

   :Platform:
       Linux
   :Copyright:
       GEOFON, GFZ Potsdam <geofon@gfz-potsdam.de>
   :License:
       To be decided!

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
from time import sleep
import logging
import argparse

try:
    import urllib.request as ul
except ImportError:
    import urllib2 as ul

def getMasterTable(foutput):
    u = ul.urlopen('http://eida.gfz-potsdam.de/arclink/table?group=eida')
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
The data is saved in the file specified by thethird parameter. Generally used to start
operating with an EIDA default configuration.

    """

    tn = telnetlib.Telnet(arclinkserver, arclinkport)
    tn.write('HELLO\n')
    # FIXME The institution should be detected here. Shouldn't it?
    logging.info(tn.read_until('GFZ', 5))
    tn.write('user webinterface@eida\n')
    logging.debug(tn.read_until('OK', 5))
    tn.write('request inventory instruments=true\n')
    logging.debug(tn.read_until('OK', 5))
    tn.write('1980,1,1,0,0,0 %d,1,1,0,0,0 * * * *\nEND\n' % (datetime.datetime.now().year + 1))

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
    ARCLINKSERVER = 'eida.gfz-potsdam.de'
    ARCLINKPORT = 18002

    parser = argparse.ArgumentParser(description=\
        'Script to update the metadata for the usage of WenDC3')
    parser.add_argument('-o', '--output', default='Arclink-inventory.xml',
                        help='Filename where to save the data.')
    parser.add_argument('-v', '--verbosity', action="count", default=0,
                        help='Increase the verbosity level')
    args = parser.parse_args()

    verbNum = 3 if args.verbosity >= 3 else args.verbosity
    lvl = 40 - args.verbosity * 10
    logging.basicConfig(level=lvl)

    downloadInventory(ARCLINKSERVER, ARCLINKPORT, args.output)
    getMasterTable('eida.xml')

if __name__ == '__main__':
    main()
