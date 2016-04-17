import os
import json

class WI_Module(object):
    def __init__(self, wi):
        self.js_conf = wi.getConfigJSON('js')
        wi.registerAction("/configuration", self.configuration)
        wi.registerAction("/loader", self.loaderjs)

        # We keep a copy of it
        self.__wi = wi

    def configuration(self, envir, params):
        """Read the configuration file and return the variables in JSON format.
        Input: nothing
        Output: All js.* variables of webinterface.cfg in JSON format
        Begun by Andres Heinloo <andres@gfz-potsdam.de>, GEOFON team, June 2013

        """
        return [ self.js_conf ]

    def loaderjs(self, envir, params):
        """It returns the Javascript code to load the loader.js file in the main page.
        Begun by Marcelo Bianchi <mbianchi@gfz-potsdam.de>, GEOFON team, June 2013

        """

        body = []

        # Create the variables that are returned in Javascript format based on the
        # information of the environment.
        serviceRoot = envir['SCRIPT_NAME']
        cssSource = os.path.dirname(serviceRoot) + '/css'
        jsSource = os.path.dirname(serviceRoot) + '/js'
        debug = (self.__wi.getConfigInt('DEBUG', 0) == 1)
        body.append("window.eidaServiceRoot=%s;" % json.dumps(serviceRoot))
        body.append("window.eidaCSSSource=%s;" % json.dumps(cssSource))
        body.append("window.eidaJSSource=%s;" % json.dumps(jsSource))
        body.append("window.eidaDebug=%s;" % json.dumps(debug))
        body.append("$('head').append($('<link>').attr({rel:'stylesheet',type:'text/css',href:%s}));" %
            json.dumps(cssSource + '/wimodule.css'))
        body.append("$.getScript(%s);" % json.dumps(jsSource + '/webdc3.min.js'))

        return body

