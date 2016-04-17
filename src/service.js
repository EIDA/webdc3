/*
 * GEOFON WebInterface
 *
 * service.js: Convenient interface to the Python webservice.
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Andres Heinloo, Javier Quinteros, GFZ Potsdam
 *  June/July 2013
 *
 */

function WIService() {
	// Private stuff

	var _busyCount = 0

	function increaseBusyCount() {
		if (++_busyCount == 1)
			$(document.body).addClass('busy')
	}

	function decreaseBusyCount() {
		if (--_busyCount == 0)
			$(document.body).removeClass('busy')
	}

	function doneFn(func, bc, fail) {
		return function(rawdata, statustext, jqxhr) {
			try {
				var data = (rawdata !== undefined)? $.parseJSON(rawdata): undefined
			}
			catch (e) {
				// construct a fake jqXHR object
				var jqxhr = {
					status: 0,
					statusText: "JSON Parse Error",
					responseText: e.message
				}

				// divert to fail
				fail(jqxhr, statustext, e)
				return
			}

			if (bc) decreaseBusyCount()

			if (func) {
				try {
					func(data, statustext, jqxhr)
				}
				catch (e) {
					wiConsole.error(e.message, e)
				}
			}
		}
	}

	function failFn(func, bc, msg) {
		return function(jqxhr, statustext, exc) {
			if (bc) decreaseBusyCount()

			if (func) {
				try {
					func(jqxhr, statustext, exc)
				}
				catch (e) {
					wiConsole.error(e.message, e)
				}
			}
			else {
				var err

				if (jqxhr.status == 500)
					err = jqxhr.statusText
				else
					err = jqxhr.responseText

				wiConsole.error(msg + ": " + err)
			}
		}
	}

	function get(done, fail, bc, url, failMsg, param1, param) {
		if (bc) increaseBusyCount()

		// allow giving parameters separately or as a single object
		if (typeof param1 == "object") param = param1

		// allow optional parameters
		for (var p in param) {
			if (param[p] === undefined)
				delete param[p]
		}

		// avoid caching
		param._ = $.now()

		var f = failFn(fail, bc, failMsg)
		return $.get(url, param, doneFn(done, bc, f)).fail(f)
	}

	function post(done, fail, bc, url, failMsg, param1, param) {
		if (bc) increaseBusyCount()

		// allow giving parameters separately or as a single object
		if (typeof param1 == "object") param = param1

		// allow optional parameters
		for (var p in param) {
			if (param[p] === undefined)
				delete param[p]
		}

		var f = failFn(fail, bc, failMsg)
		return $.post(url, param, doneFn(done, bc, f)).fail(f)
	}

	// Public functions defined in interface-server-client.txt
	//
	// Arguments:
	//     done	function to be called if the request was successful (optional)
	//     fail	function to be called if the request failed (optional, by default
	//     		an alert popup with error message will be displayed)
	//     bc	change cursor to "busy" while the request is running
	//     first parameter or an object containing all parameters
	//     second parameter
	//     ...

	this.configuration = function(done, fail, bc, param1) {
		var param = {}
		var url = configurationProxy.serviceRoot() + 'configuration'
		var failMsg = "Failed to get configuration"
		return get(done, fail, bc, url, failMsg, param1, param)
	}

	this.loader = function(done, fail, bc, param1) {
		var param = {}
		var url = configurationProxy.serviceRoot() + 'loader'
		var failMsg = "Failed to get loader"
		return get(done, fail, bc, url, failMsg, param1, param)
	}

	this.metadata = {
		sensortypes: function(done, fail, bc, param1) {
			var param = { }
			var url = configurationProxy.serviceRoot() + 'metadata/sensortypes'
			var failMsg = "Failed to get sensor type list"
			return get(done, fail, bc, url, failMsg, param1, param)
		},

		networktypes: function(done, fail, bc, param1) {
			var param = { }
			var url = configurationProxy.serviceRoot() + 'metadata/networktypes'
			var failMsg = "Failed to get networks types list"
			return get(done, fail, bc, url, failMsg, param1, param)
		},

		phases: function(done, fail, bc, param1) {
			var param = { }
			var url = configurationProxy.serviceRoot() + 'metadata/phases'
			var failMsg = "Failed to get supported phase list"
			return get(done, fail, bc, url, failMsg, param1, param)
		},

		networks: function(done, fail, bc, start, end, networktype) {
			var param = { start: start, end: end, networktype: networktype }
			var url = configurationProxy.serviceRoot() + 'metadata/networks'
			var failMsg = "Failed to get networks"
			return get(done, fail, bc, url, failMsg, start, param)
		},

		stations: function(done, fail, bc, start, end, networktype, network) {
			var param = { start: start, end: end, networktype: networktype,
				network: network }
			var url = configurationProxy.serviceRoot() + 'metadata/stations'
			var failMsg = "Failed to get stations"
			return get(done, fail, bc, url, failMsg, start, param)
		},

		streams: function(done, fail, bc, start, end, networktype, network, station) {
			var param = { start: start, end: end, networktype: networktype,
				network: network, station: station }
			var url = configurationProxy.serviceRoot() + 'metadata/streams'
			var failMsg = "Failed to get streams"
			return post(done, fail, bc, url, failMsg, start, param)
		},

		query: function(done, fail, bc, start, end, network, networktype, station, sensortype, preferredsps,
				streams, minlat, maxlat, minlon, maxlon, minradius, maxradius, minazimuth,
				maxazimuth, events) {
			var param = { start: start, end: end, network: network, networktype: networktype,
				station: station, sensortype: sensortype, preferredsps: preferredsps, streams: streams,
				minlat: minlat, maxlat: maxlat, minlon: minlon, maxlon: maxlon,
				minradius: minradius, maxradius: maxradius,
				minazimuth: minazimuth, maxazimuth: maxazimuth, events: events }
			var url = configurationProxy.serviceRoot() + 'metadata/query'
			var failMsg = "Metadata query failed"
			return post(done, fail, bc, url, failMsg, start, param)
		},

		timewindows: function(done, fail, bc, streams, start, end, events,
				startphase, startoffset, endphase, endoffset) {
			var param = { streams: streams, start: start, end: end,
				events: events, startphase: startphase, startoffset: startoffset,
				endphase: endphase, endoffset: endoffset }
			var url = configurationProxy.serviceRoot() + 'metadata/timewindows';
			var failMsg = "Failed to get time windows"
			return post(done, fail, bc, url, failMsg, streams, param)
		},

		export: function(done, fail, bc, streams) {
			var param = {streams: streams};
			bc = false;
			var url = configurationProxy.serviceRoot() + 'metadata/export';
			var failMsg = "Oops, couldn't save streams list";
			return post(done, fail, bc, url, failMsg, streams, param);
		},

	}

	this.event = {
		catalogs: function(done, fail, bc, param1) {
			var param = {}
			var url = configurationProxy.serviceRoot() + 'event/catalogs'
			var failMsg = "Failed to get event catalogs"
			return get(done, fail, bc, url, failMsg, param1, param)
		},

		parse: function(done, fail, bc, format, columns, input) {
			var param = { informat: format, columns: columns, input: input }
			var url = configurationProxy.serviceRoot() + 'event/parse'
			var failMsg = "Failed to post event parser service";
			var br = ";";
			failMsg += br;
			failMsg += " informat: " + format + br;
			failMsg += " columns: " + columns + br;
			failMsg += " input: '" + input + "'" + br;

			return post(done, fail, bc, url, failMsg, format, param)
		},

		query: function(done, fail, bc, catalog, start, end, minmag, maxmag, mindepth, maxdepth, minlat, maxlat, minlon, maxlon) {
			var param = { start: start, end: end, minmag: minmag, maxmag: maxmag, mindepth: mindepth,
					maxdepth: maxdepth, minlat: minlat, maxlat: maxlat, minlon: minlon, maxlon: maxlon }
			var failMsg = 'Failed to get events'
			var srvName = undefined

			if (typeof catalog === "object") {
				if (typeof catalog["catalog"] === "undefined") {
					// construct a fake jqXHR object
					var jqxhr = {
						status: 400,
						statusText: "Bad Request",
						responseText: "invalid catalog service"
					}

					// make sure that either fail or done is always called
					failFn(fail, false, failMsg)(jqxhr)
					return
				}

				srvName = catalog.catalog
				delete catalog.catalog
			}
			else {
				srvName = catalog
			}

			var url = configurationProxy.serviceRoot() + 'event/' + srvName
			return get(done, fail, bc, url, failMsg, catalog, param)
		}
	}

	this.request = {
		types: function(done, fail, bc, param1) {
			var param = {}
			var url = configurationProxy.serviceRoot() + 'request/types'
			var failMsg = "Failed to get request types"
			return get(done, fail, bc, url, failMsg, param1, param)
		},

		nodes: function(done, fail, bc, param1) {
			var param = {}
			var url = configurationProxy.serviceRoot() + 'request/nodes'
			var failMsg = "Failed to get node list"
			return get(done, fail, bc, url, failMsg, param1, param)
		},

		status: function(done, fail, bc, server, user, request, start, count) {
			var param = { server: server, user: user, request: request, start: start, count: count }
			var url = configurationProxy.serviceRoot() + 'request/status'
			var failMsg = "Failed to load status from " + server
			return get(done, fail, bc, url, failMsg, server, param)
		},

		purge: function(done, fail, bc, server, user, request) {
			var param = { server: server, user: user, request: request }
			var url = configurationProxy.serviceRoot() + 'request/purge'
			var failMsg = "Failed to purge request " + request + " at " + server
			return get(done, fail, bc, url, failMsg, server, param)
		},

		submit: function(done, fail, bc, user, requesttype, compressed, responsedictionary,
				timewindows, eventinfo) {
			var param = { user: user, requesttype: requesttype, compressed: compressed,
				responsedictionary: responsedictionary,
				timewindows: timewindows, eventinfo: eventinfo }
			var url = configurationProxy.serviceRoot() + 'request/submit'
			var failMsg = "Failed to submit request"
			return post(done, fail, bc, url, failMsg, user, param)
		},

		resubmit: function(done, fail, bc, user, uuid, mode, idlist) {
			var param = { user: user, uuid: uuid, mode: mode, idlist: idlist }
			var url = configurationProxy.serviceRoot() + 'request/resubmit'
			var failMsg = "Failed to " + mode + " request " + uuid
			return post(done, fail, bc, url, failMsg, user, param)
		},

		// Special case: return download URL
		downloadURL: function(server, user, request, volume) {
			var param = { server: server, user: user, request: request, volume: volume }
			var url = configurationProxy.serviceRoot() + 'request/download'

			// allow giving parameters separately or as a single object
			if (typeof server == "object") param = server

			// allow optional parameters
			for (var p in param) {
				if (param[p] === undefined)
					delete param[p]
			}

			return url + '?' + $.param(param)
		}
	}
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.wiService = new WIService()
			resolve()
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("service.js: " + e.message)

			wiConsole.error("service.js: " + e.message, e)
			reject()
		}
	})
}

