/*
 * GEOFON WebInterface
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, GFZ Potsdam
 *
 * config.js module: A config proxy to load the configuration variables from
 * the Python interface level (server) into the JavaScript client level.
 *
 */

/*
 * Page wide variable to provides the configuration proxy to all modules
 */
var configurationProxy = undefined;

/*
 * Configuration proxy Object implementation
 */
function ConfigurationProxy(url) {
	// Private
	var _url = undefined;
	var _loadComplete = undefined;
	var _cache = {};

	function gotResponse(data) {
		_cache = data;
		_loadComplete = true;
	}

	/* Reload the configuration from the server */
	reload = function() {
		if (_url === undefined) {
			alert('config.js: Server URL is not defined.');
			return;
		}

		_cache = {};
		_loadComplete = false;
		$.getJSON(_url + 'configuration', gotResponse);
	};


	// Public
	/* Get one configuration value */
	this.value = function(key, defaultValue) {
		if ( _loadComplete === undefined ) {
			if (interfaceLoader.debug()) console.error("Please call the reload method, config not loaded.");
			return defaultValue;
		}

		if ( _loadComplete === false ) {
			if (interfaceLoader.debug()) console.error("Configuration not yet loaded from the server. Please retry later.");
			return defaultValue;
		}

		var current = _cache;

		var keys = key.split(".");
		for(keyid in keys) {
			var level = keys[keyid];
			if ( (current === null) || (current[level] === undefined) ) {
				current = null;
				break;
			}
			current = current[level];
		}
		
		if (current === null) return defaultValue;
		return current;
	};

	/* This means that the module has finished to load */
	this.finished = function() {
		return _loadComplete;
	};

	this.serviceRoot = function(){
		return _url;
	};

	// Main Object Implementation
	if (!url) {
		if (interfaceLoader.debug()) console.error('config.js: Need a base server address to query for configuration parameters.');
		return;
	}

	// Check the last slash on the url
	_url = url + ( ( url[url.length-1] !== '/' ) ? '/' : '' );
	
	// Trigger the first loading of configuration
	reload();
}

/*
 * Bind the config to the document.ready method so that it is automatically 
 * loaded when this JS file in imported (by the loader).
 */
$(document).ready(function() {
	try {
		var sr = ((typeof eidaServiceRoot === 'undefined')) ? "wsgi/" : eidaServiceRoot;
		configurationProxy = new ConfigurationProxy(sr);
	}
	catch (e) {
		if (console.error !== wiConsole.error)
			console.error("config.js: " + e.message);

		wiConsole.error("config.js: " + e.message, e);
	}
});
