
.. _developer-guide:

*****************
Developer Notes
*****************

Principles
==========

We use JavaScript-based Dynamic HTML, together with the Python Web Server Gateway Interface (WSGI; :PEP:`333`) for thin web services.
Our approach is based on "dynamic HTML", in which JavaScript is used to modify
objects in the Document Object Model (DOM) of the page displayed in the
browser.

There is a modular decomposition into functions related to presentation, events, services, maps, configuration, and data requests from the Arclink server.

* Coding

  We try to comply with :PEP:`8` `Style Guide for Python Code`
  and :PEP:`257` `Docstring Conventions`, and use the Python
  unittest unit testing framework where convenient.

  For JavaScript... anything goes? There is a helper class to control access
  to the Python modules.


* Documentation

  This documentation is written in
  reStructuredText <http://docutils.sourceforge.net/rst.html> (reST, a common simple mark-up format). The final documentation is generated using Sphinx.
  Our philosophy follows the SeisComP documentation, described at
  http://www.seiscomp3.org/doc/seattle/2013.149/base/contributing-docs.html .
  Look in the `descriptions` subdirectory for configuration options
  etc. relating to particular modules e.g., `wsgi/descriptions`.

Interfaces and name spaces
==========================

The communication between JavaScript and Python uses HTTP over a web services-like
interface. The Python-based web services can run on any port on localhost
(not on a different server, due to browser/JavaScript restrictions against
cross-site scripting (XSS) attacks.)

The URL specification for services is divided into major subgroups. They are::

 <wsgi root>/         ## Interface information service / Page generation
 <wsgi root>/event    ## Event-related stuff
 <wsgi root>/metadata ## Metadata-related stuff
 <wsgi root>/request  ## Request submission and status stuff

The real services offered by the server are accommodated into one of these subgroups.

.. include:: specs/interface-server-client.txt

Modules
=======

1. :ref:`dev-presentation-module`

2. :ref:`dev-event-module`

3. :ref:`dev-metadata-module`

4. :ref:`dev-mapping-module`

5. :ref:`dev-requests-module`

6. :ref:`dev-configuration-module`

.. _dev-presentation-module:

Presentation module
~~~~~~~~~~~~~~~~~~~

There is a 'debug' option for the JavaScript.

Styles for objects within the control divs is provided in `wimodule.css`.
These are prefixed with "wi-".
Generally they do not alter colours or fonts - those should be controlled by a
"theme"-specific style sheet included by the top-level page (e.g. index.html
includes css/basic.css).

Some things ``are`` set in the JavaScript
e.g. monospace font for pull-down menus.

In particular lots of alignment decisions - padding, margins, text alignment
are made in the JavaScript - but they should not require modification.

.. _dev-event-module:

Events module
~~~~~~~~~~~~~

Each target event service requires a URL at which we can obtain CSV output.
 
One difficult choice concerns interpretation of end dates and the time
(instant) that they refer to.

Several existing catalogs understand an end date as the last day on which an
event should be returned - GEOFON's `datemax` and EMSC's `end_date` parameters
are like this.
Others specify a time, e.g. ComCat requires milliseconds since 1970.
A box giving start and end dates on a web interface needs to convert its end date to the last acceptable time, or the *end* of the end date.
For events in June 2013, users should enter 2013-06-30 in an "ending date"
box, but this means that the end parameter value required is
``2013-07-01T00:00:00``.
Following the FDSN web services specification, this date-time may be
abbreviated to `end=2013-07-01` i.e. the *start of the next day*.

  .. note::
     A query to a FDSN-style web service with ``start=2001-01-01&end=2001-01-02`` is used to obtain only events occurring on 1 January 2001.

