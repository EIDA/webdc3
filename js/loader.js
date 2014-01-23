/*
 * GEOFON WebInterface
 *
 * loader.js module: This is the loader module for the web-interface. It should
 *                   try to load all the other needed JS files.
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, GFZ Potsdam
 *  June/July 2013
 *
 */

/*
 * Page-wide variable to provides the loader to all modules in case they want to 
 * load some other JS files or even CSS files.
 */
var interfaceLoader = undefined;

/*
 * Loader Object implementation
 */
function InterfaceLoader(js, css, debug) {
	// Global debuging flag, is exported thru the 
	// this.debug() method and used
	// by other modules
	var _debug = debug;
	var _js_source = js;
	var _css_source = css;

	// List of modules to load
	var _js_lines = Array();

	// Interval between checks (milliseconds?)
	var _check_interval = 100;

	// Current State flags
	var _running = false;
	var _oChecking = false;
	var _mChecking = false;

	// Current Module parts
	var _current_module = undefined;
	var _current_object = undefined;
	var _current_method = undefined;

	// This method sets a module indicated my "jsModule" to be loaded and
	// a variable name "jsVariable" to be checked for existence and a
	// method "jsMethod" to be called before the complete loading
	// procedure is completed. The variable jsVariable should be an
	// object, that should have a method called "jsMethod" that should
	// return true or false.
	//
	// When jsVariable is undefined or null this object is not checked.
	// When jsMethod is undefined or null this method is not called.
	//
	// maxDelay is given in milliseconds.
	this.loadjs = function(jsModule, jsVariable, jsMethod) {
		_js_lines.push( [jsModule, jsVariable, jsMethod] );
	};

	this.runjs = function(){
		check_js();
	};

	this.debug = function() {
		return _debug;
	};

	this.loadcss = function(cssFile) { 
		$("head").append("<link>");
		css = $("head").children(":last");
		css.attr({
			rel:  "stylesheet",
			type: "text/css",
			href: _css_source + cssFile
		});
	};

	// Private
	function check_js() {
		if (_running) {
			window.setTimeout(check_js, _check_interval);
			return;
		}

		if (_oChecking) {
			if ( window[_current_object] === undefined ) {
				window.setTimeout(check_js, _check_interval);
				return;
			}
			_oChecking = false;
		}

		if (_mChecking) {
			if ( eval(_current_object + "." + _current_method)() !== true) {
				window.setTimeout(check_js, _check_interval);
				return;
			}
			_mChecking = false;
		}

		// Reset the variable for a next possible run
		_current_module = undefined;
		_current_object = undefined;
		_current_method = undefined;

		if (_js_lines.length > 0) {
			var current = _js_lines.shift();
			_current_module = current[0];
			_current_object = current[1];
			_current_method = current[2];

			// Init
			_running = true;
			_oChecking = (_current_object !== undefined && _current_object !== null);
			_mChecking = (_current_method !== undefined && _current_method !== null);

			// Load
			$.getScript(_js_source + _current_module)
			.done(function() {
				_running = false;
			})
			.fail(function(jqxhr, settings, exception) {
				if (_debug) console.error("loader.js: Error found while loading script: " + _current_module + " [" + exception + "]");

				_running = false;
				_oChecking = false;
				_mChecking = false;

				_current_module = undefined;
				_current_object = undefined;
				_current_method = undefined;
			});

			// Trigger the next check
			window.setTimeout(check_js, _check_interval);
			return;
		}

		return;
	};

	// Main code
	if (!debug) debug = true;

	if (_js_source)
		_js_source += (_js_source[_js_source.length-1] !== '/') ? '/' : '';
	if (_css_source)
		_css_source += (_css_source[_css_source.length-1] !== '/') ? '/' : '';
};

$(document).ready(function() {
	window.WIError = function(message) {
		this.name = undefined; // omit exception name on the console
		this.message = message;
		this.toString = function() { return this.message; }
	}

	window.WIError.prototype = new Error;

	try {
		// Check and set defaults.
		// These variables should be exported by webinterface.py
		var js = ((typeof eidaJSSource) !== 'undefined') ? eidaJSSource : "js/";
		var css = ((typeof eidaCSSSource) !== 'undefined') ? eidaCSSSource : "css/";
		var debug = (typeof eidaDebug !== 'undefined') ? eidaDebug : true;

		// Make loader
		interfaceLoader = new InterfaceLoader(js, css, debug);

		// Push methods in to be loaded
		interfaceLoader.loadjs('console.js', "wiConsole", null);
		
		// This is the configuration proxy. Before we continue to load the
		// other modules the method configurationProxy.finished() has to 
		// return "true".
		interfaceLoader.loadjs('config.js', "configurationProxy", "finished");
		
		// Other Page parts

		// Map has to come before station/event because those 
		// wants to register on coordinate update
		interfaceLoader.loadjs('mapping.js', "mapControl", null);

		interfaceLoader.loadjs('service.js', "wiService", null);
		interfaceLoader.loadjs('status.js', "wiStatusListControl", null);
		interfaceLoader.loadjs('request.js',"requestControl");
		interfaceLoader.loadjs('events.js', "eventSearchControl", null);
		interfaceLoader.loadjs('station.js', "stationSearchControl", null);
		interfaceLoader.loadjs('submit.js', null, null);
		interfaceLoader.loadjs('review.js', null, null);
		interfaceLoader.loadjs('interface.js', null, null);

		// Start the loading of the indicated modules
		interfaceLoader.runjs();
		
		interfaceLoader.loadcss("wimodule.css");
	}
	catch (e) {
		console.error("loader.js: " + e.message);
	}
});
