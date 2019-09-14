/*
 * WebDC 3
 *
 * Copyright (C) 2013-2016 Helmholtz-Zentrum Potsdam - Deutsches GeoForschungsZentrum GFZ
 *
 */

import initConsole from './console'
import initConfig from './config'
import initMapping from './mapping'
import initService from './service'
import initFdsnws from './fdsnws'
import initRequest from './request'
import initEvents from './events'
import initStation from './station'
import initSubmit from './submit'
import initReview from './review'
import initInterface from './interface'

var VERSION = "1.2 (2019.191)"

window.WIError = function(message) {
	this.name = undefined // omit exception name on the console
	this.message = message
	this.toString = function() { return this.message }
}

window.WIError.prototype = new Error

// The modules use interfaceLoader.debug(), so add this for compatibility.
window.interfaceLoader = new function() {
	this.debug = function() {
		return (typeof eidaDebug != 'undefined') ? eidaDebug : true
	}
}

$(document).ready(function() {
	initConsole()
	.then(function() {
		wiConsole.info("Loading webinterface v" + VERSION + "...")
	})
	.then(initConfig)
	.then(initMapping)
	.then(initService)
	.then(initFdsnws)
	.then(initRequest)
	.then(initEvents)
	.then(initStation)
	.then(initSubmit)
	.then(initReview)
	.then(initInterface)
	.then(function() {
		wiConsole.info("Ready.")
	})
	.catch(function() {
		wiConsole.info("Aborted.")
	})
})

