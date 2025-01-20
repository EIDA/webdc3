#!/usr/bin/env python3
#
# Event services functionality.
#
# Begun by Peter L. Evans, GEOFON team, June 2013
# <pevans@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

"""
Interface to various event services.

Copyright (C) 2013-2015 GEOFON team, Helmholtz-Zentrum Potsdam - Deutsches GeoForschungsZentrum GFZ

Provides a thin wrapper to event services.
Implemented as part of a WSGI application.

Simple usage:

  Visit <http://localhost:port/path/to/event/catalogs>

  Visit <http://localhost:port/path/to/event/geofon/?start=2013-06-01&end=2013-06-15&minmag=6>

Create new event services by subclassing the EventService class
and registering them in the catalog.


This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3, or (at your option)
any later version. For more information, see http://www.gnu.org/

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

"""

import csv
import doctest
import datetime
import json
import math
import os
import tempfile
import re
import sys
import urllib.request, urllib.error, urllib.parse

sys.path.append('..')  # for wsgicomm...
import wsgicomm

tempdir = tempfile.gettempdir()

try:
    import seiscomp.logs as logs
except ImportError:
    class logs(object):
        """
        Substitute for seiscomp.logs class??
        """
        def __init__(self):
            print("Error importing seiscomp.logs.", file=sys.stderr)
            print("Sending errors here instead.", file=sys.stderr)

        def info(s):
            print("[info] %s" % s, file=sys.stderr)

        def error(s):
            print("[error] %s" % s, file=sys.stderr)

        def debug(s):
            print("[debug] %s" % s, file=sys.stderr)

def hush(args):
    pass

try:
    import seiscomp3.Seismology as Seismology
except ImportError:
    logs.warning("Couldn't import seiscomp3.Seismology ... do you have the SeisComP libraries installed?")
    class Seismology(object):
        class Regions(object):
            def getRegionName(self, flat, flon):
                """Reimplementation of SeisComP method"""
                if flat > 0:
                    name = "Region N"
                else:
                    name = "Region S"

                name += "%i" % (int(abs(flat) / 10.0))
                if flon > 0:
                    name += "E"
                else:
                    name += "W"
                name += "%i" % (int(abs(flon) / 22.5))
                return name

try:
    import seiscomp3.Math as Math
except ImportError:
    logs.warning("Couldn't import seiscomp3.Math ... do you have the SeisComP libraries installed?")
    class Math(object):
        def delazi(self, lat_0, lon_0, lat_1, lon_1):
            return [_delazi(lat_0, lon_0, lat_1, lon_1), None, None]

class WI_Module(object):

    _EventsVersion = "2015.035"
    # The basic structure of this template for errors (and the
    # HTTP error codes which should be used) is given in the
    # FDSN web services specification, so don't change this
    # without good reason.
    # Ref: <http://www.fdsn.org/webservices/>
    #
    # I think this has to go in WI_Module, not EventService,
    # because it may be needed even when there is no service.
    _EventsErrorTemplate = """Error %(err_code)s: %(err_desc)s

Service '%(service)s': %(details)s.

Request:
%(url)s

Request Submitted:
%(date_time)s

Service version:
%(version)s
"""

    def __init__(self, wi):
        if wi is None:
            return

        known_handlers = ('comcat', 'emsc', 'fdsnws', 'geofon', 'meteor', 'neic', 'parser')

        abort = False
        config = wi.getConfigTree('event')

        self.verbose = int(config['verbosity'])
        logs.notice('Event verbosity level = %i' % self.verbose)
        if self.verbose < 4:
            logs.debug = hush
        else:
            logs.notice('logs.debug is enabled')
        if self.verbose < 3:
            logs.info = hush
        else:
            logs.notice('logs.info is enabled')

        self.services = dict.fromkeys(config['catalogs']['ids'], {})
        for k in list(config['service'].keys()):
            self.services[k] = config['service'][k]
            h = self.services[k].get('handler', None)
            # Exception for old config files:
# FIXME - unneeded??
            if (h is None) and (k in known_handlers):
                h = k
##            # Assign a handler if none was provided in configuration
# #           if not self.services[k].has_key('handler'):
##                self.services[k]['handler'] = h  ## better: make this a function handle.

        self._EventServiceCatalog = {}
        for s in self.services:
            description = self.services[s].get('description', None)
            handler = self.services[s].get('handler', None)
            if description:
                self._EventServiceCatalog[s] = (description, handler)
        self._EventServicePreferred = config['catalogs']['preferred']
        self.registeredonly = wi.getConfigBool('event.catalogs.registeredonly', True)
        logs.info("Only serve registered event services: %s" % (self.registeredonly))
        logs.info("Registered event service(s):")
        for s in sorted(self.services):
            logs.info("%24s: %s" % ("'" + s + "'",
                                    self._EventServiceCatalog.get(s, (None,))[0]))
        logs.info("Preferred event service: %s" % (self._EventServicePreferred))

        #NOT NEEDED: self.defaultLimit = config['defaultLimit']

        wi.registerAction("/event/catalogs", self.catalogs)
        wi.registerAction("/event/parse", self.parse, 'columns', 'informat', 'input')

        # Trick to get all defined catalogs registered:
        for service in self._EventServiceCatalog:
            wi.registerAction("/event/%s" % (service), self.query)
        # And some more, just for testing:
        wi.registerAction("/event/meteor", self.query)
        wi.registerAction("/event/dumpconfig", self.dumpConfig)

        # Create handlers for all services:
        # Should these options apply to *all* services from this server??
        options = {}
        options['lookupIfEmpty'] = wi.getConfigBool('event.names.lookupIfEmpty', True)
        options['lookupIfGiven'] = wi.getConfigBool('event.names.lookupIfGiven', False)
        options['defaultLimit'] = wi.getConfigInt('event.defaultLimit', 800)

        logs.info("Options:")
        for k in sorted(options):
            logs.info('%24s: %s' % (k, str(options[k])))

        self.es = dict()
        for s, props in self.services.items():

            start_time = datetime.datetime.now()

            # April 2014: A handler specification in the configuration
            # file is now mandatory:
            #   event.service.{servicename}.handler = {handler}
            #
            # except for the following "legacy" services, for which
            # we allow the handler name to be the service name.
            # This exception means users don't have to update their
            # old webinterface.cfg. It should be removed in future.
            #
            if s in known_handlers and props.get("handler", None) is None:
                h = s
                logs.notice("Assuming handler '%s'; you should set this explicitly in webinterface.cfg with:" % h)
                logs.notice("  event.service.%s.handler = '%s'" % (s, h))
            else:
                try:
                    h = props["handler"]
                    if not h in known_handlers:
                        logs.warning("Unknown handler '%s' configured for service '%s', but continuing anway!" % (h, s))
                        continue
                except KeyError:
                    logs.error("No handler configured for service '%s', aborting!" % s)
                    abort = True
                    continue
##            ##try:
##            h = props.get('handler', s)   ## Or raise if no handler set?
##            ##except KeyError:
##            ##    logs.error("No event service handler was set for service '%s'; fix in webinterface.cfg." % (s))
##            ##    h = s
            logs.debug("Handler for service id=%s is '%s'" % (s, h))

            # All known handlers:
            if h == 'geofon':
                es = ESGeofon(s, options, props['baseURL'], props['extraParams'])
            elif h == 'comcat':
                es = ESComcat(s, options, props['baseURL'], props['extraParams'])
            elif h == 'emsc':
                es = ESEMSC(s, options, props['baseURL'], props['extraParams'])
            elif h == 'fdsnws':
                es = ESFdsnws(s, options, props['baseURL'], props['extraParams'])
            elif h == 'meteor':
                es = ESMeteor(s, options)
            elif h == 'neic':
                es = ESNeic(s)
            elif h == 'parser':
                es = ESFile(s, options)
            else:
                raise SyntaxError("Uncaught handler %s" % h)
            self.es[s] = es

            end_time = datetime.datetime.now()
            #Python 2.7: logs.debug("Created new event service '%s' in %g s" % (s, (end_time-start_time).total_seconds()))
            logs.notice("Created new event service '%s', handler %s" % (s, h))
            for p in ('handler', 'baseURL', 'extraParams'):
                logs.debug('%24s: %s' % (p, props.get(p)))

        if (abort): raise SyntaxError("Configuration problem(s), see the logs.")

    def dumpConfig(self, envir, params):
        return ("Event services configuration at %s\n" % str(datetime.datetime.now()) + str(self),)

    def catalogs(self, envir, params):
        return self.getEventsCatalog()

    def parse(self, envir, params):
        return self.parseUserTextFile(envir, params)

    def query(self, envir, params):
        return self.getEvents(envir, params)

    def getEventsCatalog(self):
        """Returns text/plain JSON-formatted description list of service names.

        Each service name has a description (string) and a list of
        capabilities describing what resource parameters can be
        handled by that service.

        Not configurable, which is inconvenient.

        """
        handler_capabilities_default = {"hasDate": True,
                        "hasRectangle": True,
                        "hasCircle": False,
                        "hasDepth": False,
                        "hasMagnitude": True,
                        "description": None}

        d = dict.fromkeys(list(self._EventServiceCatalog.keys()))
        for k in list(d.keys()):
            d[k] = dict(handler_capabilities_default)
            d[k]["description"] = self._EventServiceCatalog[k][0]
            handler = self._EventServiceCatalog[k][1]

            # These are capabilities of the *handler type* not the id.
            if handler == "geofon":
                d[k]["hasCircle"] = True
                d[k]["hasDepth"] = True
            if handler == "comcat":
                d[k]["hasDepth"] = True
            elif handler == "emsc":
                d[k]["hasDepth"] = True
            elif handler == "fdsnws":
                d[k]["hasDepth"] = True

        # A hack here to force the preferred key to come first:
        indent = None
        if indent:
            joint = ",\n" + indent * " "
        else:
            joint = ", "
        prefService = self._EventServicePreferred

        if 'isc' in list(d.keys()):
            rest = d.pop('isc')
        else:
            rest = None

        left = json.dumps({prefService: d.pop(prefService)}, indent=indent)[0:-1]
        right = json.dumps(d, indent=indent).lstrip("{")
        tmp = left.rstrip() + joint + right.lstrip()

        if (rest is not None):
            left = tmp[0:-1]  # Only remove the final '}'
            right = json.dumps({'isc': rest}, indent=indent).lstrip('{')
            tmp = left.rstrip() + joint + right.lstrip()

        # DEBUG: Check the output string is loadable.
        tmp2 = json.loads(tmp)
        assert len(tmp2) == len(self._EventServiceCatalog)

        return tmp
        ##return json.dumps(self._EventServiceCatalog)

    def __str__(self):
        """Report what is known about catalogs. This is for
        debugging/maintenance, and should not be exposed across the
        web server.

        """
        s = ""
        s += "Verbosity: %i\n" % (self.verbose)
        s += "Registered services:\n"
        for k in sorted(self.services):
            s += "Service '%s'\t%s\n" % (k, self.services[k])
        s += "Preferred: %s\n" % self._EventServicePreferred
        for k in self._EventServiceCatalog:
            s += "Service '%s': %s\n" % (k, str(self._EventServiceCatalog[k]))
        s += "Registered only? " + str(self.registeredonly) + "\n"
        s += "defaultLimit: " + str(self.options['defaultLimit']) + "\n"
        s += "lookupIfEmpty? " + str(self.options['lookupIfEmpty']) + "\n"
        s += "lookupIfGiven? " + str(self.options['lookupIfGiven']) + "\n"
        return s

    def parseUserTextFile(self, envir, params):
        """Parse a user-supplied catalog.

        Input:
          informat={string} ## The INPUT format. So far CSV, later can be QML, GeoJSON
          format={string}   ## The OUTPUT format. Default 'json', others: 'csv'
          columns={string}  ## Comma-separated list of columns
                            ## in the supplied CSV file, from:
                    ('latitude', 'longitude', 'depth', 'time', 'ignore')
          input=<user supplied catalog sent as POST>
        Returns: JSON - a list of events.

        """
        params_white_list = ('informat', 'format', 'columns', 'input')
        es = self.es['parser']
        # Re-use existing service ##es = ESFile("file", options)
        for name in list(params.keys()):
            if name not in params_white_list:
                return [bodyBadRequest(envir, 'Unknown parameter name supplied', 'parser')]

        return es.handler(envir, params)

    def getEvents(self, environ, params):
        """Event web service.

        Returns parametric data for events drawn from one of many
        target event catalogs. Requests can be constrained by some
        or all of the following:

        (service,
         start date-time,
         end date-time (with the FDSN interpretation: no time ==> 00:00:00
                        i.e. the START of the day.)
         max/min latitude/longitude,
         max/min depth,
         max/min magnitude,
         other constraints,...)

        URL: /path/to/event/{service}?param1=value1&param2=value2&...
        The {service} component is mandatory.

        Returns:
          string, a list of events and their parameters.

        Depending on the 'format' parameter, the output could be JSON
        (either rowmajor or colmajor), text, comma-separated
        (csv), or something use. Use 'format=raw' to see what was
        received fom the target service.

        For CSV there is one event per line. The order of columns is:
            "Event ID";"F-E Region";Magnitude;Status;"Origin time";Latitude;Longitude;"Depth (km)";Flags
    CHECK
        This is chosen for compatibility with the webinterface front end.

        Lines beginning with '#' are comments and are to be ignored.
        (Thus an event ID may never begin with '#'.)
        The first line, with or without comment, may also need ignoring. :FIXME:

        """
        path = environ.get('PATH_INFO', '').lstrip('/')
        parts = path.split('/', 3)
        command = parts[0].lower()
        assert(command == 'event')

        if len(parts) == 1:
            # There was no slash after "event", therefore no service.
            # In future, this could return the catalog!
            return [bodyBadRequest(environ, "No service name given, try /event/catalogs")]

        service = parts[1].lower()
        service = re.escape(service)
        service = re.sub(r'([^a-zA-Z0-9-]+)', ' ', service)

        if len(parts) > 2:
            return [bodyBadRequest(environ, "Extra URL component after service name")]

        # For testing, it is nice to allow services e.g. '/event/meteor' which
        # are not in the "published" catalog. But a site which is "live"
        # should not do that. Operators can configure which services they
        # offer.
        if self.registeredonly and not service in self._EventServiceCatalog:
            return [bodyBadRequest(environ, "Unknown service name", service)]

        if service in list(self.services.keys()):
            #NOT NEEDED?:
            parameters = urllib.parse.parse_qs(environ.get('QUERY_STRING', ''))
            ##Should be: parameters = params
            return self.es[service].handler(environ, parameters)
        else:
            return [bodyBadRequest(environ, "Unknown service name", service)]



