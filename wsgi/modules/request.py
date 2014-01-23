#!/usr/bin/env python
#
# Arclink request services.
#
# Begun by Andres Heinloo, GEOFON team, June 2013
# <andres@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

import os
import json
import uuid
import datetime
import cStringIO
import xml.etree.ElementTree as ET
import wsgicomm
from seiscomp import logs
from seiscomp.xmlparser import DateTimeAttr
from seiscomp.arclink.manager import *

class MyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return DateTimeAttr.toxml(obj)

        return json.JSONEncoder.default(self, obj)

class WI_Module(object):
    def __init__(self, wi):
        wi.registerAction("/request/types", self.request_types)
        wi.registerAction("/request/nodes", self.request_nodes)
        wi.registerAction("/request/status", self.request_status)
        wi.registerAction("/request/submit", self.request_submit)
        wi.registerAction("/request/resubmit", self.request_resubmit)
        wi.registerAction("/request/download", self.request_download)
        wi.registerAction("/request/purge", self.request_purge)

        self.formats = (("MSEED", "Waveform (Mini-SEED)"),
                        ("FSEED", "Waveform (Full SEED)"),
                        ("DSEED", "Metadata (Dataless SEED)"),
                        ("INVENTORY", "Metadata (Inventory XML)"))

        self.default_server = wi.getConfigString('arclink.address', "eida.gfz-potsdam.de:18002")
        self.request_timeout = wi.getConfigInt('arclink.timeout.request', 300)
        self.status_timeout = wi.getConfigInt('arclink.timeout.status', 300)
        self.download_timeout = wi.getConfigInt('arclink.timeout.download', 300)
        self.max_req_lines = wi.getConfigInt('js.request.lineLimit', 990)
        self.max_req_lines_local = wi.getConfigInt('js.request.localLineLimit', 4990)
        self.max_req_mb = wi.getConfigInt('js.request.sizeLimit', 500)

        network_xml = [ os.path.join(wi.server_folder, 'data', f)
            for f in wi.getConfigList('arclink.networkXML', ('eida.xml',)) ]

        self.nodes = {}
        self.nodeaddr = {}
        self.__load_nodelist(network_xml)

        # get inventory cache
        self.ic = wi.ic

    # -------------------------------------------------------------------------
    # Helper functions
    # -------------------------------------------------------------------------

    def __load_nodelist(self, network_xml):
        for f in network_xml:
            try:
                tree = ET.parse(f)

            except Exception as e:
                logs.error("could not parse %s: %s" % (f, str(e)))
                continue

            root = tree.getroot()

            for e in root.findall('./node'):
                try:
                    dcid = e.attrib['dcid']
                    name = e.attrib['name']
                    addr = e.attrib['address'] + ':' + e.attrib['port']
                    self.nodes[dcid] = {'name': name, 'address': addr}
                    self.nodeaddr[addr] = dcid

                except KeyError:
                    logs.error("invalid node element in %s" % (f,))

    def __addr_to_dcid(self, addr):
        return self.nodeaddr.get(addr, addr)

    def __parse_arglist(self, arglist):
        d = {}
        for arg in arglist:
            pv = arg.split('=', 1)
            if len(pv) != 2:
                logs.error("invalid request args in status: " + args)
                continue

            d[pv[0]] = pv[1]

        return d

    def __estimate_size(self, req_body):
        for rl in req_body:
            info = self.ic.getStreamInfo(rl.start_time, rl.end_time,
                    rl.net, rl.sta, rl.cha, rl.loc)

            if info: rl.estimated_size = info['size']
            else: rl.estimated_size = 0

    def __parse_req_line(self, data):
        rqline = str(data).strip()
        if not rqline:
            logs.error("empty request line")
            return None

        rqsplit = rqline.split()
        if len(rqsplit) < 3:
            logs.error("invalid request line: %s" % (rqline,))
            return None

        try:
            start_time = datetime.datetime(*map(int, rqsplit[0].split(",")))
            end_time = datetime.datetime(*map(int, rqsplit[1].split(",")))

        except ValueError as e:
            logs.error("syntax error (%s): '%s'" % (str(e), rqline))
            return None

        network = rqsplit[2]
        station = "."
        channel = "."
        location = "."

        i = 3
        if len(rqsplit) > 3 and rqsplit[3] != ".":
            station = rqsplit[3]
            i += 1
            if len(rqsplit) > 4 and rqsplit[4] != ".":
                channel = rqsplit[4]
                i += 1
                if len(rqsplit) > 5 and rqsplit[5] != ".":
                    location = rqsplit[5]
                    i += 1

        while len(rqsplit) > i and rqsplit[i] == ".":
            i += 1

        constraints = self.__parse_arglist(rqsplit[i:])

        return RequestLine(start_time, end_time, network, station, channel, location)

    def __get_uuid(self, label, addr, req_id):
        if label.startswith("WI:"): # UUID has been embedded in request label
            return label.split(':', 2)[1]

        else: # create UUID from server address and request ID
            return str(uuid.uuid5(uuid.NAMESPACE_URL, str("arclink://%s/%s" % (addr, req_id))))

    def __get_desc(self, label):
        if label.startswith("WI:"):
            try:
                return label.split(':', 2)[2]

            except IndexError:
                return None

        return None

    def __status_to_dict(self, status, addr):
        d = {}
        for (a,v) in status.__dict__.iteritems():
            if a.startswith('_') or a == "xmlns" or a == "user":
                continue

            if isinstance(v, list):
                d[a] = [ self.__status_to_dict(s, addr) for s in v ]

            elif a == "args":
                d[a] = self.__parse_arglist(v.split())

            elif a == "content":
                rl = self.__parse_req_line(v)
                if rl: d[a] = rl.items()

            elif a == "status":
                d[a] = arclink_status_string(v)

            else:
                d[a] = v

            if a == "label":
                d['uuid'] = self.__get_uuid(v, addr, status.id)

                desc = self.__get_desc(v)
                if desc: d['description'] = desc.replace('_', ' ')

        return d

    def __get_status(self, server, user, user_ip, req_id, start=0, count=100):
        try:
            (host, port) = server.split(':')
            port = int(port)

        except ValueError:
            logs.error("invalid server address in network XML: %s" % server)
            raise wsgicomm.WIInternalError, "invalid server address"

        try:
            arcl = Arclink()
            arcl.open_connection(host, port, user, user_ip=user_ip,
                timeout=self.status_timeout)

            try:
                #new version requires an arclink update to support pagination
                #status = arcl.get_status(req_id, start, count)
                status = arcl.get_status(req_id)
                status.request = status.request[:count]
                return status

            finally:
                arcl.close_connection()

        except (ArclinkError, socket.error) as e:
            raise wsgicomm.WIServiceError, str(e)

    def __req_to_dict(self, req):
        d = {}

        if req.label:
            d['label'] = req.label

        d['type'] = req.rtype
        d['args'] = req.args

        if req.id:
            d['id'] = req.id
            d['dcid'] = self.__addr_to_dcid(req.address)

        d['line'] = []

        for rl in req.content:
            d['line'].append({'content': rl.items(),
                'routes_tried': [ self.__addr_to_dcid(a) for a in rl.routes_tried ]})

        return d

    def __parse_req_body_json(self, data):
        try:
            parsed = json.loads(data)
            dta = DateTimeAttr()
            content = []

            for items in parsed:
                for i in range(2, 6):
                    if not isinstance(items[i], basestring) or len(items[i]) > 40 or " " in items[i]:
                        raise wsgicomm.WIClientError, "invalid request body"

                content.append(RequestLine(
                    start_time = dta.fromxml(items[0]),
                    end_time = dta.fromxml(items[1]),
                    net = str(items[2]),
                    sta = str(items[3]),
                    cha = str(items[4]),
                    loc = str(items[5]),
                    estimated_size = items[6]))

        except (KeyError, ValueError, IndexError):
            raise wsgicomm.WIClientError, "invalid request body"

        return content

    def __do_request(self, server, user, user_ip, req_desc, req_uuid, req_type, req_args, req_body):
        try:
            mgr = ArclinkManager(server, user, user_ip, socket_timeout=self.request_timeout,
                download_retry=0, max_req_lines=self.max_req_lines, max_req_mb=self.max_req_mb)

            label = "WI:" + req_uuid
            if req_desc: label += ':' + req_desc

            if req_type in ("INVENTORY", "RESPONSE", "ROUTING"): # those are not routed
                req_sent = []
                req_fail = None

                startidx = 0
                while startidx < len(req_body):
                    req = mgr.new_request(req_type, req_args, label)
                    req.content = req_body[startidx:startidx+self.max_req_lines_local]
                    req.submit(server, user)

                    if req.error:
                        raise wsgicomm.WIServiceError, req.error

                    req_sent.append(req)
                    startidx += len(req.content)

            else:
                req = mgr.new_request(req_type, req_args, label)
                req.content = req_body
                # wildcards are already expanded, so we don't need inventory here
                (inv, req_sent, req_fail) = mgr.route_request(req, use_inventory=False)

        except (ArclinkError, socket.error) as e:
            raise wsgicomm.WIServiceError, str(e)

        result = {}
        result['uuid'] = req_uuid

        # successfully routed
        result['success'] = []

        # routing failed
        result['failure'] = []

        for req in req_sent:
            result['success'].append(self.__req_to_dict(req))

        if req_fail:
            result['failure'].append(self.__req_to_dict(req_fail))

        return result

    def __get_meta(self, status, dcid, req_id, vol_id):
        # Filenames would have the form:
        # ArclinkRequest-DcId_ReqId_[VolId]{.seed|.xml}[.bz2][.openssl]
        desc = self.__get_desc(status.request[0].label)

        if desc:
            desc = desc.encode('ascii', 'replace')

        else:
            desc = "ArclinkRequest"

        filename = "%s-%s_%s" % (desc, dcid, req_id)
        encrypted = False

        if vol_id:
            for vol in status.request[0].volume:
                if vol.id == vol_id:
                    if vol.status == STATUS_PROC:
                        return None

                    filename += "_" + str(vol_id)
                    #filename += "-" + str(vol.dcid)
                    encrypted = vol.encrypted
        else:
            if not status.request[0].ready:
                return None

            encrypted = status.request[0].encrypted

        req_type = status.request[0].type
        if req_type == "WAVEFORM":
            content_type = "application/x-seed"

            if "format=MSEED" in status.request[0].args.split():
                filename += '.mseed'
            else:
                filename += '.seed'

        elif req_type == "RESPONSE":
            content_type = "application/x-seed"
            filename += '.dseed'

        else:
            content_type = "application/xml"
            filename += '.xml'

        if "compression=bzip2" in status.request[0].args.split():
            content_type = "application/x-bzip2"
            filename += ".bz2"

        if encrypted:
            content_type = "application/x-openssl"
            filename += ".openssl"

        return (filename, content_type)

    # -------------------------------------------------------------------------
    # Public /request interface
    # -------------------------------------------------------------------------

    def request_types(self, envir, params):
        """List possible request types.

        Input:  (none)

        Output: JSON [list of [requesttype, description]]

        """
        return json.dumps(self.formats)

    def request_nodes(self, envir, params):
        """List nodes of the network.

        Input:  (none)

        Output: JSON [list of [DCID, name]]

        """
        return json.dumps([ (k, v['name']) for (k, v) in self.nodes.iteritems() ])

    def request_status(self, envir, params):
        """Check status of one user request at a server.

        If no request ID is given, the status of all requests at a server
        is returned.

        Input:  server          server DCID
                user            user ID
                request         request ID (optional)
                start, count    pagination

        Output: JSON [list of objects generated from arclink status XML]

        """
        dcid = params.get("server")
        user = params.get("user")
        req_id = params.get("request", "ALL")
        start = params.get("start", 0)
        count = params.get("count", 100)

        if dcid is None:
            raise wsgicomm.WIClientError, "missing server"

        else:
            try:
                server = self.nodes[dcid]['address']

            except KeyError:
                raise wsgicomm.WIClientError, "invalid server"

        if user is None:
            raise wsgicomm.WIClientError, "missing user ID"

        try:
            start = int(start)

        except TypeError:
            raise wsgicomm.WIClientError, "invalid start"

        try:
            count = int(count)

        except TypeError:
            raise wsgicomm.WIClientError, "invalid count"

        user_ip = envir.get('REMOTE_ADDR')
        status = self.__get_status(server, user, user_ip, req_id, start, count)

        try:
            return json.dumps(self.__status_to_dict(status, server)['request'], cls=MyJSONEncoder, indent=4)

        except (KeyError, TypeError):
            raise wsgicomm.WIServiceError, "invalid status"

    def request_submit(self, envir, params):
        """Submit a request.

        Use given server for inventory/routing, DEFAULT_SERVER by default.

        Input:  server          server DCID (optional)
                user            user ID
                requesttype     request type (see also /types)
                compressed      enable compression (optional, true/false,
                                default depends on server)
                responsedictionary  use response dictionary in SEED
                                    (optional, true/false,
                                    default depends on server)
                timewindows     JSON list of time windows (request lines)
                description     optional description

        Output: JSON {"uuid": uuid,
                      "success": [list of successfully routed requests],
                      "failure": [list of requests that could not be routed]}

        """
        dcid = params.get("server")
        user = params.get("user")
        data_format = params.get("requesttype")
        compressed = params.get("compressed")
        resp_dict = params.get("responsedictionary")
        timewindows = params.get("timewindows")
        req_desc = params.get("description")

        if dcid is None:
            server = self.default_server

        else:
            try:
                server = self.nodes[dcid]['address']

            except KeyError:
                raise wsgicomm.WIClientError, "invalid server"

        if user is None:
            raise wsgicomm.WIClientError, "missing user ID"

        if data_format is None:
            raise wsgicomm.WIClientError, "missing request type"

        req_args = {}

        if compressed:
            if compressed.upper() == "TRUE":
                req_args["compression"] = "bzip2"

            elif compressed.upper() != "FALSE":
                raise wsgicomm.WIClientError, "compressed must be TRUE or FALSE"

        if resp_dict:
            if resp_dict.upper() in ("TRUE", "FALSE"):
                req_args["resp_dict"] = resp_dict.lower()

            else:
                raise wsgicomm.WIClientError, "responsedictionary must be TRUE or FALSE"

        if timewindows is None:
            raise wsgicomm.WIClientError, "no time windows given"

        if data_format.upper() == "MSEED":
            req_type = "WAVEFORM"
            req_args["format"] = "MSEED"

        elif data_format.upper() == "FSEED":
            req_type = "WAVEFORM"
            req_args["format"] = "FSEED"

        elif data_format.upper() == "DSEED":
            req_type = "RESPONSE"

        elif data_format.upper() == "INVENTORY":
            req_type = "INVENTORY"
            req_args["instruments"] = "true"

        else:
            raise wsgicomm.WIClientError, "unsupported request type"

        req_body = self.__parse_req_body_json(timewindows)

        if req_desc:
            req_desc = req_desc.replace(' ', '_')

        user_ip = envir.get('REMOTE_ADDR')
        req_uuid = str(uuid.uuid1())
        result = self.__do_request(server, user, user_ip, req_desc, req_uuid, req_type, req_args, req_body)

        return json.dumps(result, cls=MyJSONEncoder, indent=4)

    def request_resubmit(self, envir, params):
        """Re-routes lines with RETRY and NODATA status code to alternative
        servers if available.

        Use given server for inventory/routing, DEFAULT_SERVER by default.

        Input:  server          server DCID (optional)
                user            user ID
                uuid            request UUID
                mode            reroute: try to send NODATA/RETRY lines to next server
                                retry: try to send NODATA lines to next server,
                                    retry RETRY lines on the same server
                                resend: resend the whole request under a new UUID
                                (optional, default "reroute")
                idlist          JSON list of [server, request] pairs that comprise
                                the original request

        Output: JSON {"uuid": uuid,
                      "success": [list of successfully routed requests],
                      "failure": [list of requests that could not be routed]}

        """
        dcid = params.get("server")
        user = params.get("user")
        req_uuid = params.get("uuid")
        mode = params.get("mode", "reroute")
        idlist = params.get("idlist")

        if dcid is None:
            server = self.default_server

        else:
            try:
                server = self.nodes[dcid]['address']

            except KeyError:
                raise wsgicomm.WIClientError, "invalid server"

        if user is None:
            raise wsgicomm.WIClientError, "missing user ID"

        if req_uuid is None:
            raise wsgicomm.WIClientError, "missing request UUID"

        if mode not in ("reroute", "retry", "resend"):
            raise wsgicomm.WIClientError, "invalid mode"

        try:
            idlist = json.loads(idlist)

        except ValueError:
            raise wsgicomm.WIClientError, "invalid or missing idlist"

        user_ip = envir.get('REMOTE_ADDR')

        req_desc = None
        req_type = None
        req_args = None
        resubmit_lines = {}
        no_resubmit_lines = set()

        for idpair in idlist:
            try:
                addr = self.nodes[idpair[0]]['address']
                req_id = str(idpair[1])

            except (KeyError, ValueError, IndexError):
                raise wsgicomm.WIClientError, "invalid (server, request) pair in idlist"

            status = self.__get_status(addr, user, user_ip, req_id)

            for sr in status.request:
                if self.__get_uuid(sr.label, addr, sr.id) != req_uuid:
                    continue

                if req_type is None:
                    req_desc = self.__get_desc(sr.label)
                    req_type = sr.type
                    req_args = self.__parse_arglist(sr.args.split())

                for sv in sr.volume:
                    for sl in sv.line:
                        if sl.content in no_resubmit_lines:
                            continue

                        # if mode == "resend", we resend everything, otherwise
                        # we cosider lines with NODATA or RETRY status
                        if mode == "resend" or sl.status == STATUS_NODATA or sl.status == STATUS_RETRY:
                            try:
                                rl = resubmit_lines[sl.content]

                            except KeyError:
                                rl = self.__parse_req_line(sl.content)
                                if rl:
                                    resubmit_lines[sl.content] = rl

                            if mode == "reroute" or (mode == "retry" and sl.status != STATUS_RETRY):
                                # this line should *not* be routed to the current
                                # server again
                                rl.routes_tried.add(addr)

                        else:
                            no_resubmit_lines.add(sl.content)
                            resubmit_lines.pop(sl.content, None)

        if mode == "resend":
            # generate new UUID
            req_uuid = str(uuid.uuid1())

        if resubmit_lines:
            req_body = resubmit_lines.values()
            self.__estimate_size(req_body)
            result = self.__do_request(server, user, user_ip, req_desc, req_uuid, req_type, req_args, req_body)

        else: # no resubmittable lines found
            result = {}
            result['uuid'] = req_uuid
            result['success'] = []
            result['failure'] = []

        return json.dumps(result, cls=MyJSONEncoder, indent=4)

    def request_download(self, envir, params):
        """Download data.

        Input:  server          server DCID
                user            user ID
                request         request ID
                volume          volume ID (optional)

        Output: iterable datastream.

        """
        dcid = params.get("server")
        user = params.get("user")
        req_id = params.get("request")
        vol_id = params.get("volume")

        if dcid is None:
            raise wsgicomm.WIClientError, "missing server"

        else:
            try:
                server = self.nodes[dcid]['address']

            except KeyError:
                raise wsgicomm.WIClientError, "invalid server"

        if user is None:
            raise wsgicomm.WIClientError, "missing user ID"

        if req_id is None:
            raise wsgicomm.WIClientError, "missing request ID"

        try:
            (host, port) = server.split(':')
            port = int(port)

        except ValueError:
            logs.error("invalid server address in network XML: %s" % server)
            raise wsgicomm.WIInternalError, "invalid server address"

        user_ip = envir.get('REMOTE_ADDR')

        try:
            arcl = Arclink()
            arcl.open_connection(host, port, user, user_ip=user_ip,
                timeout=self.download_timeout)

        except (ArclinkError, socket.error) as e:
            raise wsgicomm.WIServiceError, str(e)

        try:
            status = arcl.get_status(req_id)
            meta = self.__get_meta(status, dcid, req_id, vol_id)

            if meta is None:
                arcl.close_connection()
                raise wsgicomm.WIServiceError, "request is not downloadable"

            it = arcl.iterdownload(req_id, vol_id, raw=True)
            it.filename = meta[0]
            it.content_type = meta[1]
            return it

        except (ArclinkError, socket.error) as e:
            arcl.close_connection()
            raise wsgicomm.WIServiceError, str(e)

    def request_purge(self, envir, params):
        """Delete one user request at a given server.

        Input:  server          server DCID
                user            user ID
                request         request ID

        Output: true

        """
        dcid = params.get("server")
        user = params.get("user")
        req_id = params.get("request")

        if dcid is None:
            raise wsgicomm.WIClientError, "missing server"

        else:
            try:
                server = self.nodes[dcid]['address']

            except KeyError:
                raise wsgicomm.WIClientError, "invalid server"

        if user is None:
            raise wsgicomm.WIClientError, "missing user ID"

        if req_id is None:
            raise wsgicomm.WIClientError, "missing request ID"

        try:
            (host, port) = server.split(':')
            port = int(port)

        except ValueError:
            logs.error("invalid server address in network XML: %s" % server)
            raise wsgicomm.WIInternalError, "invalid server address"

        try:
            arcl = Arclink()
            arcl.open_connection(host, port, user)

        except (ArclinkError, socket.error) as e:
            raise wsgicomm.WIServiceError, str(e)

        try:
            arcl.purge(req_id)
            return json.dumps(True)

        except (ArclinkError, socket.error) as e:
            arcl.close_connection()
            raise wsgicomm.WIServiceError, str(e)

