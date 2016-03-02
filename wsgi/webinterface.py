#!/usr/bin/env python
#
# Arclink web interface
#
# Begun by Javier Quinteros, GEOFON team, June 2013
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------


"""ArcLink web interface

Copyright (c) 2013-2015 GEOFON, Helmholtz-Zentrum Potsdam - Deutsches GeoForschungsZentrum GFZ

Exports the functions needed by the JavaScript running in the
web browser. All the functions must be called via an URL with the
following format:
http://SERVER/path/to/function?query

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 3, or (at your option) any later
version. For more information, see http://www.gnu.org/

"""

import os
import glob
import imp
import cgi
import sys

# JSON (since Python 2.6)
import json

# SC3 stuff
import seiscomp3.System
import seiscomp3.Config
import seiscomp3.Logging

from seiscomp import logs
from wsgicomm import *
from inventorycache import InventoryCache

# Verbosity level a la SeisComP logging.level: 1=ERROR, ... 4=DEBUG
# (global parameters, settable in wsgi file)
verbosity = 3
syslog_facility = 'local0'

# Maximum size of POST data, in bytes? Or roubles?
cgi.maxlen = 1000000

##################################################################

class WebInterface(object):
    def __init__(self, appName):
        # initialize SC3 environment
        env = seiscomp3.System.Environment_Instance()

        # set up logging
        self.__syslog = seiscomp3.Logging.SyslogOutput()
        self.__syslog.open(appName, syslog_facility)

        for (v, c) in ((1, "error"), (2, "warning"), (2, "notice"), (3, "info"), (4, "debug")):
            if verbosity >= v:
                self.__syslog.subscribe(seiscomp3.Logging.getGlobalChannel(c))

        logs.debug = seiscomp3.Logging.debug
        logs.info = seiscomp3.Logging.info
        logs.notice = seiscomp3.Logging.notice
        logs.warning = seiscomp3.Logging.warning
        logs.error = seiscomp3.Logging.error

        logs.notice("Starting webinterface")

        # load SC3 config files from all standard locations (SEISCOMP_ROOT must be set)
        self.__cfg = seiscomp3.Config.Config()
        env.initConfig(self.__cfg, appName, env.CS_FIRST, env.CS_LAST, True)

        self.__action_table = {}
        self.__modules = {}

        # Common config variables
        self.server_folder = self.getConfigString('SERVER_FOLDER', None)

        if not self.server_folder:
            err="%s: Cannot find server root, configuration not loaded" % (appName)
            raise Exception(err)

        if not os.path.exists(self.server_folder):
            err="%s: Server root directory not found" % (appName)
            raise Exception(err)

        # Add inventory cache here, to be accessible to all modules
        inventory = os.path.join(self.server_folder, 'data', 'Arclink-inventory.xml')
        self.ic = InventoryCache(inventory)

        # Load all modules in given directory.
        # Modules must contain a class WI_Module, whose __init__() takes
        # WebInterface object (our self) as an argument and calls our
        # addAction().

        #for f in glob.glob(os.path.join(env.shareDir(), "plugins", "webinterface", "*.py")):
        for f in glob.glob(os.path.join(self.server_folder, "wsgi", "modules", "*.py")):
            self.__load_module(f)

        logs.debug(str(self))

    def __repr__(self):
        """Dump important information about me, including what URLs I handle."""

        s = ''

        s += 'Server directory: ' + str(self.server_folder)
        s += '\n\n'

        s += 'Modules:\n'
        s += str(sorted(self.__modules))
        s += '\n\n'

        s += 'Registered URLs:\n'
        for a in sorted(self.__action_table):
            s += a + ': ' + str(self.__action_table[a]) + '\n'
        return s

    def __load_module(self, path):
        modname = os.path.splitext(os.path.basename(path))[0].replace('.', '_')

        if modname in self.__modules:
            logs.error("'%s' is already loaded!" % modname)
            return

        try:
            mod = imp.load_source('__wi_' + modname, path)

        except:
            logs.error("Error loading '%s'" % modname)
            logs.print_exc()
            return

        self.__modules[modname] = mod.WI_Module(self)

    def registerAction(self, name, func, *multipar):
        self.__action_table[name] = (func, set(multipar))

    def getAction(self, name):
        return self.__action_table.get(name)

    def getConfigBool(self, name, default):
        try:
            return self.__cfg.getBool(name)
        except Exception, e:
            return default

    def getConfigTree(self, prefix=''):
        """Helper function to construct a structure for config."""
        def _add_pv(d, p, v):
            if len(p) == 1: # no dots in parameter name
                if len(v) == 1: # value is a single item (not a list)
                    d[p[0]] = v[0]

                else:
                    d[p[0]] = v

            else:
                try:
                    d1 = d[p[0]]

                except KeyError:
                    d1 = dict()
                    d[p[0]] = d1

                _add_pv(d1, p[1:], v)

        d = {}
        for name in self.__cfg.names(): # iterate over parameter names
            p = name.split('.')
            px = prefix.split('.')
            if not px[0] or p[0:len(px)] == px:
                _add_pv(d, p[len(px):], list(self.__cfg.getStrings(name)))

        return d

    def getConfigJSON(self, prefix=''):
        return json.dumps(self.getConfigTree(prefix))

    def getConfigString(self, name, default = None):
        try:
            return str(self.__cfg.getString(name))

        #except seiscomp3.Config.OptionNotFoundException:
        except Exception, e:
            return default

    def getConfigList(self, name, default = None):
        try:
            return list(self.__cfg.getStrings(name))

        #except seiscomp3.Config.OptionNotFoundException:
        except Exception, e:
            return default

    def getConfigInt(self, name, default = None):
        try:
            return int(self.__cfg.getString(name))

        except ValueError:
            logs.error("config parameter '%s' has invalid value" % name)
            return default

        #except seiscomp3.Config.OptionNotFoundException:
        except Exception, e:
            return default

    def getConfigFloat(self, name, default = None):
        try:
            return float(self.__cfg.getString(name))

        except ValueError:
            logs.error("config parameter '%s' has invalid value" % name)
            return default

        #except seiscomp3.Config.OptionNotFoundException:
        except Exception, e:
            return default