# ----------------------------------------------------------------------

def _delazi(lat_0, lon_0, lat_1, lon_1):
    """Distance between two points on a sphere

    Inputs:
     (lat_0, lon_0) - latitude and longitude of the first point.
     (lat_1, lon_1) - latitude and longitude of the second point.
    Returns:
     d - spherical distance

    All angles are in *degrees*.

    Position vectors are:
     (x, y, z) = a*[ cos(lon)*cos(lat), sin(lon)*cos(lat), sin(lat) ]
    Spherical distance is arccos( v_0 dot v_1 ).

    WARNING: Probably inaccurate near 0 and 180 deg distance, where cos(dotp) = 1.

    """
    deg2rad = math.pi / 180.0
    lat_0 = lat_0 * deg2rad
    lon_0 = lon_0 * deg2rad
    lat_1 = lat_1 * deg2rad
    lon_1 = lon_1 * deg2rad

    #x0 = math.cos(lon_0)*math.cos(lat_0)
    #x1 = math.cos(lon_1)*math.cos(lat_1)
    #y0 = math.sin(lon_0)*math.cos(lat_0)
    #y1 = math.sin(lon_1)*math.cos(lat_1)
    delta_lon = (lon_1 - lon_0) % (2 * math.pi)
    term_1 = math.cos(lat_0) * math.cos(lat_1) * math.cos(delta_lon)
    z0 = math.sin(lat_0)
    z1 = math.sin(lat_1)
    #dotp = x0 * x1 + y0 * y1 + z0 * z1
    dotp = term_1 + z0 * z1

    # Need the angle in (0, 180]:
    if dotp == -1:
        d = math.pi  # anti-parallel, 180 degrees
    else:
        d = math.acos(dotp)
    #elif (dotp < 0):
    #    d = math.pi - math.acos(dotp)  # not needed, Python acos does this.

    d = d / deg2rad
    #print 'TEST', lat_0, lon_0, lat_1, lon_1, dotp, d
    assert(d >= 0.0)
    assert(d <= 180.0)
    return d


verbosity = 2

def repr_dialect(d):
    """Describe 'd', a Dialect object from the csv class."""
    return """
     |  delimiter = '%s'
     |  doublequote = '%s'
     |  escapechar = '%s'
     |  lineterminator = '%s'
     |  quotechar = '%s'
     |  quoting = '%s'
     |  skipinitialspace = '%s'
""" % (d.delimiter, d.doublequote,
       d.escapechar, repr(d.lineterminator),
       d.quotechar, d.quoting, d.skipinitialspace)

def date_T(arg):
        """Dates should be 'yyyy-mm-ddThh:mm:ss', with no trailing Z or zone or milliseconds.

        >>> date_T("2013-06-15T10:39:43")
        '2013-06-15T10:39:43'
        >>> date_T("2013-06-15T10:39:43Z")
        '2013-06-15T10:39:43'
        >>> date_T("2013-06-15T10:39:43.000+00:00")
        '2013-06-15T10:39:43'
        >>> date_T("2013-06-15 10:39:43")
        '2013-06-15T10:39:43'

        """
#        if arg.endswith("Z"):
#            tmp = arg[0:-1]
#        elif arg.endswith("+00:00"):
#            tmp = arg[0:-len("+00:00")]
#        else:
#            tmp = arg

        tmp = arg.replace('Z', '', 1)
        if tmp.endswith("+00:00"):
            tmp = tmp[0:-len("+00:00")]
        dot = tmp.find(".")
        if dot > -1:
            tmp = tmp[0:dot]
        return tmp.replace(' ', 'T', 1)

def tagged(tag, strings, attrs={}):
    """Mark up all the items in the list 'strings' with the same tag 'tag'.

    Inputs:
      tag - an HTML/SGML/XML tag name, e.g. "div"
      strings - a string or list of strings
      attrs - dictionary of attributes to apply to the tag.

    Returns:
      string with each item in 'strings' marked up with 'tag' and
      all the attributes in 'attrs'.

    >>> tagged('td', ['the', 'big', 'pig'], {'color': 'red'})
    '<td color="red">the</td><td color="red">big</td><td color="red">pig</td>'

    """
    temp = ""
    attr_str = ""
    for a in sorted(attrs.keys()):
        attr_str += ' %s="%s"' % (a, attrs[a])

    # polymorphic - don't explode strs into chars!
    if isinstance(strings, str):
        temp += "<%s%s>%s</%s>" % (tag, attr_str, strings, tag)
    else:
        for item in strings:
            temp += "<%s%s>%s</%s>" % (tag, attr_str, item, tag)
    return temp


def _urlString(environ):
    """
    What is the URL which was used to visit me?
    """
    if environ['QUERY_STRING']:
        return environ.get('wsgi.url_scheme', 'unk') + "://" + environ.get('HTTP_HOST', '') + environ['PATH_INFO'] + '?' + environ['QUERY_STRING']
    else:
        return environ.get('wsgi.url_scheme', 'unk') + "://" + environ.get('HTTP_HOST', '') + environ['PATH_INFO']


"""The defaultParamMap dictionary defines a list of request
parameters that an FDSN-type events web service might accept.
See the WADL for this service at
<http://service.iris.edu/fdsnws/event/1/application.wadl>.

Event service handlers can load this dictionary with values
describing the parameter names used in their target service. For
example, the FDSN interface specifies maxlon, but the target
service requires longitude_max. Then the dictionary would have an
entry

  paramsMap['maxlon'] = 'longitude_max'

This model assumes that the *values* don't need to be changed
from those specified in the FDSN web service. For example, if
a target service requires
"start_day={dd}&start_mon={mm}&start_year={year}" rather than
the FDSN-style 'start={year}-{mm}-{dd}'. In such a case the
handler for this event service needs to do additional work.

NOTE: Another choice of default would have been to set the value
to the key, so this is the identity map, and keys are just passed on.
For now I take a more conservative position, and require
keys to be explicitly turned on.

There are three special values, '-UNIMPLEMENTED' and '-DROP':

    '-UNIMPLEMENTED': if this parameter is presented, raise an error!

    '-DROP': do not pass this parameter on to the target service.
      This can be useful if the event service handler will take
      care of complying with the constraint.

    ('func', functionhandle): apply the function 'functionhandle'
      to the value.

"""
defaultParamNames = ['start', 'end',
                     'maxmag', 'minmag',
                     'maxdepth', 'mindepth',
                     'maxlat', 'minlat',
                     'maxlon', 'minlon',
                     'lat', 'lon',
                     'maxradius', 'minradius',
                     'magnitudetype',
                     'preferredonly',
                     'eventid',
                     'includeallmagnitudes',
                     'includearrivals',
                     'limit',
                     'offset',
                     'orderby',
                     'contributor',
                     'catalog',
                     'updatedafter']
defaultParamMap = dict.fromkeys(defaultParamNames, '-UNIMPLEMENTED')


def process_parameters(paramMap, parameters):
    """
    Inputs:
        paramMap = mapping of acceptable parameter names to the target service
        parameters = something like the QUERY_STRING of the request.

    Returns:
        pairs (for good arguments to be passed on)
        bad_list (for arguments which should cause an error)
        hold_dict (dictionary for arguments to be processed in the middle)

    FIXME: This is a mish-mash - hold_dict is a dict of (name, value)

    """
    holdParamsList = ('format', 'limit')

    if (verbosity >= 5): print("ParamMap:", paramMap)

    d = {}
    pairs = []
    bad_list = []
    hold_d = {}

    for name in parameters:
        if name in paramMap:
            image = paramMap[name]
            ### print >>sys.stdout, "name '%s' -> '%s' [%s]" % (name, image, str(parameters[name]))
            value = urllib.parse.quote(parameters[name][0])
            d[name] = value

            if image[0] == 'func':
                paramhandler = image[1]  # function handle
                #logs.debug("parameter '%s' : handling with %s" % (name, paramhandler))
                extra_pairs = paramhandler(name, parameters)
                pairs.extend(extra_pairs)

            elif image.startswith('-DROP'):
                # These shouldn't be passed on to the target,
                # but shouldn't bother us either.
                # There should be none of these, but it's convenient.
                pass

            elif image.startswith('-'):
                bad_list.append(name)

            else:
                pairs.append("%s=%s" % (paramMap[name], d[name]))

        if name in holdParamsList:
            value = urllib.parse.quote(parameters[name][0])
            hold_d[name] = value

    return pairs, bad_list, hold_d


