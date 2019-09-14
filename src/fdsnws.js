/*
 * GEOFON WebInterface
 *
 * fdsnws.js module: module for FDSNWS request management.
 *
 * Begun by:
 *  Andres Heinloo, GFZ Potsdam
 *  April 2016
 *
 */

function ajaxErrorMessage(jqXHR, textStatus) {
	if (jqXHR.statusText)
		return jqXHR.statusText
	else
		return textStatus
}

function FDSNWS_Download(controlDiv, db, authToken, data, options, bulk, merge, contentType, filename, cbDownloadFinished) {
	// Private
	var pbarDiv = null
	var saveButton = null
	var handle = null
	var cred = null
	var stopped = true
	var n = 0

	function buildControl() {
		var pbarWrapperDiv = $('<div class="wi-status-full-group-buttons"/>')
		var popupDiv = $('<div class="wi-status-popup"/>').attr('title', data.url)
		var popupBodyDiv = $('<div class="wi-status-popup-group-body"/>')
		var popupTable = $('<table/>')

		pbarDiv = $('<div style="cursor:pointer"/>')
		pbarDiv.append($('<div class="wi-progress-label"/>').text(data.url).append(' - <span class="wi-download-counter">0</span>/' + data.params.length + ' time windows'))
		pbarDiv.progressbar().click(function() { popupDiv.dialog('open') })
		pbarWrapperDiv.append(pbarDiv)

		if (!merge) {
			var pbarButtonDiv = $('<div style="float:right"/>')
			pbarDiv.css('width', '86%').css('float', 'left')
			saveButton = $('<a class="wi-inline" type="button">Save</a>')
			saveButton.button({disabled: true})
			pbarButtonDiv.append(saveButton)
			pbarWrapperDiv.append(pbarButtonDiv)
			pbarWrapperDiv.append('<div style="clear:both"/>')
		}

		popupBodyDiv.append(popupTable)
		popupDiv.append(popupBodyDiv)
		controlDiv.append(pbarWrapperDiv)
		controlDiv.append(popupDiv)

		popupDiv.dialog({ autoOpen: false, modal: true, width: 600 })

		$.each(data.params, function(i, p) {
			var row = $('<tr id="wi-download-status-' + p.id + '"/>')
			row.append($('<td\>').text(p.net))
			row.append($('<td\>').text(p.sta))
			row.append($('<td\>').text(p.loc))
			row.append($('<td\>').text(p.cha))
			row.append($('<td\>').text(p.start))
			row.append($('<td\>').text(p.end))
			row.append($('<td class="wi-download-status-code"\>'))
			row.append($('<td class="wi-download-status-text"\>'))
			popupTable.append(row)
		})
	}

	function store(blob, id) {
		var t = db.transaction(["blobs"], "readwrite")
		t.objectStore("blobs").put(blob, id)
		t.oncomplete = next
		t.onerror = cbDownloadFinished
	}

	function status(id, code, text) {
		var tr = $('#wi-download-status-' + id)
		var tdcode = tr.find('.wi-download-status-code')
		var tdtext = tr.find('.wi-download-status-text')

		// TODO: use classes
		switch (code) {
			case 'OK': tr.css('color', 'green'); break;
			case 'NODATA': tr.css('color', 'orange'); break;
			case 'ERROR': tr.css('color', 'red'); break;
		}

		tdcode.text(code)

		if (text && text != 'error')
			tdtext.text(text)
	}

	function statusBulk(code, text) {
		$.each(data.params, function(i, p) {
			status(p.id, code, text)
		})
	}

	function fetchBulk() {
		var postData = ''

		$.each(Object.keys(options), function(i, k) {
			postData += k + '=' + options[k] + '\n'
		})

		$.each(data.params, function(i, p) {
			postData += p.net + ' ' + p.sta + ' ' + p.loc + ' ' + p.cha + ' ' + p.start + ' ' + p.end + '\n'
		})

		handle = $.ajax({
			method: 'POST',
			url: data.url,
			data: postData,
			contentType: 'text/plain',
			dataType: 'native',
			processData: false,
			xhrFields: {
				responseType: 'arraybuffer'
			}
		})

		handle.done(function(buf, textStatus, jqXHR) {
			handle = null

			if (jqXHR.status != 200)
				buf = new ArrayBuffer(0)

			var blob = new Blob([buf])

			if (blob.size > 0)
				statusBulk('OK')
			else
				statusBulk('NODATA')

			store(blob, data.id)
		})

		handle.fail(function(jqXHR, textStatus) {
			handle = null

			if (!stopped)
				statusBulk('ERROR', ajaxErrorMessage(jqXHR, textStatus))

			next()
		})
	}

	function processBulk() {
		var t = db.transaction(["blobs"])

		t.objectStore("blobs").get(data.id).onsuccess = function(event) {
			var blob = event.target.result

			if (blob == null) {
				fetchBulk()
			}
			else {
				if (blob.size > 0)
					statusBulk('OK')
				else
					statusBulk('NODATA')

				next()
			}
		}

		t.onerror = function(event) {
			fetchBulk(p)
		}
	}

	function doAjax(ajax, url, p, username, password) {
		var q = $.extend({}, p)
		delete q['id']
		delete q['priority']

		handle = ajax({
			method: 'GET',
			url: url + '?' + $.param(q),
			username: username,
			password: password,
			dataType: 'native',
			processData: false,
			xhrFields: {
				responseType: 'arraybuffer'
			}
		})

		handle.done(function(buf, textStatus, jqXHR) {
			handle = null

			if (jqXHR.status != 200)
				buf = new ArrayBuffer(0)

			var blob = new Blob([buf])

			if (blob.size > 0)
				status(p.id, 'OK', blob.size + ' bytes')
			else
				status(p.id, 'NODATA')

			store(blob, p.id)
		})

		handle.fail(function(jqXHR, textStatus) {
			handle = null

			if (jqXHR.status == 401) {
				auth(p)
				return
			}

			if (!stopped)
				status(p.id, 'ERROR', ajaxErrorMessage(jqXHR, textStatus))

			next()
		})
	}

	function auth(p) {
		var url = data.url.replace(/^http:/, 'https:').replace(/query$/, 'auth')

		handle = $.ajax({
			type: 'POST',
			url: url,
			data: authToken,
			contentType: 'text/plain',
			dataType: 'text'
		})

		handle.done(function(data) {
			handle = null
			cred = data
			fetch(p)
		})

		handle.fail(function(jqXHR, textStatus) {
			handle = null

			if (stopped) {
				cbDownloadFinished()
				return
			}

			wiConsole.error("fdsnws.js: " + url + ": " + ajaxErrorMessage(jqXHR, textStatus))
			authToken = null
			cred = null
			fetch(p)
		})
	}

	function wadl(p) {
		var url = data.url.replace(/query$/, 'application.wadl')

		handle = $.ajax({
			type: 'GET',
			url: url,
			dataType: 'xml'
		})

		handle.done(function(xml) {
			handle = null

			if ($(xml).find('resource[path="auth"]').length) {
				auth(p)
				return
			}

			wiConsole.info("fdsnws.js: " + url + ": authentication is not supported")
			authToken = null
			cred = null
			fetch(p)
		})

		handle.fail(function(jqXHR, textStatus) {
			handle = null

			if (stopped) {
				cbDownloadFinished()
				return
			}

			wiConsole.error("fdsnws.js: " + url + ": " + ajaxErrorMessage(jqXHR, textStatus))
			authToken = null
			cred = null
			fetch(p)
		})
	}

	function fetch(p) {
		var url = data.url

		if (authToken && !cred) {
			wadl(p)
		}
		else if (cred) {
			var userpass = cred.split(':')
			url = url.replace(/query$/, 'queryauth')
			doAjax($.ajaxDigest, url, p, userpass[0], userpass[1])
		}
		else {
			doAjax($.ajax, url, p)
		}
	}

	function process(p) {
		var t = db.transaction(["blobs"])

		t.objectStore("blobs").get(p.id).onsuccess = function(event) {
			var blob = event.target.result

			if (blob == null) {
				fetch(p)
			}
			else {
				if (blob.size > 0)
					status(p.id, 'OK', blob.size + ' bytes')
				else
					status(p.id, 'NODATA')

				next()
			}
		}

		t.onerror = function(event) {
			fetch(p)
		}
	}

	function getProduct(cbResult) {
		if (bulk) {
			var t = db.transaction(["blobs"])

			t.objectStore("blobs").get(data.id).onsuccess = function(event) {
				var blob = event.target.result

				if (blob != null)
					cbResult(blob)
				else
					cbResult(new Blob([]))
			}

			t.onerror = function(event) {
				cbResult(new Blob([]))
			}
		}
		else {
			var parts = [];

			(function addPart(i) {
				if (i < n) {
					var t = db.transaction(["blobs"])

					t.objectStore("blobs").get(data.params[i].id).onsuccess = function(event) {
						var blob = event.target.result

						if (blob != null)
							parts.push(blob)

						addPart(i+1)
					}

					t.onerror = function(event) {
						addPart(i+1)
					}
				}
				else {
					cbResult(new Blob(parts))
				}
			})(0)
		}
	}

	function deliverProduct(blob) {
		if (blob.size > 0) {
			var file = new File([blob], filename, { type: contentType })
			var url = URL.createObjectURL(file)
			saveButton.attr('href', url)
			saveButton.attr('download', filename)
			saveButton.button('enable')
		}

		cbDownloadFinished()
	}

	function retrieveProduct() {
		if (saveButton)
			getProduct(deliverProduct)
		else
			cbDownloadFinished()
	}

	function next() {
		if (stopped) {
			retrieveProduct()
			return
		}

		pbarDiv.progressbar('value', 100 * n / data.params.length)
		pbarDiv.find('.wi-download-counter').text(n)

		if (n < data.params.length) {
			if (bulk) {
				processBulk()
				n += data.params.length
			}
			else {
				process(data.params[n])
				++n
			}
		}
		else {
			retrieveProduct()
		}
	}

	function start() {
		if (saveButton)
			saveButton.button('disable')

		stopped = false
		n = 0
		next()
	}

	function stop() {
		stopped = true

		if (handle != null)
			handle.abort()
	}

	buildControl()

	// Public interface
	this.start = start
	this.stop = stop
	this.getProduct = getProduct
}

