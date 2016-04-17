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
 * Configuration proxy Object implementation
 */
function ConfigurationProxy(url) {
	// Private
	var _url = undefined;
	var _cache = {};

	/* Reload the configuration from the server */
	this.reload = function() {
		return new Promise(function(resolve, reject) {
			if (_url === undefined) {
				reject(new Error("server URL is not defined"));
				return;
			}

			_cache = {};
			$.getJSON(_url + 'configuration').done(function(data) {
				_cache = data;
				resolve();
			})
			.fail(function() {
				reject(new Error("AJAX error"));
			});
		});
	};


	// Public
	/* Get one configuration value */
	this.value = function(key, defaultValue) {
		var current = _cache;

		var keys = key.split(".");
		for(var keyid in keys) {
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
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		function error(e) {
			if (console.error !== wiConsole.error)
				console.error("config.js: " + e.message);

			wiConsole.error("config.js: " + e.message, e);
			reject();
		}

		try {
			var sr = ((typeof eidaServiceRoot === 'undefined')) ? "wsgi/" : eidaServiceRoot;
			window.configurationProxy = new ConfigurationProxy(sr);
			window.configurationProxy.reload().then(resolve).catch(error);
		}
		catch (e) {
			error(e);
		}
	});
}