def floatorwhat(arg, replacement):
    """Don't be tripped up by an empty string.

    Inputs:
      arg - string, to attempt to convert to a float
      replacement - whatever
    Returns
      a valid float, or else the replacement object.

    >>> floatorwhat('7.0', 'X')
    7.0
    >>> floatorwhat('x6y', 'X')
    'X'
    >>> floatorwhat('5', 'X')
    5.0

     """
    try:
        return float(arg)
    except ValueError:
        return replacement

def floatorzero(arg):
    """Some catalogs can have an empty string for magnitude, depth, etc.
    Return 0 in that case.
    """
    return floatorwhat(arg, 0.0)

def floatordash(arg):
    return floatorwhat(arg, '--')


class EventWriter(object):
    """Output methods for serializing the EventData container.

    Constructor requires a pointer to the data held in the container.
    This class is subclassed to provide different formats:
        CSV, JSON, [QuakeML in the future], etc.

    """

    # Required for header info for both CSV and JSON formats:
    # NOTE the names here must match what is expected by the webinterface JavaScript.
    output_header = ('datetime', 'magnitude', 'magtype', 'latitude', 'longitude', 'depth', 'key', 'region')

    def __init__(self, data):
        self.data = data

    def write_begin(self, limit):
        return '[dummy start]'

    def write_one(self, index):
        if index >= 0 and index < len(self.data):
            return str(index) + ': ' + str(self.data[index])
        else:
            return ''

    def write_events(self, start, limit):
        s = ''
        last = min(start + limit, len(self.data))
        for k in range(start, last):
            s += self.write_one(k)
        return s

    def write_end(self, limit):
        return '[dummy done]\n'

    def write_all(self, limit):
        """All-in-one-hit serialisation."""
        return self.write_begin(limit) + self.write_events(0, limit) + self.write_end(limit)


class EventWriterCSV(EventWriter):
    '''Write some events as a Comma Separated Values (CSV) table.

    For CSV output:
    There should be one row per event, and a maximum of 'limit' rows,
    plus one header row. The output delimiter is '|'.

    The row columns are defined in 'output_header'.

    '''
    delimiter = '|'
    lineterminator = '\n'
    count = None
    fid = None
    #UNUSED?filters = (date_T, floatordash, float, float, floatordash, None, None)

    def __init__(self, data):
        """Why is an explicit init() method needed for
        EventWriterCSV, but not for EventWriterJSON?"""

        #print "EventWriterCSV::init says hello world!"
        #if data:
        #    print len(data)
        #else:
        #    print
        self.data = data
        self.helper = Helpers()

    def write_begin(self, limit):
        self.count = 0
        #TMPFILE self.fid = open('local.csv', 'wb')
        self.fid = tempfile.TemporaryFile('w+b')
        self.writer = csv.writer(self.fid)
#*****USE self.output_header?
        header = ("Event Time", "Mag", "Lat", "Lon", "ID", "Depth", "Region")
        self.writer.writerow(self.output_header)
        return ''  ### self.delimiter.join(self.output_header) + self.lineterminator

    def write_one(self, index):
        #DEBUG print "write_one", index, len(self.data)
        if self.data and index >= 0 and index < len(self.data):
            self.count += 1
            ev = self.data[index]
            self.writer.writerow(ev)

            #UNUSED new_row = self.helper.filtercols(ev, self.filters)
            #return self.delimiter.join(new_row) + self.lineterminator
        return ''

    def write_end(self, limit):
        #TMPFILE self.fid.close()
        #TMPFILE self.fid = open('local.csv', 'rb')
        self.fid.seek(0)
        s = ""
        for line in self.fid.readlines():
            s += line
        self.fid.close()
        return s + "# Lines: %i\n" % self.count


class EventWriterJSON(EventWriter):
    """Write some events as a JSON table.

    JSON output includes:
    - a header row
    - zero or more events, one row per event, and a maximum of 'limit' events.

    The row columns are defined in 'output_header'. For JSON
    output to the webinterface front end the column ordering and
    types of values must conform to what webinterface expects.
    NOTE: It is assumed/hoped the eventwriter object's data is already
    safe enough for out as HTML. i.e. was validated on input.

    """
    def write_all(self, limit):
        last = min(limit, len(self.data))
        #print "EventWriterJSON::write_all len=%i limit=%i last=%i" % (len(self.data),
        #                                                              limit, last)
        return json.dumps([self.output_header] + self.data[0:last])


class EventWriterFDSNText(EventWriter):
    """Write some events as fdsnws-event format=text output.

    The specification for this output is at
    http://www.fdsn.org/webservices/FDSN-WS-Specifications-1.1.pdf

    """
    fdsnws_headers = ('EventID', 'Time', 'Latitude', 'Longitude',
                      'Depth/km', 'Author', 'Catalog',
                      'Contributor', 'ContributorID',
                      'MagType', 'Magnitude', 'MagAuthor',
                      'EventLocationName')

    def write_one(self, index):
        #DEBUG print "write_one", index, len(self.data)
        if self.data and index >= 0 and index < len(self.data):
            self.count += 1
            ev = self.data[index]
            self.writer.writerow(ev)

            #UNUSED new_row = self.helper.filtercols(ev, self.filters)
            #return self.delimiter.join(new_row) + self.lineterminator
        return ''

    def write_all(self, limit):
        sep = '|'
        crlf = '\r\n'

        last = min(limit, len(self.data))

        def rows(data, first, last):
            buf = ""
            mapping = (6, 0, 3, 4, 5, None, None, None, None, 2, 1, None, 7)
            h = Helpers()
            for r in range(first, last):
                row = data[r]
                buf += sep.join(str(x) for x in h.mapcols(row, mapping)) + crlf
            return buf

        h = sep.join(self.fdsnws_headers)
        return h + crlf + rows(self.data, 0, last)


class EventData(object):
    """Container class for just the info we should output."""

    column_names =  ("datetime", "magnitude", "magtype",
                     "latitude", "longitude", "depth",
                     "key", "region")

    def __init__(self, data=None):
        if data:
            self.data = [data]
        else:
            self.data = []

        # The following dictionary gives class names which handle each format:
        self.handlers = {'raw': EventWriter(self.data),
                         'csv': EventWriterCSV(self.data),
                         'json': EventWriterJSON(self.data),
                         'fdsnws-text': EventWriterFDSNText(self.data)}

    def append(self, new_data):
        self.data.append(new_data)

    def data(self):
        return self.data

    def column(self, col):
        """Return a 'column vector' of all items in column col."""
        if isinstance(col, str):
            col = self.column_names.index(col)  # ValueError if the value is not present.
        assert col >= 0
        t = []
        for event in self.data:
            t.append(event[col])

        assert len(t) == len(self.data)  ## Assumes no missing values
        return t

    def json_loads(self, s):
        """Speed loader from JSON string, for testing. NO CHECKING!

        Seems to read everything in as Unicode strings e.g. u'54'.
        """
        if not s:
            logs.error("json_loads: empty string")
            return   # Is this wise?

        try:
            tmp = json.loads(s)
        except:
            logs.error("json_loads: Loading failed, len(s) = %i" % len(s))
            raise

        # Throw away header:
        #self.data = tmp[1:]

        # Throw away header, convert the rest:
        for row in tmp[1:]:
            for q in range(1, 5):
                row[q] = floatorwhat(row[q], None)
            self.data.append(row)

    def __len__(self):
        if self.data:
            return len(self.data)
        else:
            return 0

    def __str__(self):
        return "EventData object with %i item(s): " % (self.__len__()) + str(self.data)

    def write_begin(self, fmt, limit):
        return self.handlers[fmt].write_begin(limit)

    def write_one(self, fmt, index):
        return self.handlers[fmt].write_one(index)

    def write_events(self, fmt, start, limit):
        return self.handlers[fmt].write_events(limit)

    def write_end(self, fmt, limit):
        return self.handlers[fmt].write_end(limit)

    def write_all(self, fmt, limit):
        """All-in-one-hit serialisation."""
        #print "EventData::write_all() fmt=", fmt
        return self.handlers[fmt].write_all(limit)


class Helpers(object):
    def mapcols(self, row, mapping):
        """Select interesting columns from a row.

        Inputs:
          row - the old row to be operated on.

          mapping - list/tuple describes a "selection" from row:
            element i tells where to get item i from in the original
            row. Thus 'mapping' is the *inverse* map from new rows to
            old rows, or the forward map from new to old. The elements
            of 'mapping' are integer indices between 0 and len(row)-1,
            or None.

        Feature/bug: If None is given in mapping element i, the output
        will be the empty string. (Not None - that creates problems
        for the filter functions which come later.)

        Returns: new row with n items, if len(mapping) = n.
        Example:

        >>> row = ['a', 'b', 'c', 'd', 'e']
        >>> mapping = (4, 0, 2)
        >>> h = Helpers()
        >>> print h.mapcols(row, mapping)
        ['e', 'a', 'c']
        >>> print h.mapcols(row, (4, None, 0, 2))
        ['e', '', 'a', 'c']

        """
        assert max(mapping) < len(row)
        #assert min(mapping) >= 0  # Fails when 'None' is allowed.
        new_row = []
        for j in mapping:
            if j is None:
                new_row.append('')
            else:
                new_row.append(row[j])
        assert(len(new_row) == len(mapping))
        return new_row

    def filtercols(self, row, filters):
        """Apply a different function to each element of row.

        Inputs:
          row - list of objects to be mapped.
          filters - list of function handles

        Returns:
          new list of objects, where the ith element is the result of
          applying the ith filter function to the ith element in row.

        If filter[i] is None, no function is applied.
        """
        assert len(row) == len(filters)
        new_row = []
        for j in range(len(row)):
            #DEBUG print >>sys.stderr, j, filters[j], "applied to", row[j]
            if filters[j]:
                try:
                    fun = filters[j]
                    new_row.append(fun(row[j]))
                except ValueError as e:
                    logs.error("filtercol: column %i failed - %s applied to %s" % (j, str(filters[j]), str(row[j])))
                    raise ValueError(e)
            else:
                new_row.append(row[j])
        assert len(new_row) == len(row)
        return new_row


class EventResponse(object):
    """Not sure yet."""
    def __init__(self, dialect, mapping, filters, options):
        self.csv_input_dialect = dialect
        self.input_mapping = mapping
        self.filters = filters
        self.rows = None
        self.cols = {'otm': 0, 'mag': 1, 'mtyp': 2,
                     'lat': 3, 'lon': 4, 'dep': 5,
                     'id': 6, 'region': 7}
        self.ed = EventData()
        self.lookupIfEmpty = options['lookupIfEmpty']
        self.lookupIfGiven = options['lookupIfGiven']

    def load_plain(self, rows):
        """
        Modifies:
          self.rows - in case of raw output. FIXME - shouldn't save both.
        """
        self.rows = rows

    def load_csv(self, rows, limit, dialect=None):
        """
        Inputs:
          rows - string, data from target service.
          limit - int, maximum number of events to load, or None (no limit,
                  load all items found in 'rows').
          dialect - a csv.Dialect object.

        Normally uses self.csv_input_dialect instead of dialect. ???

        Returns:
          nothing

        Modifies:
          self.ed - the event data container: appends event objects

        """
        self.ed = EventData()
        helper = Helpers()

        # Save a copy. FIXME
        fid = tempfile.NamedTemporaryFile('wt', prefix='wi', suffix='csv.txt', dir=tempdir, delete=False) #change wb to wt RCP (??)
        fname = fid.name
        numrows = 0
        for row in rows.splitlines():
            numrows += 1
            print(row, file=fid) #added encoding RCP
            if (not limit) or numrows > 2 * limit:
                break
        fid.close()

        if dialect is None:
            sniffer = csv.Sniffer()
            guess = sniffer.sniff(rows)
            logs.debug("Guessed dialect: %s" % (repr_dialect(guess)))
