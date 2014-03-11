# Configuration for events module.
# This is a temporary "solution" (PLE Aug 2013)
# It replaces reading from webinterface.cfg using the seiscomp3 libraries.

conf = {}
conf['catalogs'] = dict()
## not used: conf['catalogs']['ids'] = ('geofon', 'comcat', 'emsc', 'meteor')
conf['catalogs']['ids'] = ('geofon', 'comcat', 'emsc', 'parser', 'meteor','ingv')
conf['catalogs']['preferred'] = 'geofon'
conf['defaultLimit'] = 480

conf['verbosity'] = 2

conf['service'] = dict()
conf['service']['geofon'] = {
            'description': 'GFZ',
            'baseURL': 'http://geofon.gfz-potsdam.de/eqinfo/list.php',
            'extraParams': 'fmt=csv',
            }
conf['service']['comcat'] = {
        'description': 'USGS',
        'baseURL': 'http://comcat.cr.usgs.gov/earthquakes/feed/v0.1/search.php',
        'extraParams': 'format=csv',
        }
conf['service']['emsc'] = {
        'description': 'EMSC',
        'baseURL': 'http://www.emsc-csem.org/Earthquake/',
        'extraParams': 'filter=yes&export=csv',
        }
conf['service']['ingv'] = {
        'description': 'INGV',
        'baseURL': 'http://webservices.rm.ingv.it/fdsnws/event/1/query',
        'extraParams': 'format=text&user=webinterface',
    }
conf['service']['meteor'] = {
        'description': None,
	}

conf['service']['parser'] = {
	# Service needs to be created, but not displayed.
	'description': None,
	}
        # Other old/partially complete/partially dead catalogs:
        #"neic":   "NEIC/? (DEAD)",
        #"file":   "File upload: use event/parse instead",
        #"iris":   "IRIS: Not yet"

conf['names'] = {
    'lookupIfEmpty': True, 
    'lookupIfGiven': False,
}