function FDSNWS_Request(controlDiv, db, authToken, filename) {
	// Private
	var downloadsDiv = null
	var stopButton = null
	var startButton = null
	var saveButton = null
	var deleteButton = null
	var data = null
	var downloads = []
	var finished = 0

	function buildControl() {
		var buttonsDiv = $('<div class="wi-status-full-group-buttons">')
		var filenameDiv = $('<div class="wi-status-full-group-buttons"/>').text(filename)

		startButton = $('<input class="wi-inline" type="button" value="Start"/>')
		startButton.button({disabled: true}).click(function() { start() })

		stopButton = $('<input class="wi-inline" type="button" value="Stop"/>')
		stopButton.button({disabled: true}).click(function() { stop() })

		saveButton = $('<a class="wi-inline" type="button">Save</a>')
		saveButton.button({disabled: true})

		deleteButton = $('<input class="wi-inline" type="button" value="Delete"/>')
		deleteButton.button({disabled: true}).click(function() { purge() })

		buttonsDiv.append(startButton)
		buttonsDiv.append(stopButton)
		buttonsDiv.append(saveButton)
		buttonsDiv.append(deleteButton)

		downloadsDiv = $('<div>Routing in progress...</div>')

		controlDiv.append(buttonsDiv)
		controlDiv.append(filenameDiv)
		controlDiv.append(downloadsDiv)
	}

	function deliverProduct(blobs) {
		var file = new File(blobs, data.filename, { type: data.contentType })

		if (file.size > 0) {
			var url = URL.createObjectURL(file)
			saveButton.attr('href', url)
			saveButton.attr('download', data.filename)
			saveButton.button('enable')
		}

		startButton.button('enable')
		stopButton.button('disable')
		deleteButton.button('enable')
	}

	function retrieveProduct() {
		var blobs = []

		$.each(downloads, function(i, dl) {
			dl.getProduct(function(blob) {
				blobs.push(blob)

				if (blobs.length == downloads.length)
					deliverProduct(blobs)
			})
		})
	}

	function cbDownloadFinished() {
		if (++finished < data.length)
			return

		if (data.merge) {
			retrieveProduct()
		}
		else {
			startButton.button('enable')
			stopButton.button('disable')
			saveButton.button('disable')
			deleteButton.button('enable')
		}
	}

	function revokeObjectUrls() {
		controlDiv.find('a[type=button]').each(function(i, button) {
			var url = $(button).attr('href')

			if (url) {
				URL.revokeObjectURL(url)
				$(button).removeAttr('href')
			}
		})
	}

	function start() {
		startButton.button('disable')
		stopButton.button('enable')
		saveButton.button('disable')
		deleteButton.button('disable')

		revokeObjectUrls()

		if (downloadsDiv.is(':empty')) {
			$.each(data, function(i, d) {
				var dlDiv = $('<div/>')
				var dot = data.filename.lastIndexOf('.')
				var filename = data.filename.slice(0, dot) + '_' + i + data.filename.slice(dot)
				var dl = new FDSNWS_Download(dlDiv, db, authToken, d, data.options, data.bulk, data.merge, data.contentType, filename, cbDownloadFinished)
				downloadsDiv.append(dlDiv)
				downloads.push(dl)
			})
		}

		finished = 0

		$.each(downloads, function(i, dl) {
			dl.start()
		})
	}

	function stop() {
		$.each(downloads, function(i, dl) {
			dl.stop()
		})
	}

	function purge() {
		revokeObjectUrls()
		controlDiv.remove()

		var t = db.transaction(["blobs"], "readwrite")

		$.each(data, function(i, d) {
			t.objectStore("blobs").delete(d.id)

			$.each(d.params, function(i, p) {
				t.objectStore("blobs").delete(p.id)
			})
		})

		t.oncomplete = function(event) {
			var t = db.transaction(["requests"], "readwrite")
			t.objectStore("requests").delete(data.id)
		}
	}

	function create() {
		var t = db.transaction(["blobs"], "readwrite")

		$.each(data, function(i, d) {
			t.objectStore("blobs").add(null).onsuccess = function(event) {
				d.id = event.target.result
			}

			$.each(d.params, function(i, p) {
				t.objectStore("blobs").add(null).onsuccess = function(event) {
					p.id = event.target.result
				}
			})
		})

		t.oncomplete = function(event) {
			var t = db.transaction(["requests"], "readwrite")

			t.objectStore("requests").add(data).onsuccess = function(event) {
				data.id = event.target.result
			}

			t.oncomplete = start
		}
	}

	function load(d) {
		data = d
		downloadsDiv.empty()
	}

	buildControl()

	// Public interface
	this.start = start
	this.stop = stop
	this.purge = purge
	this.create = create
	this.load = load
}