#
# Can't re-read from rows, so I needed to write to a temporary file??? FIXME
# FIXME: open('r'), read(size), fid.seek(0) start reader ??
#
        try:
            fid = open(fname, 'rt') #change rb to rt (RCP)
        except:
            logs.debug("Oops, temporary file '%s' couldn't be opened.", fname)
            raise

        logs.info('Reopened ' + fname)
        reader = csv.reader(fid, dialect)
        #logs.error("Reader dialect: %s" % (repr_dialect(dialect)))

        numrow = 0
        header = next(reader)
        #print >>sys.stderr, "load_csv: Header:", header
        if len(header) > 1:
            # probably worked
            header_cols = header
        else:
            logs.error("Header unreadable: %s..." % (str(header[0])))
            header_cols = header[0].split('|')
            if len(header_cols) == 1:
                # Try again with ';'
                header_cols = header[0].split(';')

        if verbosity > 3:
            logs.error("Header (%i cols): %s" % (len(header_cols), str(header_cols)))
            logs.error("Mapping: %s" % (str(self.input_mapping)))
            logs.error("Header after mapping: %s" % str(helper.mapcols(header_cols, self.input_mapping)))
        new_header = helper.mapcols(header_cols, self.input_mapping)
        #s += "|".join(new_header) + "\n"

        for row in reader:
            if len(row) > 0:
                numrow += 1
                if verbosity > 3:
                    logs.error("Row %i: %s" % (numrow, str(row)))

                first = row[0]
                if first.startswith('#'):
                    # Comment line, so ignore it
                    continue
                #s += "|".join(row) + "\n"
                new_row = helper.mapcols(row, self.input_mapping)
                new_row = helper.filtercols(new_row, self.filters)
                self.ed.append(new_row)
                if (limit) and numrow > limit:
                    break
        fid.close()
        os.unlink(fname)
        return

    def _lookup_region(self, ev):
        lat = ev[self.cols['lat']]
        lon = ev[self.cols['lon']]

         # FIXME: Why are lat/lon not already floats?
        try:
            flat = float(lat)
            flon = float(lon)
        except ValueError:
            logs.warning("In _lookup_region: lat=%s lon=%s are not convertable to float" % (str(lat), str(lon)))
        return Seismology.Regions().getRegionName(flat, flon)


    def _fill_region(self, ev):
        """Should we look up a region for this event?

        Inputs:
            ev - an event row
        Output:
            ev - may be modified
        Calls to _lookup_region() might be expensive; avoid them if
        they aren't wanted.

        """
        col = self.cols['region']
        if self.lookupIfEmpty or self.lookupIfGiven:
            old = ev[col].strip()
            new = old
            if old == "" or old == "-" or old == "--":
                if self.lookupIfEmpty:
                    new = self._lookup_region(ev)
            else:
                if self.lookupIfGiven:
                    new = self._lookup_region(ev)
            if new != old:
                #logs.debug("(%s -> %s)" % (old, new))
                ev[col] = new

    def fill_keys(self, prefix="row", keyIfGiven=False):
        """Use this function to assign event IDs.

        prefix - string, used to make ids like "{prefix}{nnn}"
                 where nnn is the row number.

        keyIfGiven - boolean, replace id even when there is
                     one already present for an event.

        """
        num_rows = len(self.ed.data)
        if num_rows < 1:
            return

        seq_fmt = "%%0%1ii" % (int(math.log10(num_rows)) + 1)
        col = self.cols['id']
        for row in range(num_rows):
            ev = self.ed.data[row]
            if len(ev[col]) == 0 or keyIfGiven:
                ev[col] = prefix + seq_fmt % (row)

    def fill_regions(self):
        """Use this function to re-assign region names."""
        if self.lookupIfEmpty or self.lookupIfGiven:
            for ev in self.ed.data:
                self._fill_region(ev)
        return

    def write(self, limit, fmt):
        """
        Inputs:
          limit - int, max number of events to output, or None
          fmt - string, output format required

        Returns:
          string

        """
        if fmt == 'raw':
            return self.rows

        elif fmt == 'text':
            # Like 'raw', but supports the 'limit' constraint.
            row_end = 0
            for i in range(limit + 1):  # Allow one more for header.
                row_end = self.rows.find('\n', row_end + 1)
            if row_end >= 0 and row_end < len(self.rows):
                logs.error("Truncated %i to %i (%i rows)" % (len(self.rows), row_end, limit))
                return self.rows[0:row_end]
            else:
                return self.rows

        elif fmt in ('csv', 'json', 'fdsnws-text'):
            ####REMOVE BEFORE CHCKreturn self.ed.write_all('csv', 14)
            return self.ed.write_all(fmt, limit)

        else:
            raise SyntaxError("In EventResponse.write: Unimplemented output format")


class EventService(object):
    """Class to query an event service.

    Sub-classing EventService helps you provide standard error
    responses to the web service by overloading the handler
    method.

    Using the EventData class here helps manage filtering and output.

    In case your underlying service raises an error, report this
    by calling raise_client_400() or similar. Otherwise return
    self.result_page().

    Usage:

    >> class esMine(EventService):
    >>   def handler(self, environ, start_response):
    >>     lines = "a|b|c\\nd|e|f\\nh|i|g"
    >>     return self.result_page(environ, start_response, '200 OK', 'text/plain', lines)

    Or:
    >>     try:
    >>         lines = [get some content]
    >>         return self.result_page(environ, start_response, '200 OK', 'text/plain', lines)
    >>     except:
    >>         self.raise_client_400('Houston, a problem')

    where 'lines' is a string containing '\n's for returning to the client.

    Then in getEvent you'd do:
    >> return esMine.handler(environ, start_response)

    """
    column_map = (5, 2, 3, 6, 7, 8, 0, 1)
    filter_table = (date_T, floatordash, None, float, float, floatordash, None, None)
    csv_dialect = csv.excel

    _EventsErrorTemplate = WI_Module(None)._EventsErrorTemplate

    def __init__(self, name, options, service_url='', extra_params=''):
        self.id = name
        self.service_url = service_url
        self.extra_params = extra_params
        self.options = options
        self.defaultLimit = options['defaultLimit']

    def _bounding_rect(self, p_lat, p_lon, max_radius):
        """Estimate a suitable area-rectangle for an area-circle request.

        UNDER DEVELOPMENT.  :FIXME:

        Inputs:
            p_lat, p_lon - float, coordinates of central point P(lat, lon)
            max_radius - float

        Translate these into a rectangular lat-lon region
        garanteed to include the entire region around P having
        r<max_radius.

        The estimate used below for d_lon is sufficient, but
        cruder than necessary. The lat/lon box could also be
        refined based on max/min_azimuth in future.

        """
        logs.debug("bounding: P(%g, %g), max_radius=%g:" % (p_lat, p_lon, max_radius))

        arg = abs(p_lat) + max_radius
        assert(arg > 0)
        if (arg >= 90.0):
            # Region bangs into the north or south pole so all longitudes
            max_lon = None
            min_lon = None
            if p_lat >= 0:
                logs.debug("bounding:   ...North pole is in the region")
                max_lat = None
                min_lat = p_lat - max_radius
            else:
                logs.debug("bounding:   ...South pole is in the region")
                min_lat = None
                max_lat = p_lat + max_radius
            if max_lat > 90.0:
                max_lat = None
            if min_lat < -90.0:
                min_lat = None

        else:
            d_lon = min(180.0, max_radius / math.cos(arg * math.pi / 180.0))
            # Division by zero for arg = +/- 90.
            # In this case the circle *touches* a pole.

            max_lat = min(90.0, p_lat + max_radius)
            min_lat = max(-90.0, p_lat - max_radius)
            if d_lon < 180.0:
                max_lon = p_lon + d_lon
                min_lon = p_lon - d_lon
                if max_lon > 180.0:
                    max_lon = max_lon - 360.0
                if min_lon < -180.0:
                    min_lon = min_lon + 360.0
            else:
                max_lon = None
                min_lon = None

        logs.debug("bounding:    %s > lat > %s; %s > lon > %s" % (max_lat, min_lat,
                                                                  max_lon, min_lon))
        return max_lat, min_lat, max_lon, min_lon

    def handler(self, environ, start_response):
        """Overload this method to implement a service."""
        return self.result_page(environ, start_response, '404 Not Found', 'text/plain', "Service '%s' is not implemented." % self.id)

    def send_request(self, pairs):
        """Connect to the target service.

        Prepares the URL from the EventService properties and param=value pairs.

        Inputs:
           pairs - list of 'param=value' strings

        Uses:
           self.service_url - string, the URL to request.
           self.extra_params

        Returns:
           rows - retrieved body from the URL, if any.
           url - string, the URL which was used.

        """
        pairs.append(self.extra_params)
        url = self.service_url + '?' + '&'.join(pairs)
        logs.info("Service '%s' fetching URL: %s" % (self.id, url))
        #print >>sys.stderr, "Service '%s' fetching URL: %s" % (self.id, url)

        dryrun = False  # Not implemented yet.
        if dryrun:
            rows = ''
        else:
            try:
                ua = 'Python-urllib/%i.%i (webdc3)' % (sys.version_info[0:2])
                req = urllib.request.Request(url, headers={'User-Agent': ua})
                response = urllib.request.urlopen(req)
                rows = response.read()
            except urllib.error.URLError as e:
                logs.error("Errors fetching from URL: %s" % (url))
                logs.error(str(e))
                raise   # urllib2.URLError(e)
                #return self.error_page(environ, start_response,
                #                       '503 Temporarily Unavailable',
                #                       "No answer")

            # TEMP FOR DEBUGGING - RACE/PERMISSION problems
            if (verbosity > 5):
                fid = open(os.path.join(tempdir, 'latest_response.dat'), 'w')
                print(rows, file=fid)
                fid.close()
        rows = rows.decode() #want str RCP
        return rows, url

    def format_response(self, rows, limit, fmt='json-row'):
        """Load the data into a clean structure.

        Inputs:
          rows - string containing the data, lines separated by '\n'
          limit - integer, maximum number of events to produce
          fmt - string, *output* format, one of [ 'raw', 'csv', 'text',
              'fdsnws-text',
              'json' 'json-row-major', 'json-col-major',
              'quakeml' (in future), ... ]

        Uses class members:
          csv_dialect - for processing the *input* CSV data
          column_map - tuple, column mapping, see ???. Selects columns from the rows.

        Output:
          An EventResponse object holding all the events in a standard format.

        """
        logs.debug("In EventService.format_response: fmt=%s limit=%s" % (str(fmt), str(limit)))
        if fmt == 'json-row':
            fmt = 'json'

        er = EventResponse(self.csv_dialect, self.column_map, self.filter_table, self.options)

        if fmt in ('csv', 'json', 'fdsnws-text'):
            er.load_csv(rows, limit, self.csv_dialect)
            er.fill_regions()
        else:
            er.load_plain(rows)
        return er

    def filter_response(self, er):
        # How do we get service-dependent args? This must be a handle??
        """Sub-classable event filter. By default, pass everything."""
        for ev in er.ed.data:
            # Magnitude:
            #if ev[1] < 5.0:
            #    print "Too small", ev[1]
            #    er.ed.data.remove(ev)
            break
        return er

    def write_response(self, er, limit, fmt):
        """Prepare the output in the desired format.

        Output: string, depends on the value of 'fmt'.
          'raw'  - just what was received from the target service
          'text' - the same, but limited to 'limit' events?
          'csv'  - see EventWriterCSV
          'fdsnws-text' - CSV as for fdsnws-event
          'json' - see EventWriterJSON: JSON table analogous to CSV

        """
        if fmt == 'json-row':
            fmt = 'json'
        if fmt in ('raw', 'text', 'csv', 'fdsnws-text', 'json'):
            return er.write(limit, fmt)
        else:
            raise SyntaxError("In EventService.write_response: Unimplemented output format")

    def send_response(self, environ, start_response, header, allrows, limit, fmt):
        """Have some raw data. Try to format it, and send an appropriate response.

        The only likely exception is due to an unsupported format choice.
        Different services may support different output formats.

        """
        try:
            limit = int(limit)
        except ValueError:
            limit = self.defaultLimit

        try:
            er = self.format_response(allrows, limit, fmt)
            er = self.filter_response(er)  # Now should er be a member of es?? :FIXME:
            content = self.write_response(er, limit, fmt)
            return self.result_page(environ, start_response, '200 OK', 'text/plain', header + content)
        except SyntaxError as e:
            self.raise_client_400(environ, str(e))

    def error_body(self, environ, response_code, message='Unspecified'):
        """Standardised error response.

        See the FDSN web service specification at
        <http://www.fdsn.org/webservices/FDSN-WS-Specifications-1.0.pdf>

        """
        return self._EventsErrorTemplate % {'err_code': response_code.split()[0],
                                            'err_desc': response_code.split(None, 1)[1],
                                            'service': self.id,
                                            'details': str(message),
                                            'url': _urlString(environ),
                                            'date_time': str(datetime.datetime.utcnow()),
                                            'version': WI_Module(None)._EventsVersion}

    def raise_client_error(self, environ, response_code, message='Unspecified'):
        """Use this for error pages to be delivered to the client.

        For this to work, the WSGI application() must catch the error,
        and handle it by serving the body content back to the client.

        """
        msg = self.error_body(environ, response_code, message)
        raise wsgicomm.WIError(response_code, msg)

    def raise_client_204(self, environ, message):
        """RFC 2616 <http://tools.ietf.org/html/rfc2616> says no message body is allowed.  :("""
        response_code = "204 No Content"
        raise wsgicomm.WIContentError(self.error_body(environ, response_code, message))

    def raise_client_400(self, environ, message):
        response_code = "400 Bad Request"
        raise wsgicomm.WIClientError(self.error_body(environ, response_code, message))

