.. _self-study tutorial:

*******************
Self-study Tutorial
*******************

Peter L. Evans, GEOFON team
pevans@gfz-potsdam.de


Introduction
============
The GEOFON WebDC3 web interface is a new and powerful web-based tool to explore earthquake event catalogs, browse seismic stations, and extract seismic waveforms and station metadata from the EIDA archive system. It extends the old WebDC service in several interesting ways.

This document is intended to be a self-study guide to performing a few common tasks with the web interface tool, and demonstrating the new features. It is task-driven: you will be asked to find a few sets of data, and guided through the way where necessary. The whole set of tasks shouldn't take more than half an hour (it takes me a few minutes to click here and there, but then I wrote this document, and helped develop the software.)

Each task below is focussed on extracting some specific information from the system. There is a question for each one. Answers are at the back. No peeking!
If you encounter problems along the way, it may be because the interface is unclear, the documentation in the User Guide is incomplete, or there are bugs in the software. *Please* let us know about your experience. You can send e-mail to geofon@gfz-potsdam.de, or contact me at the address above.

If you're stuck, note the on-line help available as pop-ups (or whatever).
Also you can click on the link in the top right corner of the page.

To start, open your web browser on to the web interface start page, either at [http://eida.gfz-potsdam.de/webdc3] or at your local site.


Event browsing
==============
Q: `In July 2013, how many big earthquakes were there, worldwide?`

Click on the "Explore events" tab at the top of the page. You will see a box titled "Events Controls". Use this to make a selection of events in the GFZ event catalog. Press "Search" when you are ready. You should see a list of events and they are displayed on the map.

 1. How many had magnitude >=6?

 2. How many had magnitude >=5.5?

 3. (Harder) How many of these are also in the EMSC and USGS seismic catalogs?

Clear your selection of events (click "Delete Events"). 
Now we'll ask a more specific question:

 4. How many events are recorded near Tonga
    (Nukualofa, 21 degrees S latitude, 175 degrees W longitude, within say 5 degrees)
    with M>4?
    Of these, how many have depth between 100 and 400 km?


Station browsing
================
Q: `How many stations are there in the GEOFON seismic network?`

Click on the "Explore stations" tab to expand the "Stations Controls" box.

 1. How many stations were in the GEOFON network (network code "GE") in 2013?
    According to inventory, how many of these had BH stream data:

     a. Based on channel codes? [Use "by Code".]

     #. Based on sample rate close to 20 sps? Is there a difference?
        (Hint: see the help page.)

 #. How many of these stations have STS-2 instruments?
    `This one can't be done with our first version.`
 
 #. Press the "Reset" button in the Station Controls.
    For the network GE station APE (Apirathos, Naxos, Greece), how many
    channels are available altogether?

 #. How many stations were in the GE network in 2003?

 #. [What about something EIDA-wide too? For this you need "All shared networks".]


Requesting waveform data
========================
Q: `What waveforms do you have for my event?`

Reload the page.
Request mini-SEED waveform data for all Mediterranean broadband stations
(within 4 degrees) which recorded the M5.0 event in Central Italy on 2013-07-21.
Under "Explore Stations", use the "by Regions" button to filter stations by region.
Restrict your selection to just BH channels.

Use the "Submit request" tab.
Request just the vertical component (BHZ) using "Filter" on the station list.
Use "Relative mode" on the "Submit request" tab to set time
windows from 1 minute before the expected P wave arrival to 5 minutes after
the expected S wave arrival for each station.

Request full SEED waveform data. Click "Review request". Once your request
is sent, use the "Download data" tab to see how your request is progressing.

 - how many streams did you obtain?

 - how many time windows, *z*, are there in your request?

 - how many time windows, *y*, are in your request (use the "Review" button)?

 - how many time windows, *x*, returned data (use the "Status" tab)?

 - what is the size of the file you downloaded?

Note that *x* <= *y* <= *z* because:
  1. A time window with a P arrival can't be computed for all stations.
  2. We have no data from some stations at the times requested.


Requesting station metadata
===========================
Q: `I need to set up my new SeisComP system. How do I get the metadata I need?`

One way to do this is via Arclink inventory XML.
On the Station Controls, select for years 2011 to 2013.
Pick the GEOFON network (code GE) from the list under "Code". 
Under "Submit request", pick "Metadata (Inventory XML)" (and "Absolute Mode").

Another way is via dataless SEED. Which is smaller?


Request status and cleaning up
==============================
Q: `What's the status of my request?`
You can also see what requests are pending, i.e. haven't been completed, and are available for downloading.
Go to the ``Download data`` tab.

Click on a line starting "Package..." to see its status.
Use the "Refresh" button, and for a big request, you may notice
the number of lines with "Status: PROCESSING" increases, while
that with "Status: UNSET" decreases. When everything is done,
you will see "Status: OK" and green text "Download Volume".
Clicking on this text lets you save the data to your local computer.

Using catalog upload
====================
Q: `But I have my own event catalog! Can I still use the web interface?`

On 15 February 2013 a meteor exploded over Chelyabinsk, Russia
[http://en.wikipedia.org/wiki/Chelyabinsk_meteor].
What waveform data do you have around this time? A quick look in the GFZ
catalog shows we have no event associated with this meteor. Create a custom
event by choosing "User Supplied" in the Event Controls box. Use depth 0 and time 03:20 UTC.

Now download BHZ data for stations within 90 degrees of 55.0 degrees N, 61 degrees E.

[I need a good simple way to view SEED data.]


Data at different EIDA nodes
============================
Q: `Isn't there more than one EIDA node?`

Within the EIDA system, waveform data may be stored at only one participating
EIDA node, but it is still available from the web interface running at GFZ or
other nodes. For example seismic network CH is hosted at ETH in
Zürich, while GE data is here at GFZ.
Request BHZ/HHZ waveforms for all stations in
[a box from 45 to 55 degrees N, 5 to 15 degrees E - including some German stations.]
Note that GEOFON station GE.RUE, XXX and XXX are included - data for these is stored at GFZ Potsdam and BGR Hannover/LMU Munich respectively.
As a time window, take the first 15 minutes of April 1, 2013. How many streams are in your request?

Note that your request is broken into volumes and sent to each node.
You can see the status of each one using the ``Download data`` tab.

Direction-based searches
========================
Find all stations to the north (i.e. azimuth between 330 and 30, distance less than
120 degrees) of any South American event with M>6.0 between January 1 and
March 31 of 2013.

You must first select the events, from the ``Explore events`` tab.
Then use the "Explore Stations tab to go to the Stations Controls.
Select "by Events" and the desired event distance and azimuth.

Last words
==========
Finally, clean up your requests, after downloading them.
(From ``Download data``, put your e-mail address in the Manage Requests box,
and click "Get Status", to see all your requests at all EIDA nodes.
Now you can delete them all when you are ready.)

Thank you for working through this document. Here are the final questions:

 1. How long did it take you to work through these tasks?

 #. How can we improve the web interface?

 #. Can you give us an example of a request you would often like to make, but can't today?

The answers to these questions are **not** provided below.

Answers to exercises
====================

 .. note::
  The specific event numbers, stream details, file sizes etc. listed here were
  accurate for the GFZ web interface at
  http://eida.gfz-potsdam.de/webdc3 in August 2013.
  They may have changed by the time you work through this document.

Event browsing
~~~~~~~~~~~~~~
 1. 13 with M>=6.0; there is 1 with M5.9, and 1 with M5.8

 2. 33, plus 5 with M5.4; but setting magmin=5.4 gives 39!

 3. For M>=6.0 there are also 13 with all catalogs; but differences can occur
    when the magnitude is close to the threshold.
    For M>5.5, EMSC has 40 events, while USGS has 33.

 4. 15, and 2 (at 2013-07-24T03:32:33Z and 2013-07-30T03:00:32Z).

Station browsing
~~~~~~~~~~~~~~~~
 1. In 2013: 75 stations; but this may increase during the year.
    [There might be a difference between these two ways of selection.]

 3. 5 x 3 components = 15 channels.

 4. In 2003 there were 52 stations.

Requesting waveform data
~~~~~~~~~~~~~~~~~~~~~~~~
The event in question has latitude 43.56N, longitude 13.76E. I found 333
stations in inventory, from at least 12 different networks, within 4 degrees.
For BH streams, there are 189 stations.

There are hundreds of stations you could use for this.
Out of my selection of 189 stations, filtering down to BHZ built a request
with `y` = 185 traces, with one time window per station. 

(Since much of the data is at INGV, not GFZ, there may sometimes be routing
problems in fulfilling your request.)

Requesting station metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For GE metadata for 2011-2013, my inventory XML file was 760 kB for 1383
streams in 75 stations. 
The corresponding dataless SEED file was about 512 kB.

Direction-based searches
~~~~~~~~~~~~~~~~~~~~~~~~

Use longitude 85W to 25W, latitude 60S to 15N; there are only 2 events.
I found over 130 matching stations, from networks 5E, CN, CX, DK (Greenland), G, GE and others.