We were faced with two unpalatable choices:

 * Allow `end=YYYY-MM-01` to mean the end of the first day of a month.
   Then it could be passed through to those target services which cut off at the end of the given date.
   However the Python web service we built to wrap multiple event services would be flawed in that it did not itself offer FDSN-style date support.
   Meanwhile interactions with new target services using the FDSN convention would have to compute `end=YYYY-MM-02T00:00:00`. 

 * Bite the bullet now, and have the Python web service present an FDSN-style interface.
   Then the JavaScript in the client must prepare an "end={value}" string
   for sending to the Python, and this must be converted to the older convention for older target services.
   These two conversions, one in JavaScript, one in Python, increase the possibility of coding errors.
 
We chose the second option, so that 

    a. we can support *times* within days in future (e.g. a
       search for events between 00:00 and 06:00 on 1 April 2013), and

    b. we stop perpetuating the same problem of being unclear about what an
       incompletely-specified time like 2013-04-01 means.

The event service handlers for GEOFON and EMSC now convert a request like::

    /event/geofon?end=2013-04-01

into requests for

    <http://geofon.gfz-potsdam.de/eqinfo/list.php?datemax=2013-03-31>

    <http://www.emsc-csem.org/Earthquake/?filter=yes&end_date=2013-03-31>


Implementing extensions
-----------------------

To build a new event service:

1. Add it to the list of configured event services, so that the front end displays it.
   For now, selecting this will do nothing, at best, and probably crash your
   browser.  :-)

   For now, add it in _EventsServicesCatalog in the Python (event.py)

2. Add some test cases in test/testEvent.py.

#. In the Python (event.py) file: subclass EventService.
   You need to provide a handler() method. This function is expected to:

   i.   Builds a query from the parameters it receives.
   ii.  Query the target service
   iii. Process the response to produce a JSON object representing a list of events.
   iv.  Return this object to the caller.

   The EventService class provides several methods to help you do this.

   * result_page()
   * format_response()
   * error_page()

   + the process_parameters function.


   A simple event service class definition might be::

     class ESPhlogiston(EventService):
       def __init__(self, name):
          # Accept defaults, or they can be overridden here:
   	  self.csv_dialect = ...
	  self.column_map = ...
	  self.filter_table = ...
      
       def handler(self, environ, parameters):
          """Get events from http://quakes.phlogiston.org/ as CSV."""

	  # set paramMap to handle the FDSN-style parameters from the QUERY_STRING
	  pairs, bad_list, hold_dict = process_parameters(paramMap, parameters)

	  # Build URL ready for submission and make the request
	  try:
            allrows, url = self.send_request(pairs)
          except urllib2.URLError:
            self.raise_client_400(environ, 'No answer')

	  fmt = hold_dict.get('format', 'text')
	  content = self.format_response(allrows, numrows, limit, fmt)
	  return self.result_page(environ, start_response, '200 OK', 'text/plain', content)


The 'parameters' dictionary contains values for zero or more of the following
arguments:

  ====================    ================    ==============================
  Parameter name          Allowable values     Remarks
  ====================    ================    ==============================
  start                   [0-9TZ:-.]*
  end                     [0-9TZ:-.]*
  minlat                  float [+-][0-9.]
  maxlat                  float
  minlon                  float
  maxlon                  float
  lat                     float
  lon                     float
  minradius               float_pos
  maxradius               float_pos
  mindepth                float                Negative depth is okay
  maxdepth                float_pos
  minmag                  float                Negative mag is okay
  maxmag                  float_pos
  magnitudetype           string???            Can we do wild cards?
                                               What do MT solutions have?
  preferredonly                                Ignored for eqinfo
  eventid                                      Sure, might be handy
  includeallmagnitudes      bool                NOT supported
  includearrivals           bool                NOT supported
  limit              
  offset                  -                   Not in eqinfo
  orderby                 -                   could be
  contributor             -                   Not in eqinfo
  catalog                 -                   ignored
  updatedafter            -                   Ignored for now (EMSC?)
  ====================    ================    ==============================
                   
The values of these parameters (default, type, units etc.) are as set out
in the FDSN standard. In particular date-time strings with no time refer to the start of the day e.g. "end=2000-04-01" implies "2000-04-01T00:00:00.0", the *start* of 1 April, not the end of this day. 