#    def error_page(self, environ, start_response, response_code, message = "Unspecified"):
#        """Shouldn't be needed with the new WIError mechanism."""
#        content = self.error_body(environ, response_code, message)
#        return self.result_page(environ, start_response, response_code, 'text/plain', content)

    def result_page(self, environ, start_response, response_code, content_type, data):
        """Return a web page for a successful request."""
        #### start_response(response_code, [('Content-Type', content_type)])
        return [data]

# ------------------------------------------------------

class ESFile(EventService):

    def check_cols(self, columns):
        """Parse and check user input from 'columns=...' constraint.

        Input:
          columns - list of words found in the QUERY_STRING argument
        Returns:
          List of valid column identifiers
        Raises:
          ValueError with a message if there's any problem.
          FIXME: Raise WIClientError instead?

        >>> opts = {'defaultLimit': 10}
        >>> ESFile('', opts).check_cols(['ignore', 'Latitude', 'Longitude', 'IGNORE', 'depth', 'tImE'])
        ['ignore', 'latitude', 'longitude', 'ignore', 'depth', 'time']

        """
        valid_names = ('latitude', 'longitude', 'depth', 'time', 'ignore')
        new_columns = []
        for word in columns:
            name = str(word).lower()
            # TODO: Support short names by looking for an approximate match here.
            # e.g. accept "lat" for "latitude", "dep" for "depth", but not
            # "l" (is it latitude or longitude?)
            if name in valid_names:
                new_columns.append(name)
            else:
                raise ValueError("Improper name in the 'columns' specifier; use only %s" % str(valid_names))
        if new_columns.count('latitude') != 1:
            raise ValueError("Exactly one 'latitude' is required in the 'columns' specifier")
        if new_columns.count('longitude') != 1:
            raise ValueError("Exactly one 'longitude' is required in the 'columns' specifier")
        if new_columns.count('time') != 1:
            raise ValueError("Exactly one 'time' is required in the 'columns' specifier")
        if new_columns.count('depth') > 1:
            raise ValueError("Only one 'depth' is allowed in the 'columns' specifier")
        return new_columns

    def check_event(self, columns, row):
        """Plausibility check for event parameters.

        Mostly in dealing with a target service we can waive
        responsibility for parameters to it: we are just wrapping
        their service. But when allowing user input, we are
        responsible for validating the input and sanity checks of
        the values.

        This function should be called after splitting up CSV rows
        / parsing JSON / parsing QuakeML to ensure the values are
        safe to insert into an EventData structure.

        Constraints:
         * date-time string must be convertible
         * latitude is numeric, in the range [-90, 90]
         * longitude is numeric, convert to range [-180, 180]
         * depth is numeric, or empty (in this case, set to 0)

        These will invalidate, i.e. reject, some obvious wrong rows:
         * rows with strings in numeric columns
         * far east/far west events with lat-lon reversed (where |lon| > 90)

        Input:
          columns - valid list of column identifiers
          row - list, with entries corresponding to 'columns' above.

        Returns:
          result - cleaned-up row, safe to insert or else None

        """
        def valid_latitude(val):
            if isinstance(val, str):
                words = val.split()
                try:
                    result = float(words[0])
                except ValueError:
                    return False, None
                if len(words) == 1:
                    return (abs(result) <= 90.0), result
                elif len(words) == 2:
                    return (0 <= result) and (result <= 90.0) and words[1][0].upper() in ['N', 'S'], result
                else:
                    return False, None
            else:
                try:
                    result = float(val)
                except ValueError:
                    return False, None
                return (abs(result) <= 90.0), result

        def valid_longitude(val):
            if isinstance(val, str):
                words = val.split()
                try:
                    result = float(words[0])
                except ValueError:
                    return False, None
                if len(words) == 1:
                    if (abs(result) > 180.0):
                        result = result % 360.0
                        if result > 180.0:
                            result = result - 360.0
                    return True, result
                elif len(words == 2):
                    return (0 <= result) and (result <= 180.0) and words[1][0].upper() in ['E', 'W'], result
                else:
                    return False, None
            else:
                try:
                    result = float(val)
                except ValueError:
                    return False, None
                if (abs(result) > 180.0):
                    result = result % 360.0
                    if result > 180.0:
                        result = result - 360.0
                return True, result

        def valid_depth(val):
            if not val:
                return True, 0.0
            try:
                result = float(val)
                return True, result
            except ValueError:
                return False, None

        def valid_datetime(val):
            """Only a few formats are allowed today. We should be more
            lenient in future."""

            allowedFmts = ('%Y-%m-%d %H:%M:%S',
                           '%Y-%m-%dT%H:%M:%S',
                           )

            if not isinstance(val, str):
                return False, None

            # FIXME: This repeats code in date_T() - remove trailing Z, +00:00 and .nnnn
            val = val.strip()
            val = val.rstrip('Z')
            #val = date_T(val)
            if val.endswith("+00:00"):
                val = val[0:-len("+00:00")]
            dot = val.rfind(".")
            if dot > -1:
                val = val[0:dot]

            for fmt in allowedFmts:
                try:
                    dt = datetime.datetime.strptime(val, fmt)
                    return True, dt.isoformat()
                except ValueError:
                    continue  # Try the next format

            return False, 'invalid datetime'

        assert len(columns) <= len(row), 'row is too short - wasn\'t this checked already?'

        for i in range(len(columns)):
            what = columns[i]
            value = row[i]
            if what == 'latitude':
                result, row[i] = valid_latitude(value)
                if not result: break
            elif what == 'longitude':
                result, row[i] = valid_longitude(value)
                if not result: break
            elif what == 'depth':
                result, row[i] = valid_depth(value)
                if not result: break
            elif what == 'time':
                result, row[i] = valid_datetime(value)
                if not result: break
            elif what == 'ignore':
                pass
            else:
                raise ValueError('Improper column spec - can\'t check the row')
        if result:
            return row
        else:
            logs.debug('Failed %s: %s' % (what, value))
            return None

    def column_map(self, columns):
        """Prepare column_map for later.

        Given a list of valid column identifiers (see check_cols)

        Returns: The map for selection from input rows to what is
        required for storage in EventData.

        Note: 'None' will mean the field will be empty in EventData.

        >>> opts = {'defaultLimit': 10}
        >>> ESFile('', opts).column_map(['latitude', 'longitude', 'time', 'ignore', 'depth'])
        (2, None, None, 0, 1, 4, None, None)

        """
        cols = 8 * [None]
        d = {'latitude': 3,
             'longitude': 4,
             'depth': 5,
             'time': 0}
        for k, v in list(d.items()):
            try:
                i = columns.index(k)
                cols[v] = i
            except ValueError:
                pass
        return tuple(cols)

    def handler(self, environ, parameters):

        # Process parameters:
        for k in ('columns', 'input'):
            if k not in parameters:
                self.raise_client_400(environ, "Required parameter '%s' was not specified" % (k))
        input_fmt = parameters.get('informat', ['csv'])[0]
        output_fmt = parameters.get('format', ['json'])[0]

        if input_fmt != 'csv':
            self.raise_client_400(environ, 'Input format can only be \'csv\' today')
            logs.warning('ESFile: Input format was "%s"' % input_fmt)

        infile = str(parameters['input'][0])  ### Is that right??
        lines = infile.splitlines()
        logs.info('ESFile::handler: input has %i line(s)' % len(lines))
        thing = str(parameters['columns'][0])
        columns = thing.split(',')
        logs.info('ESFile::handler: columns are %s' % str(columns))

        # Form columns, then attempt to parse the file

        min_columns = 3  # latitude, longitude, time - but this should be count(value != 'ignore')
        try:
            columns = self.check_cols(columns)
        except ValueError as e:
            self.raise_client_400(environ, str(e))

        logs.debug("ESFile::handler: Input file '%s'" % (infile))
        logs.debug("ESFile::handler: Columns: [%s] (%i)" % ("|".join(columns), len(columns)))