function FDSNWS_Control(controlDiv) {
	// Private
	var statusListDiv = null
	var callback = null
	var db = null
	var authToken = null
	var authInfo = null

	function buildControl() {
		statusListDiv = $('<div class="wi-status-list-body"/>')
		controlDiv.append(statusListDiv)
	}

	function createObjectStores(db) {
		db.createObjectStore("user")
		db.createObjectStore("requests", { autoIncrement: true, keyPath: 'id' })
		db.createObjectStore("blobs", { autoIncrement: true })
	}

	function openDatabase() {
		return new Promise(function(resolve, reject) {
			if (!window.indexedDB) {
				wiConsole.error("fdsnws.js: IndexedDB is not supported by browser")
				reject()
				return
			}

			var dbOpenReq
			var dbVersion = 1

			try {
				dbOpenReq = window.indexedDB.open("webdc", { version: dbVersion, storage: "persistent" })
			}
			catch (e) {
				if (e instanceof TypeError) {
					try {
						dbOpenReq = window.indexedDB.open("webdc", dbVersion)
					}
					catch (e) {
						reject(e)
						return
					}
				}
				else {
					reject(e)
					return
				}
			}

			dbOpenReq.onsuccess = function(event) {
				db = event.target.result

				db.onerror = function(event) {
					wiConsole.error("fdsnws.js: IndexedDB error (errorCode=" + event.target.errorCode + ")")
				}

				// For browsers not supporting 'onupgradeneeded'
				if (db.setVersion) {
					if (db.version != dbVersion) {
						db.setVersion(dbVersion).onsuccess = function() {
							try {
								createObjectStore(db)
							}
							catch (e) {
								reject(e)
							}
						}
					}
				}

				resolve()
			}

			dbOpenReq.onupgradeneeded = function(event) {
				try {
					createObjectStores(event.target.result)
				}
				catch (e) {
					reject(e)
				}
			}

			dbOpenReq.onerror = function(event) {
				wiConsole.error("fdsnws.js: access to database denied")
				reject()
			}
		})
	}

	function loadAuthToken() {
		return new Promise(function(resolve, reject) {
			var t = db.transaction(["user"])

			t.objectStore("user").get("auth").onsuccess = function(event) {
				if (event.target.result) {
					setAuthToken(event.target.result)
				}
			}

			t.oncomplete = resolve
			t.onerror = reject
		})
	}

	function loadRequests() {
		return new Promise(function(resolve, reject) {
			var t = db.transaction(["requests"])

			t.objectStore("requests").openCursor().onsuccess = function(event) {
				var cursor = event.target.result

				if (cursor) {
					var reqDiv = $('<div class="wi-status-full-group"/>')
					var data = cursor.value
					var req = new FDSNWS_Request(reqDiv, db, authToken, data.filename)
					statusListDiv.append(reqDiv)
					req.load(data)
					req.start()
					cursor.continue()
				}
			}

			t.oncomplete = resolve
			t.onerror = reject
		})
	}

	function init() {
		return openDatabase().then(loadAuthToken).then(loadRequests)
	}

	function submitRequest(param) {
		var reqDiv = $('<div class="wi-status-full-group"/>')
		var req = new FDSNWS_Request(reqDiv, db, authToken, param.filename)
		statusListDiv.append(reqDiv)
		callback()

		var timewindows = JSON.parse(param.timewindows)

		// If using a routing service
		if (routing) {
			var postData = 'service=' + param.service + '\nformat=json\n'

			$.each(timewindows, function(i, item) {
				var start = item[0]
				var end = item[1]
				var net = item[2]
				var sta = item[3]
				var cha = item[4]
				var loc = item[5]

				if (loc == '')
					loc = '--'

				postData += net + ' ' + sta + ' ' + loc + ' ' + cha + ' ' + start + ' ' + end + '\n'
			})

			$.ajax({
				type: 'POST',
				url: routerURL,
				data: postData,
				contentType: 'text/plain',
				dataType: 'json',
				success: function(reqData) {
					if (!reqData) {
						wiConsole.error("fdsnws.js: no routes received")
						reqDiv.remove()
						return
					}

					reqData.options = param.options
					reqData.bulk = param.bulk
					reqData.merge = param.merge
					reqData.filename = param.filename
					reqData.contentType = param.contentType
					req.load(reqData)
					req.create()
				},
				error: function(jqXHR, textStatus) {
					wiConsole.error("fdsnws.js: routing failed: " + ajaxErrorMessage(jqXHR, textStatus))
					reqDiv.remove()
				}
			})
		// If using a local FDSNWS without routing
		} else {
			var reqData = [{
				url: fdsnwsURL + '/' + param.service + '/1/' + ((param.service == 'dataselect')? 'queryauth': 'query'),
				name: param.service,
				params: []
			}]

			$.each(timewindows, function(i, item) {
				var start = item[0]
				var end = item[1]
				var net = item[2]
				var sta = item[3]
				var cha = item[4]
				var loc = item[5]

				if (loc == '')
					loc = '--'

				reqData[0]['params'].push({ net: net, sta: sta, loc: loc, cha: cha, start: start, end: end })
			})

			reqData.options = param.options
			reqData.bulk = param.bulk
			reqData.merge = true
			reqData.filename = param.filename
			reqData.contentType = param.contentType
			req.load(reqData)
			req.create()
		}
	}

	function setCallback(cb) {
		callback = cb
	}

	function setAuthToken(tok) {
		if (!tok) {
			var t = db.transaction(["user"], "readwrite")
			t.objectStore("user").delete("auth")
			authToken = null
			authInfo = null
			return
		}

		try {
			var text = openpgp.message.readArmored(tok).getText()

			if (!text) {
				try {
					text = openpgp.cleartext.readArmored(tok).getText()
				}
				catch(e) {
					wiConsole.error("fdsnws.js: invalid auth token: No auth data")
					return
				}
			}

			var auth = $.parseJSON(text)
			var t = db.transaction(["user"], "readwrite")
			t.objectStore("user").put(tok, "auth")
			authToken = tok
			authInfo = { userId: auth.mail, validUntil: new Date(auth.valid_until) }
		}
		catch(e) {
			wiConsole.error("fdsnws.js: invalid auth token: " + e.message)
		}
	}

	function getAuthInfo() {
		return authInfo
	}

	buildControl()

	// Get routing configuration
	var routing = (configurationProxy.value('fdsnws.routing', 'true') == 'true')
	var routerURL = configurationProxy.value('fdsnws.routerURL', '/eidaws/routing/1/query')
	var fdsnwsURL = configurationProxy.value('fdsnws.fdsnwsURL', '/fdsnws').replace(/\/+$/, '')

	// Public interface
	this.init = init
	this.submitRequest = submitRequest
	this.setCallback = setCallback
	this.setAuthToken = setAuthToken
	this.getAuthInfo = getAuthInfo
}

function FDSNWS_Dummy() {
	// Public interface
	this.setCallback = function() {}
	this.setAuthToken = function() {}
	this.getAuthInfo = function() {}
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			var div = $('#wi-FDSNWS-Control')

			if (!div.length) {
				window.wiFDSNWS_Control = new FDSNWS_Dummy()
				resolve()
				return
			}

			var fdsnws = new FDSNWS_Control(div)

			wiConsole.info("fdsnws.js: initializing")
			fdsnws.init()
			.then(function() {
				wiConsole.info("fdsnws.js: init successful")
				window.wiFDSNWS_Control = fdsnws
				resolve()
			})
			.catch(function(e) {
				if (e instanceof Error)
					wiConsole.error("fdsnws.js: " + e.message, e)

				wiConsole.info("fdsnws.js: init failed")
				div.parent().remove()
				window.wiFDSNWS_Control = new FDSNWS_Dummy()
				resolve()
			})

		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("fdsnws.js: " + e.message)

			wiConsole.error("fdsnws.js: " + e.message, e)
			reject()
		}
	})
}

