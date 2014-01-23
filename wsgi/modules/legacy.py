import eida
from seiscomp.arclink.manager import *

class WI_Module(object):
    def __init__(self, wi):
        wi.registerAction("/getAllFromList", self.nothing)
        wi.registerAction("/loadStationForm", self.loadStationForm)
        wi.registerAction("/loadStationList", self.nothing)
        wi.registerAction("/loadNodeList", self.loadNodeList)
        wi.registerAction("/proxy", self.nothing)
        wi.registerAction("/getRegion", self.getRegion)
        wi.registerAction("/select", self.nothing)
        wi.registerAction("/submit_large", self.nothing, "rq")
        wi.registerAction("/submit", self.nothing, "rq")
        wi.registerAction("/status", self.nothing)
        wi.registerAction("/download", self.nothing)
        wi.registerAction("/purge", self.nothing)
        wi.registerAction("/newuser", self.nothing)
        wi.registerAction("/default", self.nothing)

        self.nettypes = [("all", "All nets", None, None),
            ("virt", "Virtual nets", None, None),
            ("perm", "All permanent nets", True, None),
            ("temp", "All temporary nets", False, None),
            ("open", "All public nets", None, False),
            ("restr", "All non-public nets", None, True),
            ("permo", "Public permanent nets", True, False),
            ("tempo", "Public temporary nets", False, False),
            ("permr", "Non-public permanent nets", True, True),
            ("tempr", "Non-public temporary nets", False, True)]

        self.server_folder = wi.server_folder
        self.network_xml = wi.getConfigList('NETWORK_XML', ("eida.xml",))
        self.default_addr = wi.getConfigString('DEFAULT_ADDR', "webdc.eu:18002")
        self.default_user = wi.getConfigString('DEFAULT_USER', "guest@webdc")
        
        self.arcl = Arclink()
        self.mgr = ArclinkManager(self.default_addr, self.default_user)

    def nothing(self, envir, params):
        """Called if nothing more than the directory of the WSGI script is entered.
        
        As no function is being called, we just do not look at the input parameters
        (if any) and return the main starting page of the system.
        
        Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013

        """

        body = []

        # Main starting page is read from the main directory
        # FIXME: Of course we have problems because nothing static like javascript
        # files can be served
        try:
            f = open(self.server_folder + '/index.html')
        except IOError:
            print('Error: index.html could not be opened.')
        else:
            with f:
                for line in f:
                    body.append(line)

        return body

    def loadStationForm(self, envir, params):
        """
        Input: start     start of the time range ('YYYY-MM-DD hh:mm:ss')
               end       end of the time range ('YYYY-MM-DD hh:mm:ss')
               mag       minimum magnitude (float)
               depth     maximum depth (unsigned float)
               dbsel     Catalog (???)
               elatmin   minimum latitude (signed float)
               elatmax   maximum latitude (signed float)
               elonmin   minimum longitude (signed float)
               elonmax   maximum longitude (signed float)
               before    minutes before the event (unsigned float) (???)
               after     minutes after the event (unsigned float) (???)
        
        Output: All networks and all stations based in the input parameters.
                The two list are returned one after another.
                As usual in CSV format. Columns for networks are:
                NET-ID, CODE, FLAGS, START-YEAR, DESCRIPTION, CATALOG (???)
                While columns for stations are:
                STATION-ID, CODE, 
                The headers before the lists are:
                [NETWORKS|STATIONS], LENGTH-OF-LIST
        
        FIXME: What do we do with the station group code? Is it an extra field?
               See line with text = "%-5s, %2s, %4s, %s" % (sta.code, nCode, nStart, sgrp.code)
        
        Example:
        
        NETWORKS, 4
        TI-1980-None, TI, *+, 1980, 'TIPAGE Network, Tadjikistan/Kirgistan, 2008', 'GFZ', 
        X6-2010-None, X6, *+, 2010, 'MonaSeis Project 2010/2011 (GIPP/Uni_Franksfurt,_Germany)', 'GFZ', 
        Z5-2008-None, Z5, *+, 2008, 'Rwenzori project 2009/12,JWG University Frankfurt, Germany (Rwenzori_project)', 'GFZ', 
        ZE-2012-2014, ZE, *+, 2012, 'Madagascar Profile, Madagascar, 2012/2014', 'GFZ', 
        STATIONS, 7
        ZE-2012-2014-MS01, MS01 , ZE, 2012, 
        ZE-2012-2014-MS02, MS02 , ZE, 2012, 
        ZE-2012-2014-MS03, MS03 , ZE, 2012, 
        ZE-2012-2014-MS04, MS04 , ZE, 2012, 
        ZE-2012-2014-MS05, MS05 , ZE, 2012, 
        ZE-2012-2014-MS06, MS06 , ZE, 2012, 
        ZE-2012-2014-MS07, MS07 , ZE, 2012, 

        Comment from previous version:
            This method was complete rewritten to support temporary networks
            The FIXEDARCHIVE flag was not implemented completely since we think that this is not necessary
            To support those methods were also some changes in the query.js and for better layout of the items
            The file html_chunks.py was also modified.
            Bianchi @ 2012
        
        Migrated by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013
        Original version from:
        (2005) Andres Heinloo, GFZ Potsdam
        (2009) Doreen Pahlke, GFZ Potsdam

        """

        start_date  = params.get("start")
        end_date    = params.get("end")
        typeNet     = params.get("typesel", "open")
        networkInfo = params.get("netsel", "*")
        stationInfo = params.get("statsel", "*")
        # cookies    = Cookie.get_cookies(obj)

        # Fix Archive
        ## NOT IMPLEMENTED ANYMORE
        # try:
        #     fixedarchive = cookies["archive"].value
        #     if fixedarchive == "all":
        #         fixedarchive = None

        # except KeyError:
        #     fixedarchive = None


        # Dates
        begd = None
        if start_date != None:
            try:
                begd = datetime.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ArclinkError, "invalid start date: " + start_date
       
        endd = None
        if end_date != None:
            try:
                endd = datetime.datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ArclinkError, "invalid end date: " + end_date


        # parse the parameters for network code and station to split dates
        networkCode = None
        networkStart = None
        networkEnd = None
        stationCode = None
        
        if networkInfo.find("-") != -1:
            try:
                (networkCode, networkStart, networkEnd) = networkInfo.split("-")
            except ValueError:
                print 'Problem with the network code: %s' % networkInfo

            try:
                networkStart = datetime.datetime(int(networkStart), 1, 1, 0, 0, 0)
            except:
                networkStart = None

            try:
                networkEnd   = datetime.datetime(int(networkEnd), 12, 31, 23, 59, 59)
            except:
                networkEnd = None

            network = networkCode
        else:
            network = networkInfo
        
        if stationInfo.find("-") != -1:
            try:
                (networkCode, networkStart, networkEnd, stationCode) = stationInfo.split("-")
            except ValueError:
                print 'Problem with the station code: %s' % stationInfo

            try:
                networkStart = datetime.datetime(int(networkStart), 1, 1, 0, 0, 0)
            except:
                networkStart = None

            try:
                networkEnd   = datetime.datetime(int(networkEnd), 12, 31, 23, 59, 59)
            except:
                networkEnd = None

            network = networkCode
            station = stationCode
        else:
            network = networkInfo
            station = stationInfo

        # Find the parameters to be sent to the arclink server based on the network type selected
        permanent = None
        restricted = None
        if (typeNet is not None) and (network == "*"):
            for (nt, desc, permanent, restricted) in self.nettypes:
                if nt == type:
                    break

        # Send the arclink request
        db = self.mgr.get_inventory(network, station, "*", "*", begin=begd, end=endd, permanent=permanent, restricted=restricted, allnet=True)

    #DEBUG#    syslog.syslog(syslog.LOG_ALERT, "%s %s %s %s %s %s %s" % (network, station, networkCode, networkStart, networkEnd, stationCode, type))

        # Prepare the network and station collectors
        networkList = []
        stationList = []
        
        # If type not virt add normal networks (also prepare the list of stations from networks)
        if typeNet != "virt":
            for nspams in db.network.values():
                for net in nspams.values():
                    nCode = net.code
                    nStart = net.start.year
                    nEnd = net.end.year if net.end else None
                    flag = ""
                    flag += "*" if net.netClass == "t" else " "
                    flag += "+" if net.restricted else " "
                    text = "%2s, %s, %4d, '%s', '%s'" % (nCode, flag, nStart, net.description, net.archive)
                    selected = True if nCode == networkCode and networkStart.year == nStart else False
                    key = "%s-%s-%s" % (nCode, nStart, nEnd)
                    
                    networkList.append((key, text, selected))

                    # Read STATIONS only from the networks that coincide with networkCode
                    if (networkCode and networkCode != nCode) or (networkStart and networkStart.year != nStart): continue

                    for sspams in net.station.values():
                        for sta in sspams.values():
                            sCode = sta.code
                            sStart = sta.start.year
                            sEnd = sta.end.year if sta.end else None

                            # Select only the stations that coincide with stationCode
                            if stationCode and stationCode != sCode: continue

                            text = "%-5s, %2s, %4s" % (sCode, nCode, nStart)
    #DEBUG#                        syslog.syslog(syslog.LOG_ALERT, "%s" % text)
                            key = "%s-%s-%s-%s" % (nCode, nStart, nEnd, sCode)
                            selected = False

                            if (key, text, selected) not in stationList:
                                stationList.append((key, text, selected))
                        
        # Since we want that the virtual stuff goes to the end we 
        # sort the lists so that the list is sorted by the network code and station code
        networkList.sort()
        stationList.sort()

        # And add virtual networks to the list if type is "all" or "virt"
        if (typeNet == "virt") or (typeNet == "all"):
            for sgrp in db.stationGroup.itervalues():
                sgCode  = sgrp.code
                sgStart = sgrp.start.year if sgrp.start else None
                sgEnd   = sgrp.end.year if sgrp.end else None
                
                if (typeNet == "virt") and (networkCode is None):
    #DEBUG#                syslog.syslog(syslog.LOG_ALERT, "Seting it ... %s " % sgCode)
                    networkCode = sgCode
                    networkStart = sgrp.start
                
                sgLen   = len(sgrp.stationReference)
                text = "%s,,, '%s'," % (sgCode, sgrp.description)
                key = "%s-%s-%s" % (sgCode, sgStart, sgEnd)
                selected = True if (sgCode == networkCode) and ((networkStart and networkStart.year == sgStart) or (networkStart == sgStart)) else False
                
                networkList.append((key, text, selected))

                # Dont collect station from the groups not selected
                if networkCode:
                    if networkCode != sgrp.code:
                        continue
                    if networkStart and sgrp.start is None:
                        continue
                    elif networkStart is None and sgrp.start: 
                        continue
                    elif networkStart and sgrp.start and networkStart.year != sgrp.start.year:
                        continue

                # Add the stations for the station groups
    #DEBUG#            syslog.syslog(syslog.LOG_ALERT, "%s:: %s " % (sgCode,sgrp.stationReference))
                for sref in sgrp.stationReference.itervalues():
                    for nspams in db.network.itervalues():
                        for net in nspams.itervalues():
                            try:
                                sta = net.object[sref.stationID]
                            except:
                                continue
                            nCode = net.code
                            nStart = net.start.year
                            nEnd = net.end.year if net.end else None
                            text = "%-5s, %2s, %4s, %s" % (sta.code, nCode, nStart, sgrp.code)
                            key = "%s-%s-%s-%s" % (nCode, nStart, nEnd, sta.code)
                            if (key, text, False) not in stationList:
    #DEBUG#                            syslog.syslog(syslog.LOG_ALERT, "Added .. %s / %s" % (key, sgrp.code))
                                stationList.append((key, text, False))

        # Finally add the "All" option to the first position
        # if typeNet != "virt":
        #     networkList.insert(0,("*", "All networks", (True if network == "*" else False)))
        # stationList.insert(0,("*", "All stations", (True if station == "*" else False)))

        body = ['NETWORKS, %d' % len(networkList)]

        # And render the result to the browser
        for (key, text, selected) in networkList:
            body.append('%s, %s, %s' % (key, text, "selected" if selected else ""))

        body.append('STATIONS, %d' % len(stationList))

        for (key, text, selected) in stationList:
            body.append('%s, %s, %s' % (key, text, "selected" if selected else ""))

        return body



    def getRegion(self, envir, params):
        """Return a region name based on latitude and longitude.

        Input: lat      latitude (float)
               lon      longitude (float)

        Output: a string with the name of the region or 'NOREGION' in
                case of error.

        Migrated by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013
        Original version from:
        (2005) Andres Heinloo, GFZ Potsdam
        (2009) Doreen Pahlke, GFZ Potsdam

        """
        latitude = params.get("lat")
        longitude = params.get("lon")

        if not latitude or not longitude:
            return ['NOREGION']
        
        body = []

        try:
            region = fe.region(float(latitude), float(longitude))
        except:
            return ['NOREGION']

        body.append(region)
        return body



    def loadNodeList(self, envir, params):
        """Return a list of Nodes

        Input: nothing

        Output: List of EIDA nodes from the configuration in CSV format.
                The columns are NODEID, NAME, HOSTNAME, PORT.

        Migrated by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013
        Original version from:
        (2005) Andres Heinloo, GFZ Potsdam
        (2009) Doreen Pahlke, GFZ Potsdam

        """

        eidaNodes = eida.Nodes()
        for file in self.network_xml:
            try:
                eidaNodes.load_xml(self.server_folder + '/wsgi/' + file)
            except:
                print "Could not load network XML file: %s" % (conf['SERVER_FOLDER'] + '/wsgi/' + file)
                # FIXME: Please check if this is OK. Only add the proxy address if there
                # is a problem with the one configured.
                proxynode = eida.Node("GFZP", "webdc.eu", "18001")
                proxynode.name = "Geofon Data Center (proxy)"
                eidaNodes.add(proxynode)
                pass

        body = []

        for node in eidaNodes:
            body.append('%s, %s, %s, %s' % (node.dcid, node.name, node.address, node.port))

        return body