##        if not os.path.exists(infile):
##            self.raise_client_error(environ, '500 Internal Server Error', 'No such file')

        # FIXME: Writing to a temp file again! Perhaps put it in an EventResponse.rows??
        infile = os.path.join(tempdir, 'user_input_csv.txt')
        logs.debug('ESFile::handler: Writing to %s' % (infile))
        with open(infile, 'w') as fid:
            for t in lines:
                print(t, file=fid)

        ed = EventData()
        helper = Helpers()
        mapping = self.column_map(columns)  # Will come from 'columns' parameter of the request. Use (4, 2, 5, 6, 7, 0, 1) for eqinfo
        limit = self.defaultLimit           # Only read (and write) this many events.

        logs.debug('ESFile::handler: Mapping = %s' % (str(mapping)))
        logs.debug('ESFile::handler: Reading back from %s' % (infile))
        e = ''

        # Count number of imported events
        count = 0
        with open(infile, 'rt') as csvfd: #change from rb to rt (RCP) (unsure if needed)
            try:
                dialect = csv.Sniffer().sniff(csvfd.read(1024))
                logs.info("ESFile::handler: Sniffing file found dialect: %s" % repr_dialect(dialect))
            except:
                logs.notice("ESFile::handler: Sniffing file failed: %s" % (str(e)))
                self.raise_client_400(environ, "Failed to detect a readable CSV file.")
            csvfd.seek(0)

            er = EventResponse(dialect, mapping, self.filter_table, self.options)
            # Why can't we just use er.load_csv() here now?
            # It would rewrite and read from a different temp file, re-sniff...

            reader = csv.reader(csvfd, dialect)

            # Is there a header? Heuristic: if there's any item
            # starting with a digit [0-9] or '+' or '-' in this
            # row, it's probably not a header!
            header = next(reader)
            is_header = True
            for word in header:
                if re.match('^[0-9+-]', word):
                    is_header = False
            if not is_header:
                csvfd.seek(0)
                reader = csv.reader(csvfd, dialect)

            for row in reader:
                logs.debug("Row %i: %i item(s), content: %s" % (count, len(row), str(row)))

                row = row.decode() #to str (RCP) (unsure if needed)

                if len(row) < min_columns:
                    # Skip rows which don't have enough data, with NO WARNING.
                    # Extra items on the row are ignored.
                    continue

                # This can arise from dopey user input?:
                if not (len(row) >= len(columns)):
                    self.raise_client_400(environ, "Input row %i seems too short: %i < %i" % (count, len(row), len(columns)))

                ##if len(row) >= len(mapping):
                if len(row) >= len(columns):
                    new_row = self.check_event(columns, row)
                    if not new_row:
                        # Silently skip this row
                        continue
                    new_row = helper.mapcols(new_row, mapping)
                    new_row = helper.filtercols(new_row, self.filter_table)
                    er.ed.append(new_row)
                    logs.info("New %i: %i item(s), content: %s" % (count, len(new_row), str(new_row)))
                    count += 1

                    if count > limit:
                        msg = "Too many items, limit is %i" % (limit)
                        self.raise_client_error(environ, '413 Request Entity Too Large', msg)

        os.unlink(infile)

        if count == 0:
            self.raise_client_204(environ, 'No rows were read')

        er.fill_regions()
        er.fill_keys('user' + str(int(datetime.datetime.now().strftime("%s")) % 1000))

        logs.debug('ESFile::handler: final data:\n' + str(er.ed.data))

        ###output_fmt = 'json'  # :FIXME: Currently this overrides users's input
        content = er.write(limit, output_fmt)
        if (content):
            return self.result_page(environ, start_response, '200 OK', 'text/plain', content)
        else:
            self.raise_client_204(environ, 'No file specified?')

# ------------------------------------------------------

def emsc_prevday(name, parameters):
    """
    >>> emsc_prevday('end', {'end': ['2012-02-29']})
    ['end_date=2012-02-28']

    """
    if name == 'end':
        outname = 'end_date'
    else:
        raise SyntaxError('name not supported')

    value = parameters[name][0]
    d = datetime.datetime.strptime(value, "%Y-%m-%d")
    nextday = d - datetime.timedelta(1, 0, 0)
    outvalue = str(nextday.date())
    return ['%s=%s' % (outname, outvalue)]

class ESEMSC(EventService):
    class my_dialect(csv.excel):
        delimiter = ';'
    csv_dialect = my_dialect
    column_map = (0, 6, 5, 1, 2, 3, 9, 7)  # column numbers are *after* merging cols 0 and 1

    def handler(self, environ, parameters):
        """The EMSC event service, retrieved from CSV.

        - interprets the end of end_date as the last time for
        which an event may be returned.

        """
        paramMap = defaultParamMap
        paramMap['start'] = 'start_date'
        paramMap['end'] = ('func', emsc_prevday)
        paramMap['maxmag'] = 'max_mag'
        paramMap['minmag'] = 'min_mag'
        paramMap['maxdepth'] = 'max_depth'
        paramMap['mindepth'] = 'min_depth'
        paramMap['maxlat'] = 'max_lat'
        paramMap['minlat'] = 'min_lat'
        paramMap['maxlon'] = 'max_long'
        paramMap['minlon'] = 'min_long'
        paramMap['limit'] = '-DROP'

        pairs, bad_list, hold_dict = process_parameters(paramMap, parameters)
        if verbosity > 3:
            logs.error("In ESEMSC::handler() Hold list: %s" % str(hold_dict))
        if len(bad_list) > 0:
            logs.notice('*** Bad keys were presented: %s' % str(bad_list))
            self.raise_client_400(environ, "Unimplemented constraint(s): " + ", ".join(bad_list))

        # Make the request
        try:
            allrows, url = self.send_request(pairs)
        except urllib.error.URLError as e:
            msg = "No answer from URL / %s" % (e)
            self.raise_client_error(environ, '503 Temporarily Unavailable', msg)

        limit = hold_dict.get('limit', self.defaultLimit)
        try:
            limit = int(limit)
        except ValueError:
            self.raise_client_400("Parameter 'limit' must be an integer")

        fmt = hold_dict.get('format', 'text')

        # EMSC provides time and date as separate columns in the CSV.
        ## If I had CSV already, I could do this:
        #for row in allrows:
        #    if len(row) > 1:
        #        row[1] = row[0] + 'T' + row[1];
        #        row.pop(0)

        # But at this stage 'allrows' is just a string.
        # So seek for \n, and replace only the first ';' after it with a 'T'.
        # This is probably grotesquely inefficient.
        #
        # (One alternative would be to re-write format_response to support merging cols.)
        #
        # Also, they don't have a limit option, so I chop here
        # before calling send_response.
        #
        rows = []
        for row in allrows.splitlines():  # Same separator as the lineterminator used in their CSV?
            rows.append("T".join(row.split(self.csv_dialect.delimiter, 1)))
            if (len(rows)) > 2 * limit:
                break
        allrows = "\n".join(rows)

        return self.send_response(environ, start_response, '', allrows, limit, fmt)

# ------------------------------------------------------

class ESMeteor(EventService):
    """An event service for testing, which always has the same event."""

    class meteor_dialect(csv.excel):
        delimiter = '|'
    csv_dialect = meteor_dialect

    def __init__(self, name, options):
        self.id = name
        self.options = options

    def handler(self, environ, parameters):

        columns = '''"Event ID";"F-E Region";Magnitude;MagType;Status;"Origin time";Latitude;Longitude;"Depth (km)";Flags'''.split(';')
        sep = '|'
        allrows = sep.join(columns) + "\n"
        allrows += (sep.join(['ev123abc', 'Chelyabinsk',
                              str(2.0), 'Mw', 'M',
                              '2013-04-01T00:00:00Z',
                              str(55.15), str(61.41), str(-5.0),
                              'xxl']) + "\n")
        fmt = str(parameters.get('format', ['raw'])[0])
        if verbosity > 2:
            logs.error("Meteor::handler(): fmt=%s map=%s" % (fmt, str(self.column_map)))
        return self.send_response(environ, start_response, '', allrows, 100, fmt)

# ------------------------------------------------------

# FIXME
# Why do I gotta do this? Just want to convert "2012-01-01" to seconds
# since the epoch, where the string is interpreted as UTC time "2012-01-01 00:00:00"
# Ref: <http://www.python.org/doc//current/library/datetime.html>
ZERO = datetime.timedelta(0)

