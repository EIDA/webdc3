#!/usr/bin/env python
#
# Resources to communicate via a WSGI module
#
# Begun by Javier Quinteros, GEOFON team, June 2013
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------


"""Functions and resources to communicate via a WSGI module

(c) 2013 GEOFON, GFZ Potsdam

The list of functions in this module and the information it returns is:
- query: different network types (the name should change. See what returns.)

The internal functions are:
- __init_session: triple containing session-key, username and password.

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2, or (at your option) any later
version. For more information, see http://www.gnu.org/

"""


##################################################################
#
# Exceptions to be caught (usually) by the application handler
#
##################################################################


class PlsRedirect(Exception):
    """Exception to signal that the web client should be redirected to a new URL.
    
    The constructor of the class receives a string, which is the
    URL where the web browser is going to be redirected.
    
    Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013
    
    """

    def __init__(self, url):
        self.url = url
    def __str__(self):
        return repr(self.url)


class WIError(Exception):
    """Exception to signal that an error occurred while doing something, that the web client should see.

    Inputs:
      status     - string, like "200 Good", "400 Bad"
      body       - string, plain text content to display to the client
      verbosity  - integer, 0 = silent, 4 = debug

    """

    def __init__(self, status, body, verbosity = 1):
        self.status = status
        self.body = body
        self.verbosity = verbosity

    def __str__(self):
        return repr(self.status)+': '+repr(self.body)  # body but not verbosity(?)


class WIContentError(WIError):
    def __init__(self, *args, **kwargs):
        WIError.__init__(self, "204 No Content", *args, **kwargs)


class WIClientError(WIError):
    def __init__(self, *args, **kwargs):
        WIError.__init__(self, "400 Bad Request", *args, **kwargs)


class WIInternalError(WIError):
    def __init__(self, *args, **kwargs):
        WIError.__init__(self, "500 Internal Server Error", *args, **kwargs)


class WIServiceError(WIError):
    def __init__(self, *args, **kwargs):
        WIError.__init__(self, "503 Service Unavailable", *args, **kwargs)


##################################################################
#
# Functions to send a response to the client
#
##################################################################

def redirect_page(url, start_response):
    """Tells the web client through the WSGI module to redirect to an URL.
    
    Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013
    
    """

    response_headers = [('Location', url)]
    start_response('301 Moved Permanently', response_headers)
    return ''

def send_html_response(status, body, start_response):
    """Sends an HTML response in WSGI style.
    
    Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013
    
    """

    response_headers = [('Content-Type', 'text/html; charset=UTF-8'),
                   ('Content-Length', str(len(body)))]
    start_response(status, response_headers)
    return [ body ]

def send_plain_response(status, body, start_response):
    """Sends a plain response in WSGI style.
    
    Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2013
    
    """

    response_headers = [('Content-Type', 'text/plain'),
                   ('Content-Length', str(len(body)))]
    start_response(status, response_headers)
    return [ body ]

def send_file_response(status, body, start_response):
    """Sends a file or similar object.

    Caller must set the filename, size and content_type attributes of body.

    """
    response_headers = [('Content-Type', body.content_type),
                   ('Content-Length', str(body.size)),
                        ('Content-Disposition', 'attachment; filename=%s' % (body.filename))]
    start_response(status, response_headers)
    return body

