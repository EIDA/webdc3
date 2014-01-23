The WebDC3 web interface generator
==================================

This code was developed from the old webdc.eu portal developed at GFZ in the
NERIES project. In the first stage we decided to maintain the functionalities
already achieved focusing on a code clean-up and technology upgrade to
accommodate the current EIDA needs.

The new web interface looks different, but functions more or less
like the old one. Users can select waveforms, dataless SEED, and inventory XML
for downloading. The selection can be constrained
by streams by network, station location, channel and other properties,
and the time windows chosen can be constrained based on user-selected events.

The web interface mainly uses JavaScript for presentation,
with Python used to provide underlying services.

This documentation contains:

 * A :ref:`user-guide` for getting data from the running web interface.

 * :ref:`operator-guide`, for installing and configuring the software.

 * The :ref:`developer-guide`, for understanding the internal functions and
   contributing new code such as event services.

As an appendix, there is a :ref:`self-study tutorial` as a base to get your
users familiar with what they can do with the tool.

We hope you find it useful.