class UTC(datetime.tzinfo):
    """A UTC class"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return ZERO

utc = UTC()

def millidate(name, parameters):
        """
        Convert input date (as UTC) to milliseconds since 1970.
        Returns item to be added to pairs.

        >>> millidate('start', {'start': ['1970-01-01']})
        ['minEventTime=0']

        >>> millidate('start', {'start': ['2012-01-01']})
        ['minEventTime=1325376000000']

        >>> millidate('end', {'end': ['2013-08-01']})
        ['maxEventTime=1375315200000']

        # date +%s -d "2013-08-01" -u
        1375315200
        # date +%s -d "2012-01-01" -u
        1325376000

        """
        if name == 'start':
            outname = 'minEventTime'
        elif name == 'end':
            outname = 'maxEventTime'
        else:
            raise SyntaxError('name not supported')

        value = parameters[name][0]
        if verbosity > 3:
            logs.debug("Converting '%s=%s' to..." % (name, value))

        try:
            #dt = datetime.datetime.strptime(value, "%Y-%m-%d")
            dt = datetime.datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=utc)
            seconds = datetime.datetime.strftime(dt, '%s')

        except ValueError:
            try:
                seconds = datetime.datetime.strftime(datetime.datetime(1980, 1, 1), "%s")
            except ValueError:
                # On Windows?, Python >= 2.7
                #seconds = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
                raise ValueError
        except ValueError:
            seconds = "1370000000"
        outvalue = str(1000 * (int(seconds) + 3600))  # FUDGE FIXME
        if verbosity > 3:
            logs.debug(" ...to '%s=%s'." % (outname, outvalue))

        return ['%s=%s' % (outname, outvalue)]

class ESComcat(EventService):
    """Quasi-replacement for the old NEIC service.

    See front end at <http://earthquake.usgs.gov/earthquakes/eqarchives/epic/results.php>

    Typical link:

    Base: http://comcat.cr.usgs.gov/earthquakes/feed/v0.1/search.php
    Query string:
    ?maxEventLatitude=45&minEventLatitude=-90&minEventLongitude=-90&maxEventLongitude=180&minEventTime=1372032000000&maxEventTime=1372723200000&minEventMagnitude=-1&maxEventMagnitude=10&minEventDepth=0&maxEventDepth=800&format=csv

    Can export CSV or GeoJSON (provide format = {csv | geojson})

    Dates are milliseconds since 1970.
    Columns are:
    "DATE_TIME LAT LON DEP MAG MT SC"

         - Note: no region names are given.

    Bails out after receiving 'limit' (default=500) events.

    """
    csv_dialect = csv.excel

    column_map = (0, 4, 5, 1, 2, 3, 11, None)  # Note: comcat gives no region.
    filter_table = (date_T, floatordash, None, float, float, floatordash, None, None)

    def handler(self, environ, parameters):
        """The Comcat service from USGS (Replacement for NEIC?)

        Uses an old format for start and end dates: milliseconds since 1970 (UTC).

        Doesn't offer the following:
          - constraints by circular region

        """
        paramMap = defaultParamMap
        paramMap['start'] = ('func', millidate)
        paramMap['end'] = ('func', millidate)
        paramMap['minmag'] = 'minEventMagnitude'
        paramMap['maxmag'] = 'maxEventMagnitude'
        paramMap['mindepth'] = 'minEventDepth'
        paramMap['maxdepth'] = 'maxEventDepth'
        paramMap['minlat'] = 'minEventLatitude'
        paramMap['maxlat'] = 'maxEventLatitude'
        paramMap['minlon'] = 'minEventLongitude'
        paramMap['maxlon'] = 'maxEventLongitude'
        paramMap['limit'] = 'limit'

        pairs, bad_list, hold_dict = process_parameters(paramMap, parameters)

        if len(bad_list) > 0:
            logs.notice('*** Bad keys were presented: %s' % str(bad_list))
            self.raise_client_400(environ, "Unimplemented constraint(s): " + ", ".join(bad_list))

        limit = hold_dict.get('limit', self.defaultLimit)
        try:
            limit = int(limit)
        except ValueError:
            logs.error("Error converting limit argument %s" % str(limit))
            limit = self.defaultLimit

        fmt = hold_dict.get('format', 'text')

        try:
            allrows, url = self.send_request(pairs)
        except urllib.error.URLError as e:
            msg = "No answer from URL / %s" % (e)
            self.raise_client_error(environ, '503 Temporarily Unavailable', msg)

        if fmt != 'raw':
            # UGLY HACK: Reverse lines (other than the header) to get
            # decreasing date order (newest events first)
            #
            #print "Allrows before:\n", allrows
            rows = allrows.splitlines()
            tmp = [rows[0]]
            tmp.extend(rows[-1:0:-1])
            allrows = '\n'.join(tmp)
            #print "Allrows  after:\n", allrows

        if fmt.startswith("json"):
            header = ""
        else:
            numrows = rows.count('\n')
            header = "# " + url + "\n"
            header += "# Lines: " + str(numrows) + '\n'

        return self.send_response(environ, start_response, header, allrows, limit, fmt)

        ##content = self.format_response(allrows, int(limit), fmt)
        ##return self.result_page(environ, start_response, '200 OK', 'text/plain', header + content)

# ------------------------------------------------------

class ESNeic(EventService):
    service_url = 'http://neic.usgs.gov/cgi-bin/epic/epic.cgi'
    extra_params = 'SEARCHMETHOD=1&FILEFORMAT=6&SEARCHRANGE=HH' + '&SUBMIT=Submit+Search'

    def date_helper(self, param, params):
        """Split a date param with ISO date string into day, month and year params.

        Returns a tuple of split parameters like this:

           (SYEAR=yyyy,  SMONTH=mm , SDAY=dd)

        """
        value = params[param]
        try:
            (y_str, m_str, d_str) = split(value, '-', 2)
            y = int(y_str)
            m = int(m_str)
            d = int(d_str)
        except Exception as e:
            logs.error("Oops, trouble converting a '%s' argument" % param)
        if param == 'start':
            pairs = (('SYEAR=%04i' % y),
                     ('SMONTH=%02i' % m),
                     ('SDAY=%02i' % d))
        elif param == 'end':
            pairs = (('EYEAR=%04i' % y),
                     ('EMONTH=%02i' % m),
                     ('EDAY=%02i' % d))

        else:
            raise SyntaxError

        return pairs

    def handler(self, environ, parameters):
        """The NEIC service.

        Uses an old format for start and end dates.

        Doesn't offer the following:
          constaints by region

        """
        paramMap = defaultParamMap
        paramMap['start'] = ('func', neic_date_helper)
        paramMap['end'] = ('func', neic_date_helper)
        paramMap['mindepth'] = 'NDEP1'
        paramMap['mindepth'] = 'NDEP2'
        paramMap['minmag'] = 'LMAG'
        paramMap['maxmag'] = 'UMAG'

        pairs, bad_list, hold_dict = process_parameters(paramMap, parameters)

        if len(bad_list) > 0:
            logs.notice('*** Bad keys were presented: %s' % str(bad_list))
            self.raise_client_400(environ, "Unimplemented constraint(s): " + ", ".join(bad_list))

        #url = self.service_url + '?' + self.extra_params + '&'.join(pairs)
        try:
            allrows, url = self.send_request(pairs)
        except urllib.error.URLError as e:
            msg = "No answer from URL / %s" % (e)
            self.raise_client_error(environ, '503 Temporarily Unavailable', msg)

        numrows = allrows.count('\n')
        header = "# " + url + "\n"
        header += "# Lines: " + str(numrows) + '\n'

        return self.result_page(environ, start_response, '200 OK', 'text/plain', header + allrows)

# ------------------------------------------------------

def geofon_prevday(name, parameters):
    """
    The day before this one - GEOFON will give until *its* end.

    >>> geofon_prevday('end', {'end': ['2000-01-01']})
    ['datemax=1999-12-31']

    >>> geofon_prevday('end', {'end': ['2013-03-01']})
    ['datemax=2013-02-28']

    """
    if name == 'end':
        outname = 'datemax'
    else:
        raise SyntaxError('name not supported')

    value = parameters[name][0]
    if verbosity > 3:
        logs.debug("Converting '%s=%s' to..." % (name, value))

    d = datetime.datetime.strptime(value, "%Y-%m-%d")

    nextday = d - datetime.timedelta(1, 0, 0)
    outvalue = str(nextday.date())
    return ['%s=%s' % (outname, outvalue)]

class ESGeofon(EventService):
    class geofon_dialect(csv.excel):
        delimiter = ';'
    #column_map = (5, 2, 3, 6, 7, 8, 0, 1)    # if we provide mag type in column 3
    column_map = (4, 2, None, 5, 6, 7, 0, 1)  # if not
    csv_dialect = geofon_dialect
    filter_table = (date_T, floatordash, None, float, float, floatordash, None, None)

    def _area_circle_check(self, environ, d):
        """Plausibility check of circle arguments.

        environ - needed so this function can raise errors. FIXME
        d - dictionary of user-supplied values, still unchecked.

        For area_circle requests:
        - both lat and lon are REQUIRED,
        - but the four parameters (max,min)(radius,azimuth) are all OPTIONAL.

        Returns a dictionary with keys like the FDSN names and valid values.
        """
        if not ('lat' in d and 'lon' in d):
            msg = "both 'lat' and 'lon' are required for area-circle geographic constaints"
            self.raise_client_400(environ, msg)

        circle_params = dict()
        try:
            circle_params['lat'] = float(d['lat'])
            circle_params['lon'] = float(d['lon'])
        except ValueError:
            self.raise_client_400(environ, "Parameters 'lat' and 'lon' must be floats")

        # TODO: Azimuth might be okay in the range -360 .. 360
        max_azimuth = d.get('maxazimuth', 360.0)
        min_azimuth = d.get('minazimuth', 0.0)
        try:
            max_azimuth = float(max_azimuth)
            min_azimuth = float(min_azimuth)
            if max_azimuth < 0 or max_azimuth > 360 or min_azimuth < 0 or min_azimuth > 360:
                raise ValueError
        except ValueError:
            self.raise_client_400(environ, "If present, parameters 'maxazimuth' and 'minazimuth' must be floats between 0.0 and 360.0")
        circle_params['maxaximuth'] = max_azimuth
        circle_params['minaximuth'] = min_azimuth

        max_radius = d.get('maxradius', 180.0)  # FDSN default
        min_radius = d.get('minradius', 0.0)    # FDSN default
        try:
            max_radius = float(max_radius)
            min_radius = float(min_radius)
            if max_radius < 0 or max_radius > 180 or min_radius < 0 or min_radius > 180:
                raise ValueError
        except ValueError:
            self.raise_client_400(environ, "If present, parameters 'maxradius' and 'minradius' must be floats between 0.0 and 180.0")
        if max_radius < min_radius:
            self.raise_client_400(environ, "Must have 'minradius' < 'maxradius' to find anything")
        circle_params['maxradius'] = max_radius
        circle_params['minradius'] = min_radius

        return circle_params

    def _trim_rows(self, circle_params, rows, limit):
        """It's a shame we need an EventData just to do this!"""
        class funny_dialect(csv.excel):           ### comma separated?
            delimiter = ';'

        er = EventResponse(funny_dialect, self.column_map, self.filter_table, self.options)
        er.load_csv(rows, limit, funny_dialect)   ### sniffing failed, but it shouldn't have been needed!
        logs.debug('trim_rows: Loaded %i row(s) from %i char(s)' % (len(er.ed), len(rows)))

        p_lat = circle_params['lat']
        p_lon = circle_params['lon']

        col = {'lat': 3, 'lon': 4}
        er_new = EventResponse(funny_dialect, self.column_map, self.filter_table, self.options)
        for ev in er.ed.data:
            lat = ev[col['lat']]
            lon = ev[col['lon']]
            d = Math.delazi(p_lat, p_lon, lat, lon)[0]
            # Offline?
            #d = Math().delazi(p_lat, p_lon, lat, lon)
            if d >= circle_params['minradius'] and d <= circle_params['maxradius']:
                er_new.ed.data.append(ev)
                print("DEBUG: appending", ev)

        print("DEBUG: writing", er_new.ed.data)
        rows = er_new.ed.write_all(fmt='csv', limit=limit)

        ## Yuck! And there's no header yet!!
        ## {convert er.ed back to string!}
        #row = ""
        #for ev in new_rows:
        #    line = '|'.join(ev)
        #    rows += line + '\n'

        return rows, rows.count('\n')

    def handler(self, environ, parameters):
        """The GFZ eqinfo service at GEOFON, retrieved from CSV.

        eqinfo offers these extensions of the FDSN standard:
            ? maxazimuth, minazimuth ?
            ? format={quakeml, text}?
        eqinfo doesn't offer the following:
            - area-circle features
        eqinfo deviates from the standard:
            - returns a header line instead of an HTTP 204 status code.
            - 'datemax=YYYY-MM-DD' returns events up to the END of this day.

        """
        d = dict()  # Holds any acceptable parameters not passed on

        paramMap = defaultParamMap
        paramMap['start'] = 'datemin'
        paramMap['end'] = ('func', geofon_prevday)
        paramMap['maxmag'] = 'magmax'
        paramMap['minmag'] = 'magmin'
        paramMap['maxdepth'] = 'depmax'
        paramMap['mindepth'] = 'depmin'
        paramMap['maxlat'] = 'latmax'
        paramMap['minlat'] = 'latmin'
        paramMap['maxlon'] = 'lonmax'
        paramMap['minlon'] = 'lonmin'
        paramMap['limit'] = 'nmax'

        # Parameters lat, lon, minradius, maxradius require
        # special treatment by the handler. They are NOT passed
        # along to the target service.
        good_keys = (
                     'lat', 'lon',
                     'minradius', 'maxradius',
                     'minazimuth', 'maxazimuth',
                     )
        for name in good_keys:
            if name in parameters:
                paramMap[name] = '-DROP'  # not '-UNIMPLEMENTED'
                d[name] = urllib.parse.quote(parameters[name][0])

        # Then build the parameter string for the underlying service:
        pairs, bad_list, hold_dict = process_parameters(paramMap, parameters)

        if len(bad_list) > 0:
            logs.notice('*** Bad keys were presented: %s' % str(bad_list))
            self.raise_client_400(environ, "Unimplemented constraint(s): " + ", ".join(bad_list))

        # Q: Is depth two-sized for eqinfo service (depthmin/depthmax)?


        # PLE: The FDSN spec specifies defaults for maxlat ..
        # minlon, but we don't apply them here. We rely on the
        # eqinfo service having the same defaults. This is risky,
        # but gives shorter URLs.

        area_rectangle = False
        for k in ('maxlat', 'minlat', 'maxlon', 'minlon'):
            area_rectangle = area_rectangle or k in parameters

        # The eqinfo service doesn't implement annular regions, so
        # we have to take care of it. We start by constraining to
        # a "square", based on maxradius, which will be trimmed
        # later.

        area_circle = False
        for k in ('lat', 'lon', 'maxazimuth', 'minazimuth', 'maxradius', 'minradius'):
            area_circle = area_circle or k in d

        # We refuse to accept any area_rectangle
        # (minlat, ... maxlon) constraints when in area_circle mode.
        # And similarly if in rectangle mode.

        if area_rectangle and area_circle:
            msg = "can't give both area-rectangle and area-circle geographic constraints"
            self.raise_client_400(environ, msg)

        if area_circle:
            circle_params = self._area_circle_check(environ, d)

            # FIXME: This logic is common to all services, but
            # here we are building up only the geofon eqinfo form!
            max_lat, min_lat, max_lon, min_lon = self._bounding_rect(circle_params['lat'], circle_params['lon'], circle_params['maxradius'])
            if not max_lat is None:
                pairs.append('%s=%g' % (paramMap['maxlat'], max_lat))
            if not max_lon is None:
                pairs.append('%s=%g' % (paramMap['minlat'], min_lat))
            if not max_lon is None:
                pairs.append('%s=%g' % (paramMap['maxlon'], max_lon))
            if not min_lon is None:
                pairs.append('%s=%g' % (paramMap['minlon'], min_lon))

        # Unimplemented keys for which we would rather stop here than attempt:

        # NOTE: While webinterface is the only user of this
        # service, there's no immediate need to handle these,
        # since it won't attempt these constraints. But if we open
        # the event service wider, we must be ready for these...
        #bad_keys = ['offset',
        #            'magtype',
        #            'magnitudetype',
        #            'includeallmagnitudes',
        #            'preferredonly',
        #            'orderby',
        #            'contributor',
        #            'updatedafter']

        # Unimplemented keys which we simply suppress:
        #drop_keys = ['catalog']

        # Keys which we can pass on without modification:
        #pass_keys = ['eventid']

        fmt = hold_dict.get('format', 'text')  # ???

        fmts_okay = ('raw', 'text', 'csv', 'fdsnws-text', 'json', 'json-row')
        if not fmt in fmts_okay:
            msg = "Supported output formats are %s" % (str(fmts_okay))
            self.raise_client_400(environ, msg)

        # TODO: Review this, can it get added twice??
        limit = hold_dict.get('limit', self.defaultLimit)  # FDSN default is 0!
        try:
            limit = int(limit)
        except ValueError:
            logs.error("Error converting limit argument %s" % (str(limit)))
            limit =  self.defaultLimit

        if limit > -1 and limit <= self.defaultLimit:
            pairs.append('nmax=%i' % (limit))

        try:
            allrows, url = self.send_request(pairs)
        except urllib.error.URLError as e:
            msg = "No answer from URL / %s" % (e)
            self.raise_client_error(environ, '503 Temporarily Unavailable', msg)

        # Heuristic to identify "no data" from eqinfo: ';' and one line break.
        numrows = allrows.count('\n')
        if numrows <= 1 and allrows.count(self.csv_dialect.delimiter) > 1:
            self.raise_client_204(environ, 'No events returned')

        # Now work on trimming away region outside the circle...
        # July 25: This APPROACH IS WRONG. DOn't try hacking raw text, have send_response accept a structure
        # which we can modify. Major change!
        #