##################################################################
#
# Initialization of variables used inside the module
#
##################################################################

wi = WebInterface(__name__)


def application(environ, start_response):
    """Main WSGI handler that processes client requests and calls
    the proper functions.

    Begun by Javier Quinteros <javier@gfz-potsdam.de>,
    GEOFON team, June 2013

    """

    # Read the URI and save the first word in fname
    #fname = environ['PATH_INFO'].split("/")[-1]
    #fname = environ['PATH_INFO'].lstrip('/').split("/")[0]
    # print "environ['PATH_INFO'].lstrip('/')", environ['PATH_INFO'].lstrip('/')

    fname = environ['PATH_INFO']

    if not len(fname):
       fname = 'default'

    logs.debug('fname: %s' % (fname))

    item = wi.getAction(fname)
    logs.debug('item: %s' % (str(item)))

    # Among others, this will filter wrong function names,
    # but also the favicon.ico request, for instance.
    if item is None:
       status = '404 Not Found'
       return send_html_response(status, 'Error! ' + status, start_response)

    (action, multipar) = item
    parameters = {}

    try:
        form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)

    except ValueError, e:
        if str(e) == "Maximum content length exceeded":
            # Add some user-friendliness (this message triggers an alert box on the client)
            return send_plain_response("400 Bad Request", "maximum request size exceeded", start_response)

        return send_plain_response("400 Bad Request", str(e), start_response)

    if form:
        for k in form.keys():
            if k in multipar:
                parameters[k] = form.getlist(k)

            else:
                parameters[k] = form.getfirst(k)

    logs.debug('parameters: %s' % (parameters))

    body = []

    # body.extend(["%s: %s" % (key, value)
    #     for key, value in environ.iteritems()])

    # status = '200 OK'
    # return send_plain_response(status, body, start_response)

    logs.debug('Calling %s' % action)

    try:
        res_string = action(environ, parameters)

    except PlsRedirect as redir:
        return redirect_page(redir.url, start_response)

    except WIError as error:
        error_page = error.body
        logs.notice('Error page %s: "%s"' % (error.status, error_page))
        if error.verbosity > 1:
            extra = 'VERBOSE verbose=%i' % error.verbosity
            error_page += '\n' + extra
        return send_plain_response(error.status, error_page, start_response)

    if isinstance(res_string, basestring):
        status = '200 OK'
        body = res_string
        return send_plain_response(status, body, start_response)

    elif hasattr(res_string, 'filename'):
        status = '200 OK'
        body = res_string
        return send_file_response(status, body, start_response)

    status = '200 OK'
    body = "\n".join(res_string)
    return send_plain_response(status, body, start_response)

