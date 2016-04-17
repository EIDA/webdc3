/*
 * Geofon WebInterface
 *
 * console.js: Logging functions.
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, Andres Heinloo, GFZ Potsdam
 *  June/July 2013
 *
 */

/*
 * Implementation of the wiConsole
 */
function WIConsole(htmlTagId) {

	// Private

	var _controlDiv = null
	var _callback = null
	var _maxMessages = 100
	var _level = 0
	var _msgClass = 'wi-console-debug'

	function load(htmlTagId) {
		var control = $(htmlTagId)

		// If we don't find one div ...
		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("console.js: Cannot find a div with class '" + htmlTagId + "'")
			return
		}

		// otherwise finish load ...
		_controlDiv = control
	}

	function log(msgClass, msg, exc) {
		var msgList = _controlDiv.children()

		if (!msgList.length) {
			// Append a clear console link as the first element
			_controlDiv.append('<div align="right"><a href="javascript:wiConsole.clear()">Clear Console</a></div>')
		}

		if (msgList.length >= _maxMessages + 1)
			msgList.eq(1).remove()

		var msgDiv = $('<div class="' + msgClass + '"/>')
		msgDiv.text(msg)
		_controlDiv.append(msgDiv)

		if (typeof exc != 'undefined' && typeof printStackTrace != 'undefined') {
			var trace = printStackTrace({e: exc})

			for (var i in trace) {
				if (msgList.length >= _maxMessages + 1)
					msgList.eq(1).remove()

				msgDiv = $('<div class="wi-console-stacktrace"/>')
				msgDiv.text(trace[i])
				_controlDiv.append(msgDiv)
			}
		}

		_controlDiv.prop('scrollTop', _controlDiv.prop('scrollHeight'))
	}

	// Public

	this.debug = function debug(msg, exc) {
		var msgClass = 'wi-console-debug'

		if (_controlDiv) {
			try {
				log(msgClass, msg, exc)
				return
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (console.debug !== debug)
			console.debug(msg)
	}

	this.info = function info(msg, exc) {
		var msgClass = 'wi-console-info'

		if (_level < 1) {
			_level = 1
			_msgClass = msgClass

			try {
				if (_callback) _callback(_level, msgClass)
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (_controlDiv) {
			try {
				log(msgClass, msg, exc)
				return
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (console.info !== info)
			console.info(msg)
	}

	this.notice = function notice(msg, exc) {
		var msgClass = 'wi-console-notice'

		if (_level < 2) {
			_level = 2
			_msgClass = msgClass

			try {
				if (_callback) _callback(_level, msgClass)
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (_controlDiv) {
			try {
				log(msgClass, msg, exc)
				return
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (console.log !== notice)
			console.log(msg)
	}

	this.warning = function warning(msg, exc) {
		var msgClass = 'wi-console-warning'

		if (_level < 3) {
			_level = 3
			_msgClass = msgClass

			try {
				if (_callback) _callback(_level, msgClass)
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (_controlDiv) {
			try {
				log(msgClass, msg, exc)
				return
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (console.warn !== warning)
			console.warn(msg)
	}

	this.error = function error(msg, exc) {
		var msgClass = 'wi-console-error'

		if (_level < 4) {
			_level = 4
			_msgClass = msgClass

			try {
				if (_callback) _callback(_level, msgClass)
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (_controlDiv) {
			try {
				log(msgClass, msg, exc)
				return
			}
			catch (e) {
				alert("console.js: " + e.message)
			}
		}

		if (console.error !== error)
			console.error(msg)
	}

	this.clear = function() {
		// Clear the console
		_controlDiv.children().remove()
	}

	// Scrolling doesn't work while the console is invisible, so we add an
	// extra method to be called after the console is displayed
	this.scrollToBottom = function() {
		_controlDiv.prop('scrollTop', _controlDiv.prop('scrollHeight'))
	}

	this.resetLevel = function() {
		_level = 0
		_msgClass = 'wi-console-debug'
	}

	this.level = function() {
		return _level
	}

	this.setCallback = function(callback) {
		_callback = callback
		_callback(_level, _msgClass)
	}

	// Load the object into the HTML page
	load(htmlTagId)
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.wiConsole = new WIConsole("#wi-Console")

			// Define console object for old browsers, so we at least
			// might have a chance to see some errors
			if (window.console === undefined)
				window.console = {}

			if (window.console.debug === undefined)
				window.console.debug = wiConsole.debug

			if (window.console.info === undefined)
				window.console.info = wiConsole.info

			if (window.console.log === undefined)
				window.console.log = wiConsole.notice

			if (window.console.warn === undefined)
				window.console.warn = wiConsole.warning

			if (window.console.error === undefined)
				window.console.error = wiConsole.error

			window.onerror = function(errorMsg, url, lineNumber) {
				if (interfaceLoader.debug())
					window.wiConsole.error(errorMsg + ' (' + url + ':' + lineNumber + ')')
				else
					window.wiConsole.error(errorMsg)
			}

			resolve()
		}
		catch (e) {
			alert("console.js: " + e.message)
			reject()
		}
	})
}