##        if area_circle:
##            logs.info('Got %i row(s), starting to trim...' % (numrows))
##            #print '\n\n\nAllrows IN:'
##            #print allrows
##            #print '\n\n'
##
##            allrows, numrows = self._trim_rows(circle_params, allrows, numrows)
##            logs.info('Trimmed, now %i row(s)' % (numrows))
##
##            #print '\n\nAllrows OUT:'
##            #print allrows
##            #print '\n\n'

        if fmt.startswith("json") or fmt == "csv" or fmt == "fdsnws-text":
            header = ""
        else:
            header = "# " + url + "\n"
            header += "# Lines: " + str(numrows) + '\n'

        return self.send_response(environ, start_response, header, allrows, limit, fmt)

# --------------------------- INGV ES --------------------------------

class ESFdsnws(EventService):
    """An event service for FDSN fdsnws-event web service
    (e.g. running at INGV). This is based on its CSV output,
    so requires "format=text" on the query strings sent to
    the target web service.

    Initial version contributed by Valentino Laucani, Massimo
    Fares et al. at INGV. Many thanks!

    """

    class fdsnws_dialect(csv.excel):
        delimiter = '|'

    csv_dialect = fdsnws_dialect

    #
    #   column_map -> field meaning & position :
    #    'datetime'-0, 'magnitude'-1,
    #    'magtype' - 2,
    #    'latitude'-3, 'longitude'-4, 'depth'-5, 'key'-6, 'region'-7
    #
    column_map = (0, 1, 2, 3, 4, 5, 6, 7)

    #
    #    filter_table
    #
    filter_table = (date_T, floatordash, None, float, float, floatordash, None, None)

    def __init__(self, name, options, service_url, extra_params):
        self.name = name
        self.options = options
        self.id = name
        self.service_url = service_url
        self.extra_params = extra_params
        self.defaultLimit = options['defaultLimit']

    def handler(self, environ, parameters):
        paramMap = defaultParamMap
        paramMap['start'] = 'starttime'
        paramMap['end'] = 'endtime'
        paramMap['minlat'] = 'minlat'
        paramMap['maxlat'] = 'maxlat'
        paramMap['minlon'] = 'minlon'
        paramMap['maxlon'] = 'maxlon'
        paramMap['lat'] = 'lat'
        paramMap['lon'] = 'lon'
        paramMap['minradius'] = 'minradius'
        paramMap['maxradius'] = 'maxradius'
        paramMap['mindepth'] = 'mindepth'
        paramMap['maxdepth'] = 'maxdepth'
        paramMap['minmag'] = 'minmag'
        paramMap['maxmag'] = 'maxmag'
        paramMap['limit'] = 'limit'

        header = ''

        pairs, bad_list, hold_dict = process_parameters(paramMap, parameters)

        limit = hold_dict.get('limit', self.defaultLimit)
        try:
            limit = int(limit) + 1
        except ValueError:
            self.raise_client_400("Parameter 'limit' must be an integer")

        for k in range(len(pairs)):
            if pairs[k].startswith('limit'):
                del pairs[k]
        pairs.append("limit=%s" % (limit))

        # send a request
        try:
            allrows, url = self.send_request(pairs)
        except urllib.error.URLError as e:
            msg = "No answer from URL / %s" % (e)
            self.raise_client_error(environ, '503 Temporarily Unavailable', msg)

        # Heuristic to identify "no data" from INGV service
        numrows = allrows.count('\n')
        if numrows <= 1 and allrows.count(self.csv_dialect.delimiter) > 1:
            self.raise_client_204(environ, 'No events returned')

        # check response for "no data" returned
        check_string = "Error 413"
        if (check_string in allrows) or (len(allrows) < 5):
            self.raise_client_204(environ, 'No events returned')

        # PLE: I'm not sure whether we need to send the header row ourselves.
        myallrow = allrows.split("\n")
        #myallrow[0] = "#"+myallrow[0]

        my_row_for_send = 'EventID|Time|Latitude|Longitude|Depth/km|Author|Catalog|Contributor|ContributorID|MagType|Magnitude|MagAuthor|EventLocationName\n'

        # rebuild the resultset
        for item in myallrow:
            if(item):
                if(item[0] == '#'):
                    continue

                this_row = item.split("|")
                mytime = this_row[1].split(".")
                my_row_for_send += ""+mytime[0]+"|"+this_row[10]+"|"+this_row[9]+"|"+this_row[2]+"|"+this_row[3]+"|"+this_row[4]+"|\""+this_row[0]+"\"|\""+this_row[12]+"\"\n"  #schema: 1 | 10 | 9 | 2 | 3 | 4 | 0 | 12
                #CANDIDATE FIXME:
#                my_row_for_send  += '|'.join((mytime[0],
#                                              this_row[10], this_row[9],
#                                              this_row[2], this_row[3],
#                                              this_row[4],
#                                              '"' + this_row[0] + '"',
#                                              '"' + this_row[12] + '"\n'))
        fmt = str(parameters.get('format', ['text'])[0])

        return self.send_response(environ, start_response, header, my_row_for_send, limit, fmt)

# --------------------------------------------------------------------


def bodyBadRequest(environ, msg, service="[event]"):
    """A text/plain message in case of trouble before reaching getEvents().

    Input:
      environ - WSGI environment
      msg - string, description of what went wrong.
      service - string, what service called this, if known.
    Returns:
      string, page contents to be sent back to web client.

    """
    return WI_Module(None)._EventsErrorTemplate % {'err_code': "400",
                                    'err_desc': "Bad Request",
                                    'service': service,
                                    'details': msg,
                                    'url': _urlString(environ),
                                    'date_time': str(datetime.datetime.utcnow()),
                                    'version': WI_Module(None)._EventsVersion,
                                    }



# ----------------------------------------------------------------------
# Test suite for event services, and associated helper functions.

def gen_test_table(urlbase, fmt='html'):
    """Test table for event services.

    Returns: string

    This table of links can be used to test that the combined
    event service responds correctly to the entire matrix of
    one-parameter query strings for all implemented services.
    Include the HTML table in a web page, and follow all the links.

    If format='list' the set of URLs is printed and can be fed to
    e.g. 'wget' for automated testing.

    """
    def make_url(urlbase, service, paramName):
        value = "VALUE"
        if paramName in ("end", "start", "updatedafter"):
            value = "2013-06-01"
        if paramName.endswith("mag"):
            value = "5.5"
        if paramName.endswith("depth"):
            value = "5.0"
        if paramName.endswith("lon"):
            value = "135.0"
        if paramName.endswith("lat"):
            value = "-5.0"
        if paramName.endswith("radius"):
            value = "15.0"

        url = "%(base)s/event/%(service)s?%(name)s=%(value)s" % {"base": urlbase,
                                                               "service": service,
                                                               "name": paramName,
                                                               "value": value}
        return url

    def get_one():
        for row in defaultParamNames:
            for col in _EventServiceCatalog:
                url = make_url(urlbase, col, row)
                yield url

    if fmt == 'html':
        s = "<table>"
        s += tagged("tr", tagged("th", _EventServiceCatalog))
        for row in defaultParamNames:
            s += "<tr>"
            for col in _EventServiceCatalog:
                url = make_url(urlbase, col, row)
                s += tagged("td", tagged("a", row, {'href': url}))
            s += "</tr>"
        s += "</table>"

    elif fmt == "list":
        s = "# == Link Table for Event Service =="
        for link in get_one():
            s += link
    else:
        raise SyntaxError

    return s


def make_html_test_table(hostport, filename):
    fid = open(filename, 'w+')
    print(gen_test_table("http://" + hostport), file=fid)
    fid.close()


def start_response(arg1, arg2):
    verbose = True
    if verbose:
        print("Server Response:", arg1)
        print(arg2[0][0], ':', arg2[0][1])
        print()


# ----------------------------------------------------------------------
# Code beyond here is to have standalone event functionality for testing
# and debugging.

if __name__ == '__main__':

        doctest.testmod()

        #print "About me:"
        #print str(wi)

        port = 8005
        hostport = 'localhost:%i' % port
        print("Starting wsgiref on port %(p)i" % {'p': port})
        print("Now visit e.g. <%s/event/geofon?maxlat=-20>" % (hostport))
        print(" or <%s/event/catalogs>" % (hostport))
        print(" or <%s/event/meteor>" % (hostport))

        #make_html_test_table(hostport, "test_events.html")

        import wsgiref
        from wsgiref.simple_server import make_server
        #srv = make_server('localhost', port, application)
        #srv.serve_forever()