[Extension: lat and lon may be vectors (values separated by commas).
If both have the same number of items, then each lat-lon pair is checked in turn in searching for matching events. It is an error if the lists are of different length, or if one of lat and lon is not present when the other is.]
[The long (unabbreviated) parameter names in Table 1 are *not* supported.]

These are passed to getEvents() during an event services request,
as arguments to the URL.
The similarity to the FDSN 'event' web service *is* intentional. [#vs-fdsnws]_
Some parameters in the FDSN 'event' web service are not relevant to the web interface at present, or are not implemented in the GEOFON eqinfo service, but it should be okay to include them in queries. 

.. rubric:: Footnotes

.. [#vs-fdsnws] See Table 1 of "FDSN
    Web Service Specifications", Version 1.0, 2013/04/24,
    accessed 2013-10-10 from
    http://www.fdsn.org/webservices/FDSN-WS-Specifications-1.0.pdf .
    We do not claim to support the entire FDSN-defined service interface.
    A major difference between this web service and FDSN's is that FDSN web services
    are expected to return parametric data for events as QuakeML - any text/CSV
    output is an undocumented extension of the FDSN interface.
    Furthermore, our services, at this stage, are not available to the general public, or even necessarily hosts beyond `localhost`.

The columns of the CSV list of events must be in the following order:

  .. note::
        Put this table elsewhere.
  
Table: Existing/Proposed/to be implemented event services:

  ============    ==============    ==========================================
  Service Name     Status            Description
  ============    ==============    ==========================================
  geofon           Done              GFZ eqinfo service
  comcat           Done              USGS, replaces NEIC
  emsc             Done              EMSC
  parse            Done              Event time, lat/long by hand on web page
  iris             TODO              Text-based
  file-txt         TODO              Text file upload
  file-qml         TODO              QuakeML file upload
  fdsn-qml         TODO              Generic QuakeML-based service
  sc3-txt
  ============    ==============    ==========================================


* geofon:
   Our GFZ eqinfo service (text services need tuning per supplier).

* EMSC:
   Old pre-FDSN web service at <http://www.emsc-csem.org/>
   -have CSV and JSON and (pre?)QuakeML
   Base: <http://www.emsc-csem.org/Earthquake/?filter=yes&export=csv>

* NEIC: reserved for old service at <http://neic.usgs.gov/>
   Base: <http://neic.usgs.gov/cgi-bin/epic/epic.cgi?>
   + `SEARCHMETHOD=1&FILEFORMAT=6&SEARCHRANGE=HH
   {params} &SUBMIT=Submit+Search`

* sc3fdsnws-txt:
   Talk to a SC3 implementation of FDSN web services, using fmt=txt option.
* fdsnws-qml:
   Talk to a generic implementor of FDSN web services, using QuakeML.
                {baseUrl}/fdsnws/event/1/query?
                {params} &format=&nodata= 

The following table shows how some non-standard services are implemented:

Table: Event service mappings

  ====================  ================  ==================  ==================
  FDSN Standard         GFZ eqinfo        EMSC                NEIC (old)[2]
  ====================  ================  ==================  ==================
  start                  start             start_date          SYEAR,SMONTH,SDAY
  end                    end               end_date[*]         EYEAR,EMONTH,EDAY
  minlat                 latmin            min_lat            -unavailable
  maxlat                 latmax            max_lat
  minlon                 lonmin            min_long            SLON1 ?
  maxlon                 lonmax            max_long            SLON2 ?
  lat                   -unavailable      -unavailable         CLAT
  lon                   -unavailable      -unavailable         CLON
  minradius             -unavailable      -unavailable
  maxradius             -unavailable      -unavailable
  mindepth              -drop[1]           min_depth           NDEP1=0
  maxdepth              -drop              max_depth           NDEP2=depth
  minmag                 magmin            min_mag             LMAG ?
  maxmag                -unavailable[3]    max_mag             UMAG=9.9 ?
  -                                        min_intens
  -                                        max_intens
  -                                        region
  magnitudetype                           -unavailable
  preferredonly                           -unavailable
  eventid                ""               -unavailable
  includeallmagnitudes  -unavailable      -unavailable
  includearrivals       -unavailable      -unavailable
  limit                  nmax              ""
  offset                -unavailable       ""
  orderby               -unavailable      -unavailable
  contributor            ""
  catalog                ""
  updatedafter          -unavailable       "" [1]
  ====================  ================  ==================  ==================


    * "-unavailable" : submission with this parameter would be ignored, result in bad/misleading results, is an error, don't submit.

    * "" : harmless, pass this parameter on to target, but it won't be processed by it.

    Note 1: 'updatedafter' is an attribute present in EMSC output, but is not
    constrainable in query parameters. 'depth' is present in eqinfo output,
    but is not constrainable.
    
    Note 2: Looks like NEIC had no geographical constraints, hence filterEventsFromNEIC did it in the old js/query.js.

    Note 3: We added magmax to the eqinfo service to implement this (July 2013).


3. Implement the functionality

You may need to rename arguments passed to, and reorder outputs etc. received from your target service. This wrapper function achieves that.
Regarding output, see below.

If you encounter an error while querying your target service, simply return an empty string. The getEvent function calling yours will see this response and generate a "204 No Content" response, and the web interface will report to the user that no events were available for the selected event catalogue and parameters.

4. Add an instance of the new class in getEvents() in `events.py`.

#. Add one or more test functions for your function in the TestEventServices
class (`test/testEvents.py`), run the unit tests and start the service stand-alone::

     cd test
     python testEvents.py
     python testMetadata.py
     python manage.py
    
You can now try the service, by visiting <http://localhost:{port}/event/{service}?{params}>

#. Add a new option to generate a different ``<div>`` e.g. a file upload box, or a picker for single event!

#. Restart WSGI on the server, refresh or close your browser to reload JavaScript.

#. Check that the new module works as expected.
   Debugging info goes to Apache's logging (typically
   `/var/log/apache2/error_log`) and SeisComP's logging
   (which may be in `~/seiscomp3/var/log`, depending on your configuration.)

Event service output
--------------------

The event service JSON output must have the structure of a table with one row per event.
The columns in each row are:

   ========   ============   ============    ========================
   Position    Quantity       Type            Remarks
   ========   ============   ============    ========================
    0         Event Time      datetime        Rounded to seconds!
    1         Magnitude       float/str       "--" if not in input
    2         Magn. Type      string          left blank if missing?
    3         Latitude        float
    4         Longitude       float
    5         Depth           float/str       "--" if not in input
    6         Event ID        string          Used by JavaScript
    7         Region          string         Can be filled if missing
   ========   ============   ============    ========================

Rounding event times to the closest second might have consequences if
users expected waveforms to be very carefully aligned.

.. _dev-metadata-module:

Station metadata module
~~~~~~~~~~~~~~~~~~~~~~~

The information related to the inventory is first retrieved and updated from
an Arclink server by means of a script (`data/update-metadata.py`) run from
crontab. The update interval can be configured according to the needs of
the operator. As this information does not change frequently over time, an
update interval of 24 hours is the suggested value.

This information is saved to a file on the server (`data/Arclink-inventory.xml`) and will be read from this file if necessary. The parsing of the file and the creation of the internal representation can take up from 5 to 9 seconds, depending on the hardware. To improve performance, once the information is stored in memory, a dump of all these variables are saved in a temporary file.
If other threads of the server are started, the timestamp of the original
information and the memory dump is checked and the newer is loaded. In this
way, the system does not need to establish a connection with the Arclink
server while consulting the metadata, making operations much faster than in
the previous version of the system.

.. note::  Note on Timeouts for Arclink
   A generous timeout is needed for requesting metadata from a busy server.
   The `arclink_fetch` client uses the Python sockets library, with a default timeout of 300 seconds. ObsPy's <https://github.com/obspy/obspy/blob/master/obspy/clients/arclink/client.py>_ client.py sets this to 20 seconds. So 60 seconds is probably adequate.
  (ObsPy uses additional command_delay = 0, status_delay = 0.5s variables.
  ObsPy uses MAX_REQUEST = 50 STATUS requests, so 25 sec by default.)
  ~~Timeout may have the signature "invalid request:" in the Arclink server logging.~~

  Regardless of success or not, the update-metadata client should probably send "PURGE {request id}".


The internal representation of the metadata consists of four lists representing networks, stations, sensor locations and streams. All the lists contain tuples and every tuple represents one instance of the related information (e.g. one network). 
The structure of these tuples is described below.

Network:

  ==========  ==============  ===============   ===================================================
   Position    Variable        Type              Remarks
  ==========  ==============  ===============   ===================================================
    0          Code            string
    1          First station   int               Pointer to the first station of the network.
                                                 If it is a virtual network, this should be None.
    2          Last station    int               Pointer to the last station of the network
                                                 (exclusive; to be used with the function range).
                                                 If it is a virtual network, this should be None.
    3          Stations        list              Station pointers in case of a virtual network.
    4          Start year      int               Start year of operation.
    5          End year        int               End year of operation.
    6          Description     string
    7          Restricted      int               1: restricted; 2: open.
    8          Class           char              'p' for permanent and 't' for temporary.
    9          Archive         string            Archiving node, 'GFZ', 'RESIF', 'INGV', etc.
   10          Institutions    string            Network operators.
  ==========  ==============  ===============   ===================================================


Station:

  ==========  ==============  =============   ===================================================
   Position    Variable        Type            Remarks
  ==========  ==============  =============   ===================================================
    0         Network         int              Pointer to the containing network.
    1         First sensor    int              Pointer to the first sensor of the station.
    2         Last sensor     int              Pointer to the last sensor of the station.
                                               (exclusive; can be used with `range`).
    3         Reserved        NoneType
    4         Code            string           Station code.
    5         Latitude        float
    6         Longitude       float
    7         Description     string
    8         Start date      datetime         Start date and time of operation.
    9         End date        datetime         End date and time of operation.
   10         Elevation       float
   11         Restricted      int              1: restricted; 2: open.
  ==========  ==============  =============   ===================================================


Sensor Location:

   ========   ============   ============    =====================================================
   Position    Variable       Type            Remarks
   ========   ============   ============    =====================================================
    0         Station         int             Pointer to the belonging station.
    1         First stream    int             Pointer to the first stream of the sensor.
    2         Last stream     int             Pointer to the last stream of the sensor.
                                              (exclusive; can be used with `range`).
    3         Reserved        NoneType
    4         Code            string          Sensor code.
   ========   ============   ============    =====================================================


Stream:

   ========   ==============   ============    =====================================================
   Position    Variable         Type            Remarks
   ========   ==============   ============    =====================================================
    0         Sensor            int             Pointer to the belonging sensor.
    1         Code              string          Stream code.
    2         Sensor type       string
    3         Sample denom.     float
    4         Sample numer.     float
    5         Datalogger        string
    6         Start date        datetime        Start date and time of operation.
    7         End date          datetime        End date and time of operation.
    8         Restricted        int             1: restricted; 2: open.
   ========   ==============   ============    =====================================================

.. _dev-mapping-module:

Maps module
~~~~~~~~~~~

Uses OpenLayers.

The icons supplied for station and event markers are 13x13 PNG images, with an alpha channel.
They were produced using Inkscape.

.. _dev-requests-module:

Data requests module
~~~~~~~~~~~~~~~~~~~~

This part communicates with the Arclink server. It can break large requests
into chunks and handle splitting requests between servers.

FIXME: Andres, does "reroute" work down the routing table in priority order, or something else?

.. _dev-configuration-module:

Configuration
=============

webinterface.cfg is processed using SeisComP configuration code.
It is read in by ...XXX.
Configuration values can be obtained in the Python code by ... XXXX.

