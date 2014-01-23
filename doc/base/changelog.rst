
**************
Change History
**************

Initial revision
================

Compared to the old web interface, developed until 2012,
there are many internal and external differences.

* Site customisation: There's no more html_chunks.py! Instead just create index.html containing the hooks you need. See :ref:`op-customization`.

* Modular support for multiple event catalogs.
 
   - The old NEIC service has been removed, and replaced by USGS's Comcat service.

   - EMSC's service has been added.

   - You can upload events from a custom CSV catalog.

* Stations/metadata:

  - Webinterface caches inventory data from its base Arclink server. This
    saves many Arclink requests and gives much better performance.
    The `update-metadata.sh` script is provided as a tool for refreshing locally
    downloaded data.

  - There is better display of what streams are available for a particular set of stations.
  - Selection based on sample rate closest to a specific value is possible.

* Request handling:

  - Request status is displayed for all data centres which were involved in
    handling a request.

  - Routing/retrying/refreshing.

* This documentation exists.

v0.3 (2013-10-11)
=================
* js - event services URL can have a limit. Quick M>=6 feature.
  Extra help comments. Different event symbols.
* For events and stations, 'Search' -> 'Search/Append'
* For events and stations, items which are unselected remain visible on the
  map.
* Add 'restricted' column on station table.
* Request metadata/streams by POST not GET.
* Warning on too many unpurged requests at the data centre.
* Swap "Time Window selection" and "Request information" on submit tool.
* Added 'type="text/javascript"' to <script> elements in HTML documents.
* Documentation: Many small improvements and updates.

v0.4 (2014-01-22)
============================

* Events: Magnitude type is displayed in event service output, if available.
  Removed the GFZ>M6.0 button. Set ``event.defaultLimit = 800``.
* Stations: support restricted streams, shown in red on the station list.
* BUG FIX to support IE>8.
* Moved example HTML files into examples; moved wsgi/webinterface.cfg to wsgi/webinterface.cfg.sample.
* Documentation:
  - Notes on customisation, and upgrading.
  - Notes on browser compatibility, bzip2 compression and response dictionaries.
  - "WebDC3" references; minor language improvements; lots of minor polish, spell-checking etc.
