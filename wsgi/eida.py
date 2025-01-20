import os
import datetime
import sys
import string
from xml.dom.minidom import Document as E
from xml.dom.minidom import parseString

class Nodes(object):
    def __init__(self):
        self._nodes = {}
        self._groups = {}

    def getHTMLOptions(self):
        options = ""
        for node in self:
            options = options + ("<option value='%s:%s'>%s</option>\n" % (node.address, node.port, node.name))
        return options

    def getNode(self, dcid):
        return self._nodes[dcid]

    def __iter__(self):
        return iter(self._nodes.values())

    def xml(self, ids = None):
        doc = E()
        arclinkNet = doc.createElement("arclink-network")
        doc.appendChild(arclinkNet)
        for node in self:
            if ids is not None and node.dcid.upper() not in list(map(string.upper, ids)):
                continue
            arclinkNet.appendChild(node._xml(doc))
        xml = doc.toprettyxml()
        del doc
        return xml

    def add(self, node):
        if node.dcid in self._nodes:
            raise Exception("Node already inserted")
        self._nodes[node.dcid.upper()] = node

    def remove(self, dcid):
        if dcid in self._nodes:
            self._nodes.pop(dcid)

    def findGroup(self, name):
        group = []
        
        name = name.upper()
        if name in list(map(string.upper, self._groups)):
            group.extend(self._groups[name.upper()])
        return group

    def load_xml(self, filename):
        try:
            r = open(filename, "r")
            xdoc = parseString(r.read())
            r.close()
        except:
            raise Exception("Could not load file %s" % filename)
        
        for node in xdoc.getElementsByTagName("group"):
            name = str(node.getAttribute("name"))
            if name in self._groups:
                raise Exception("Duplicated group name %s" % name)
            group = []
            for item in node.getElementsByTagName("element"):
                id = str(item.getAttribute("code"));
                group.append(id)
            if group:
                self._groups[name.upper()] = group
        
        for node in xdoc.getElementsByTagName("node"):
            id = str(node.getAttribute("dcid"))
            if id in self._nodes:
                raise Exception("Node already defined.")
            
            ad = str(node.getAttribute("address"))
            pt = int(node.getAttribute("port"))
            
            n = Node(id, ad, pt)
            n.name = str(node.getAttribute("name"))
            n.email = str(node.getAttribute("email"))
            n.contact = str(node.getAttribute("contact"))
            
            for network in node.getElementsByTagName("network"):
                code = str(network.getAttribute("code"))
                start = datetime.datetime.strptime(network.getAttribute("start"), "%Y-%m-%d %H:%M:%S")
                end = network.getAttribute("end")
                if end == "":
                    end = None
                else:
                    end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                n.addNetwork(code, start, end)
            for stationGroup in node.getElementsByTagName("stationGroup"):
                code = str(stationGroup.getAttribute("code"))
                start = datetime.datetime.strptime(stationGroup.getAttribute("start"), "%Y-%m-%d %H:%M:%S")
                end = stationGroup.getAttribute("end")
                if end == "":
                    end = None
                else:
                    end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                n.addStationGroup(code, start, end)
            self.add(n)

    def save_xml(self, filename):
        out = open(filename, "w")
        out.write(self.xml())
        out.close()
        return

    def unload(self):
        self._nodes = {}
        self._group = {}

class Node(object):
    __slots__ = (
            "dcid",
            "name",
            "address",
            "port",
            "contact",
            "email",
            "networks",
            "stationGroups"
    )

    def __init__(self, dcid, address, port):
        for at in self.__slots__:
            setattr(self, at, None)
        self.dcid = dcid
        self.address = address
        self.port = port
        self.networks = {}
        self.stationGroups = {}

    def networkList(self):
        pack = []
        for ones in list(self.networks.values()):
            for obj in ones:
                pack.append(obj)
        return pack

    def stationGroupList(self):
        pack = []
        for ones in list(self.stationGroups.values()):
            for obj in ones:
                pack.append(obj)
        return pack

    def _xml(self, doc):
        xnode = doc.createElement("node")
        for att in self.__slots__:
            if att in ["networks", "stationGroups"]:
                continue
            if getattr(self, att) is not None:
                xnode.setAttribute(att, str(getattr(self, att)))
        for (n,s,e) in self.networkList():
            nnode = doc.createElement("network")
            nnode.setAttribute("code", n)
            nnode.setAttribute("start", str(s))
            if e is not None: nnode.setAttribute("end", str(e))
            xnode.appendChild(nnode)
        for (n,s,e) in self.stationGroupList():
            nnode = doc.createElement("stationGroup")
            nnode.setAttribute("code", n)
            nnode.setAttribute("start", str(s))
            if e is not None: nnode.setAttribute("end", str(e))
            xnode.appendChild(nnode)
        return xnode

    def __overlap__(self, s1, e1, s2, e2):
        if e1:
            if e1 > s2:
                if not e2 or s1 < e2:
                    return True
        else:
            if not e2 or s1 < e2:
                return True
        return False

    def _conflict(self, obj, nn, ss, ee):
        try:
            list = obj[nn]
        except:
            list = []
        
        for (n,s,e) in list:
            if n != nn: continue
            if self.__overlap__(s, e, ss, ee):
                return True
        return False

    def _add(self, obj, code, start, end):
        if code is None:
            raise Exception("Invalid code")
        
        if start is None:
            raise Exception("Invalid start date")
        
        if self._conflict(obj, code, start, end):
            raise Exception("Conflicting items")
        
        if code not in obj:
            obj[code] = []
        
        obj[code].append((code, start, end))
        obj[code].sort()

    def _remove(self, obj, code, start):
        if code is None:
            raise Exception("Invalid network code")
        
        if start is None:
            raise Exception("Invalid start date")
        
        try:
            ones = obj[code]
            for (n,s,e) in ones:
                if code == n and start == s:
                    ones.remove((n,s,e))
                    return
        except:
            raise Exception("Code Not found")
        raise Exception("Start/End not found")

    def addNetwork(self, code, start, end):
        self._add(self.networks, code, start, end)

    def removeNetwork(self, code, start):
        self._remove(self.networks, code, start)

    def addStationGroup(self, code, start, end):
        self._add(self.stationGroups, code, start, end)

    def removeStationGroup(self, code, start):
        self._remove(self.stationGroups, code, start)

    def info(self, where=sys.stderr):
        print("%s" % (self.dcid), file=where)
        print(" Name: %s" % (self.name), file=where)
        print(" Contact: %s" % (self.contact), end=' ', file=where)
        print("\tEmail: %s" % (self.email), file=where)
        print(" Address: %-15s" % (self.address), end=' ', file=where)
        print("\tPort: %s" % (self.port), file=where)
        
        nList = self.networkList()
        sgList = self.stationGroupList()
        
        print(" %d network%s\t %d station group%s" % (len(nList),"" if len(nList) == 1 else "s", len(sgList), "" if len(sgList) == 1 else "s"), file=where)
        i=1
        for (n,s,e) in nList:
            print("  [%d] %s (%s) (%s)" % (i,n,s,e), file=where)
            i=i+1
        for (n,s,e) in sgList:
            print("  [%d] %s (%s) (%s)" % (i,n,s,e), file=where)
            i=i+1
        print("", file=where)
