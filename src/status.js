/*
 * GEOFON WebInterface
 *
 * status.js module: set up a control module for request management.
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, Andres Heinloo, GFZ Potsdam
 *  June/July 2013
 *
 */

/*
 * Implementation of the wiStatusQueryControl
 */
function WIStatusQueryControl(htmlTagId) {
	// Private
	var _controlDiv = null
	var _downloadButton = null
	var _purgeButton = null
	var _queryButton = null
	var _urls = null
	var _jdownloader = false
	var _node = {}

	function clear() {
		_downloadButton.button('disable')
		_purgeButton.button('disable')
		_urls.val('')
		_jdownloader = false

		$.each(_node, function(dcid, node) { node.req_ids = [] })
	}

	function purge() {
		var user = _controlDiv.find("#wi-User").val()

		if (!confirm("Delete all requests?"))
			return

		$.each(_node, function(dcid, node) {
			$.each(node.req_ids, function(i, req_id) {
				wiService.request.purge(null, null, false, dcid, user, req_id)
			})
		})

		clear()
		wiStatusFullControl.clear()
		wiStatusListControl.clear(false, false)
	}

	function query() {
		clear()
		wiStatusFullControl.clear()

		$.getScript('http://127.0.0.1:9666/jdcheck.js', function() {
			wiConsole.info("jDownloader detected")
			_jdownloader = true

			if (_urls.val())
				_downloadButton.button('enable')
		})

		var statusLimit = configurationProxy.value('request.statusLimit', 100)
		var dcidlist = $.map(_node, function(v, k) { return v.busy? undefined: k })

		if (dcidlist.length) {
			wiConsole.info("Fetching status from " + dcidlist.join(', '))

			var user = _controlDiv.find("#wi-User").val()
			wiStatusFullControl.setUser(user)

			$.each(dcidlist, function(i, dcid) {
				_node[dcid].busy = true
				wiService.request.status(addRequestsFn(dcid), function(jqxhr) {
					if (jqxhr.status == 500)
						var err = jqxhr.statusText
					else
						var err = jqxhr.responseText

					wiConsole.error("Error getting status from " + dcid + ": " + err)
					_node[dcid].busy = false
				}, true, dcid, user, "ALL", 0, statusLimit + 1)
			})
		}
	}

	function buildControl() {
		var html = '<div class="wi-control-item">'
		html += '<div class="wi-spacer">Your email address:</div>'
		html += '<input type="text" class="spacer" id="wi-User"/><br/>'
		html += '<input type="checkbox" id="wi-UserKeep"> Remember me?'
		html += '</div>'

		_controlDiv.append(html)

		var downloadDiv = $('<div class="wi-control-item-last" style="float: left"/>')
		var downloadForm = $('<form action="http://127.0.0.1:9666/flash/add" target="downloadFrame" method="post"/>')

		_downloadButton = $('<input type="submit" name="submit" title="Add download links to a running jDownloader instance (http://jdownloader.org/)" value="Download All"/>')
		_downloadButton.button({disabled: true})

		_urls = $('<input type="hidden" name="urls"/>')

		downloadForm.append(_downloadButton)
		downloadForm.append(_urls)
		downloadDiv.append(downloadForm)

		var buttonsDiv = $('<div class="wi-control-item-last" style="float: right"/>')

		_purgeButton = $('<input class="wi-inline-full" type="button" value="Delete All"/>')
		_purgeButton.button({disabled: true}).click(purge)

		_queryButton = $('<input class="wi-inline-full" type="button" value="Get Status"/>')
		_queryButton.button({disabled: true}).click(query)

		buttonsDiv.append(_purgeButton)
		buttonsDiv.append(_queryButton)

		var userInput = _controlDiv.find("#wi-User")
		var userKeepInput = _controlDiv.find("#wi-UserKeep")
		var savedUser = $.cookie("scUser")

		if (savedUser) {
			userInput.val(savedUser)
			userKeepInput.prop('checked', true)
		}

		userInput.change(function() {
			if (!userKeepInput.prop('checked'))
				return

			var user = $(this).val()

			if (user) $.cookie('scUser', user, { expires: 30 })
			else $.removeCookie('scUser')
		})

		userKeepInput.change(function() {
			if ($(this).prop('checked')) userInput.change()
			else $.removeCookie('scUser')
		})

		// trigger cookie refresh
		userInput.change()

		_controlDiv.append(downloadDiv)
		_controlDiv.append(buttonsDiv)
		_controlDiv.append('<div style="clear: both"/>')
	}

	function load(htmlTagId) {
		var control = $(htmlTagId)

		// If we don't find one div ...
		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("status.js: Cannot find a div with class '" + htmlTagId + "'")
			return
		}

		// otherwise finish load ...
		_controlDiv = control

		// build the interface
		buildControl()
	}

	function jdURL(dcid, user, req_id, vol_id) {
		return window.location.protocol + '//' + window.location.host + wiService.request.downloadURL(dcid, user, req_id, vol_id) + '.jdeatme'
	}

	function addRequestsFn(dcid) {
		var user = _controlDiv.find("#wi-User").val()

		return function(data) {
			wiStatusFullControl.addRequests(dcid, data)

			$.each(data, function(i, req) {
				_node[dcid].req_ids.push(req.id)

				if (i == 0) _purgeButton.button('enable')

				$.each(req.volume, function(i, vol) {
					if (vol.status == "OK" || vol.status == "WARNING" || vol.status == "PROCESSING") {
						if (!_urls.val()) {
							_urls.val(jdURL(dcid, user, req.id, vol.id))

							if (_jdownloader) _downloadButton.button('enable')
						}
						else {
							_urls.val(_urls.val() + '\r\n' + jdURL(dcid, user, req.id, vol.id))
						}
					}
				})
			})

			wiConsole.info("Got status from " + dcid)
			_node[dcid].busy = false
		}
	}

	function nodename(dcid) {
		return _node[dcid].name
	}

	function checkCookie() {
		// Check cookie again when the control is brought to view
		var userInput = _controlDiv.find("#wi-User")
		var userKeepInput = _controlDiv.find("#wi-UserKeep")
		var savedUser = $.cookie("scUser")

		if (savedUser) {
			userInput.val(savedUser)
			userKeepInput.prop('checked', true)
		}
	}

	// Public
	this.clear = clear
	this.nodename = nodename
	this.checkCookie = checkCookie

	// Load the object into the HTML page
	load(htmlTagId)

	wiService.request.nodes(function(data) {
		$.each(data, function(i, nodeinfo) {
			_node[nodeinfo[0]] = {
				name: nodeinfo[1],
				busy: false,
				req_ids: []
			}
		})

		if (_queryButton) _queryButton.button('enable')
	}, null, true)
}

/*
 * Base class
 */
function WIStatusBase(htmlTagId) {
	function formatEncrypted(val) {
		if (val)
			return '<span class="wi-request-encrypted">Yes</span>'
		else
			return 'No'
	}

	function formatStatus(val) {
		var statusClass = 'wi-request-status-other'

		if (val == "OK")
			statusClass = 'wi-request-status-ok'

		else if (val == "WARNING")
			statusClass = 'wi-request-status-warn'

		return '<span class="' + statusClass + '">' + val + '</span>'
	}

	function formatArgs(val) {
		return $.map(val, function(v, k) { return k + '=' + v }).join(' ')
	}

	function formatDate(val) {
		var date = new Date(val)

		return [ date.getUTCFullYear(),
			 date.getUTCMonth()+1,
			 date.getUTCDate(),
			 date.getUTCHours(),
			 date.getUTCMinutes(),
			 date.getUTCSeconds() ].join()
	}

	function formatLine(val) {
		var start = formatDate(val[0])
		var end = formatDate(val[1])
		var nscl = $.map(val.slice(2,6), function(v, k) { if (!v) return '.'; else return v })
		var constraints = formatArgs(val[6])

		return [ start, end, nscl[0], nscl[1], nscl[2], nscl[3], constraints ].join(' ')
	}

	function renderVolume(dcid, req, vol) {
		var self = this
		var html = '<div class="wi-request-volume">' // open volume div

		html += '<div class="wi-request-volume-header">' // open volume header div

		if (vol.status == "OK" || vol.status == "WARNING")
			html += '<a href="' + wiService.request.downloadURL(dcid, self.user, req.id, vol.id) + '" class="wi-request-volume-download" target="wi-DownloadFrame">Download Volume</a>'

		html += '&nbsp;</div>' // close volume header div

		html += '<div class="wi-request-volume-info">' // open volume info div
		html += '<b>Volume ID</b>: ' + vol.id + ', <b>Status</b>: ' + formatStatus(vol.status) + ', <b>Encrypted</b>: ' + formatEncrypted(vol.encrypted) + ', <b>Size</b>: ' + vol.size + ', <b>Info</b>: ' + vol.message
		html += '</div>' // close volume info div

		html += '</div>' // close volume div

		var volumeDiv = $(html)

		// might use css (background image) for nicer +/- sign
		var linesCollapsedDiv = $('<div class="wi-request-volume-content" style="cursor: pointer; display: block"><b>[+] ' + vol.line.length + ' lines in this volume</b></div>')
		var linesExpandedDiv = $('<div class="wi-request-volume-content" style="cursor: pointer; display: none"><b>[-] ' + vol.line.length + ' lines in this volume</b></div>')

		$.each(vol.line, function(i, rqln) {
			html = '<div class="wi-request-line">' // open line div
			html += '&nbsp;&nbsp;&nbsp;&nbsp;' + formatLine(rqln.content) + '<br/>'
			html += '&nbsp;&nbsp;&nbsp;&nbsp;' + 'Status: ' + formatStatus(rqln.status) + ', Size: ' + rqln.size + ', Info: ' + rqln.message + '<br/>'
			html += '</div>' // close line div
			linesExpandedDiv.append(html)
		})

		volumeDiv.append(linesCollapsedDiv)
		volumeDiv.append(linesExpandedDiv)

		var toggle = function() {
			$.each([linesCollapsedDiv, linesExpandedDiv], function(i, div) {
				if (div.css('display') == 'none') div.css('display', 'block')
				else div.css('display', 'none')
			})
		}

		linesCollapsedDiv.click(toggle)
		linesExpandedDiv.click(toggle)

		return volumeDiv
	}

	function renderRequest(dcid, req) {
		var self = this
		var req_status

		if (req.error)
			req_status = "ERROR"
		else if (req.ready)
			req_status = "READY"
		else
			req_status = "PROCESSING"

		var canDownloadRequest = true
		var volumesToDownload = 0

		$.each(req.volume, function(i, vol) {
			 if (vol.encrypted && vol.size > 0)
				 canDownloadRequest = false

			 if (vol.status == "OK" && vol.size > 0)
				 volumesToDownload += 1
		})

		if (volumesToDownload == 1)
			 canDownloadRequest = true

		var html = '<div class="wi-request">' // open request div

		html += '<div class="wi-request-datacenter">' + wiStatusQueryControl.nodename(dcid) + '</div>'
		html += '<div class="wi-request-header">' // open request header div

		//if (req.ready && !req.error && req.size>0 && canDownloadRequest)
		//	html += '<a href="' + wiService.request.downloadURL(dcid, self.user, req.id) + '" class="wi-request-download" target="wi-DownloadFrame">Download Request</a>'

		html += '&nbsp;</div>' // close request header div

		html += '<div class="wi-request-info">' // open request info div
		html += '<b>Request ID</b>: ' + req.id + ', <b>Type</b>: ' + req.type + ', <b>Encrypted</b>: ' + formatEncrypted(req.encrypted) + ', <b>Args</b>: ' + formatArgs(req.args) + '<br/>'
		html += '<b>Description</b>: ' + (req.description? req.description: '') + '<br/>'
		html += '<b>Status</b>: ' + req_status + ', <b>Size</b>: ' + req.size + ', <b>Info</b>: ' + req.message
		html += '</div>' // close request info div

		html += '</div>' // close request div

		var requestDiv = $(html)
		requestDiv.data({dcid: dcid, req_id: req.id, ready: req.ready})

		$.each(req.volume, function(i, vol) {
			requestDiv.append(self.renderVolume(dcid, req, vol))
		})

		return requestDiv
	}

	function resubmitDoneFn(mode) {
		var self = this

		return function(data) {
			if (!data.success.length && !data.failure.length) {
				wiConsole.notice("No applicable request lines found")
				return
			}
			else if (!data.success.length) {
				wiConsole.notice("No more routes found")
				return
			}
			else {
				wiConsole.info("Sent " + data.success.length + " request" + ((data.success.length != 1)? "s": ""))
			}

			$.each(data.success, function(i, req) {
				wiService.request.status(self.addRequestsFn(req.dcid), null, true, req.dcid, self.user, req.id)
			})
		}
	}

	function resubmitButtonFn(requestListDiv, mode) {
		var self = this

		return function() {
			var uuid = requestListDiv.parent().attr('id')
			var idList = []

			requestListDiv.children().each(function(i, e) {
				var data = $(e).data()
				idList.push([data.dcid, data.req_id])
			})

			wiService.request.resubmit(self.resubmitDoneFn(mode), null, true, self.user, uuid, mode, JSON.stringify(idList))

			// no more in sync, deactivate download and delete buttons
			wiStatusQueryControl.clear()
		}
	}

	function deleteButtonFn(requestListDiv) {
		var self = this

		return function() {
			var uuid = requestListDiv.parent().attr('id')

			requestListDiv.children().each(function(i, e) {
				var data = $(e).data()
				wiService.request.purge(null, null, false, data.dcid, self.user, data.req_id)
			})

			// remove parent request group
			requestListDiv.parent().remove()

			// remove status item from the list as well
			wiStatusListControl.removeStatusItem(uuid)

			// no more in sync, deactivate download and delete buttons
			wiStatusQueryControl.clear()
		}
	}

	function refreshButtonFn(requestListDiv) {
		var self = this

		return function() {
			requestListDiv.children().each(function(i, e) {
				var data = $(e).data()

				// if (!data.ready)
					wiService.request.status(self.addRequestsFn(data.dcid), null, true, data.dcid, self.user, data.req_id)
			})

			// no more in sync, deactivate download and delete buttons
			wiStatusQueryControl.clear()
		}
	}

	function addEncryptionWarning(div) {
		var html = ''

		html += '<div class="wi-warning-encryption">';
		html += 'Attention: Some of your requests are encrypted. Please consult the <a href="help.html">help page</a> on how to decrypt encrypted data.';
		html += '</div>';

		div.append(html)
	}

	function addOneRequest(dcid, req, msgsDiv, groupsDiv, groupClass) {
		var self = this
		var groupDiv = groupsDiv.children('#' + req.uuid)

		if (req.encrypted && !msgsDiv.children(".wi-warning-encryption").length)
			addEncryptionWarning(msgsDiv)

		if (!groupDiv.length) {
			groupDiv = $('<div class="' + groupClass + '" id="' + req.uuid + '">')

			var requestListDiv = $('<div class="' + groupClass + '-body">')
			requestListDiv.append(self.renderRequest(dcid, req))

			var rerouteButton = $('<input class="wi-inline" type="button" value="Reroute"/>')
			rerouteButton.button().click(self.resubmitButtonFn(requestListDiv, "reroute"))

			var retryButton = $('<input class="wi-inline" type="button" value="Retry"/>')
			retryButton.button().click(self.resubmitButtonFn(requestListDiv, "retry"))

			var resendButton = $('<input class="wi-inline" type="button" value="Resend"/>')
			resendButton.button().click(self.resubmitButtonFn(requestListDiv, "resend"))

			var deleteButton = $('<input class="wi-inline" type="button" value="Delete"/>')
			deleteButton.button().click(self.deleteButtonFn(requestListDiv))

			var refreshButton = $('<input class="wi-inline" type="button" value="Refresh"/>')
			refreshButton.button().click(self.refreshButtonFn(requestListDiv))

			var buttonsDiv = $('<div class="' + groupClass + '-buttons">')
			buttonsDiv.append(rerouteButton)
			buttonsDiv.append(retryButton)
			buttonsDiv.append(resendButton)
			buttonsDiv.append(deleteButton)
			buttonsDiv.append(refreshButton)

			groupDiv.append(buttonsDiv)
			groupDiv.append(requestListDiv)

			groupsDiv.prepend(groupDiv)
		}
		else {
			var requestListDiv = groupDiv.children('.' + groupClass + '-body')
			var newRequest = true

			requestListDiv.children().each(function(i, e) {
				var data = $(e).data()

				if (data.req_id == req.id && data.dcid == dcid) {
					$(e).replaceWith(self.renderRequest(dcid, req))
					newRequest = false
					return false
				}
			})

			if (newRequest)
				requestListDiv.append(self.renderRequest(dcid, req))
		}
	}

	function addRequestsFn(dcid) {
		var self = this

		return function(data) {
			self.addRequests(dcid, data)
		}
	}

	function setUser(user) {
		var self = this

		if (user != self.user) {
			self.clear(true)
			self.user = user
		}
	}

	this.user = null
	this.formatLine = formatLine
	this.renderVolume = renderVolume
	this.renderRequest = renderRequest
	this.resubmitDoneFn = resubmitDoneFn
	this.resubmitButtonFn = resubmitButtonFn
	this.deleteButtonFn = deleteButtonFn
	this.refreshButtonFn = refreshButtonFn
	this.addOneRequest = addOneRequest
	this.addRequests = undefined // pure virtual
	this.addRequestsFn = addRequestsFn
	this.clear = undefined // pure virtual
	this.setUser = setUser
}

/*
 * Implementation of the wiStatusFullControl
 */
function WIStatusFullControl(htmlTagId) {
	// Private
	var _controlDiv = null
	var _msgsDiv = null
	var _groupsDiv = null
	var _groupClass = 'wi-status-full-group'

	function buildControl() {
		_msgsDiv = $('<div class="wi-status-full-msgs"/>')
		_groupsDiv = $('<div class="wi-status-full-groups"/>')

		_controlDiv.append(_msgsDiv)
		_controlDiv.append(_groupsDiv)
	}

	function load(htmlTagId) {
		var control = $(htmlTagId)

		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("status.js: Cannot find a div with class '" + htmlTagId + "'")
			return
		}

		// Save the main control div
		_controlDiv = control

		// Build
		buildControl()
	}

	function addRequests(dcid, data) {
		if (!_controlDiv) return

		var self = this

		var statusLimit = configurationProxy.value('request.statusLimit', 100)

		if (data.length > statusLimit) {
			var html = ''

			html += '<div class="wi-warning-encryption">';
			html += 'Attention: The number of your requests at datacenter ' + dcid + ' exceeds configured limit (' + statusLimit + '). Please delete requests after you have downloaded the data.';
			html += '</div>';

			_msgsDiv.append(html)
		}

		$.each(data, function(i, req) {
			if (i == 0) _controlDiv.css('display', 'block')

			if (i < statusLimit) self.addOneRequest(dcid, req, _msgsDiv, _groupsDiv, _groupClass)
		})
	}

	function clear(force) {
		if (!_controlDiv) return

		_controlDiv.css('display', 'none')

		_msgsDiv.empty()
		_groupsDiv.empty()
	}

	// Public
	this.addRequests = addRequests
	this.clear = clear

	// Load the object into the HTML page
	load(htmlTagId)
}

WIStatusFullControl.prototype = new WIStatusBase

/*
 * Implementation of the wiStatusListControl
 */
function WIStatusListControl(htmlTagId) {
	// Private
	var _controlDiv = null
	var _buttonsDiv = null
	var _statusListDiv = null
	var _popupDiv = null
	var _callback = null
	var _groupClass = 'wi-status-popup-group'

	function buildControl() {
		_buttonsDiv = $('<div class="wi-status-list-buttons"/>')
		_statusListDiv = $('<div class="wi-status-list-body"/>')

		_controlDiv.append(_buttonsDiv)
		_controlDiv.append(_statusListDiv)

		_popupDiv = $('<div class="wi-status-popup"/>')

		_popupDiv.dialog({
			autoOpen: false,
			modal: true,
			width: 650
		})

		_popupDiv.on('close', function() {
			$(this).children('.wi-status-popup-display').remove()
		})
	}

	function load(htmlTagId) {
		var control = $(htmlTagId)

		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("status.js: Cannot find a div with class '" + htmlTagId + "'")
			return
		}

		// Save the main control div
		_controlDiv = control

		// Build
		buildControl()
	}

	function newDisplay() {
		var displayDiv = $('<div class="wi-status-popup-display"/>')
		var msgsDiv = $('<div class="wi-status-popup-msgs"/>')
		var groupsDiv = $('<div class="wi-status-popup-groups"/>')

		displayDiv.append(msgsDiv)
		displayDiv.append(groupsDiv)

		// There must be no more than one display, but we use first(), just in case.
		var prevDisplayDiv = _popupDiv.children('.wi-status-popup-display').first()

		if (prevDisplayDiv.length)
			prevDisplayDiv.replaceWith(displayDiv)
		else
			_popupDiv.append(displayDiv)

		return {
			main: displayDiv,
			msgs: msgsDiv,
			groups: groupsDiv
		}
	}

	function resubmitFailFn(statusDiv, mode, uuid) {
		var self = this

		return function(jqxhr) {
			if (jqxhr.status == 500)
				var err = jqxhr.statusText
			else
				var err = jqxhr.responseText

			wiConsole.error("Failed to " + mode + " request " + uuid + ": " + err)

			if (mode == 'reroute' || mode == 'retry')
				// restore the status div to previous state
				self.updateStatusDiv(statusDiv, statusDiv.data())
			else
				self.removeStatusDiv(statusDiv)
		}
	}

	function resubmitDoneFn(statusDiv, mode) {
		var self = this

		return function(data) {
			if (!data.success.length && !data.failure.length)
				wiConsole.notice("No applicable request lines found")
			else if (!data.success.length)
				wiConsole.notice("No more routes found")
			else
				wiConsole.info("Sent " + data.success.length + " request" + ((data.success.length != 1)? "s": ""))

			if (mode == 'reroute' || mode == 'retry') {
				var prevData = statusDiv.data()
				$.merge(data.success, prevData.success)
				data.failure = prevData.failure
			}

			self.updateStatusDiv(statusDiv, data)
		}
	}

	function resubmitButtonFn(requestListDiv, mode) {
		var self = this

		return function() {
			var uuid = requestListDiv.parent().attr('id')
			var statusDiv = _statusListDiv.children('#status-' + uuid)

			if (mode == 'resend') {
				var description = statusDiv.children('.wi-status-item-description').first().text()
				var newStatusDiv = self.addStatusDiv(description)
			}
			else {
				var newStatusDiv = self.updateStatusDiv(statusDiv, null)
			}

			var idList = []

			requestListDiv.children().each(function(i, e) {
				var data = $(e).data()
				idList.push([data.dcid, data.req_id])
			})

			wiService.request.resubmit(self.resubmitDoneFn(newStatusDiv, mode), self.resubmitFailFn(newStatusDiv, mode, uuid), false, self.user, uuid, mode, JSON.stringify(idList))

			// no more in sync, deactivate download and delete buttons
			wiStatusQueryControl.clear()

			_popupDiv.dialog('close')
		}
	}

	function deleteButtonFn(requestListDiv) {
		var self = this

		return function() {
			var uuid = requestListDiv.parent().attr('id')

			removeStatusDiv(_statusListDiv.children('#status-' + uuid))

			requestListDiv.children().each(function(i, e) {
				var data = $(e).data()
				wiService.request.purge(null, null, false, data.dcid, self.user, data.req_id)
			})

			// no more in sync, deactivate download and delete buttons
			wiStatusQueryControl.clear()

			_popupDiv.dialog('close')
		}
	}

	function addOneRequest(dcid, req) {
		var self = this
		var displayDiv = _popupDiv.children('.wi-status-popup-display').first()
		var msgsDiv = displayDiv.children('.wi-status-popup-msgs').first()
		var groupsDiv = displayDiv.children('.wi-status-popup-groups').first()

		if (!msgsDiv.length || !groupsDiv.length || (groupsDiv.children().length && !groupsDiv.children('#' + req.uuid).length)) {
			var disp = newDisplay()
			msgsDiv = disp.msgs
			groupsDiv = disp.groups
		}

		return self.addOneRequestBase(dcid, req, msgsDiv, groupsDiv, _groupClass)
	}

	function addRequests(dcid, data) {
		var self = this

		$.each(data, function(i, req) { self.addOneRequest(dcid, req) })
	}

	function openStatusPopupFn(div) {
		var self = this

		return function() {
			var data = div.data()
			var disp = newDisplay()

			if (data.failure.length) {
				var html = '<div class="wi-warning-routing">Routing of the following lines failed:<br/>'
				$.each(data.failure, function(i, req) {
					$.each(req.line, function(i, line) {
						html += self.formatLine(line.content) + '<br/>'
					})
				})

				html += '</div>'

				disp.main.append(html)
			}

			$.each(data.success, function(i, req) {
				wiService.request.status(self.addRequestsFn(req.dcid), null, true, req.dcid, self.user, req.id)
			})

			var description = div.children('.wi-status-item-description').first().text()

			_popupDiv.dialog('option', 'title', description)
			_popupDiv.dialog('open')
		}
	}

	function renderStatusDiv(data, description, rowclass, ready, statusmsg) {
		var self = this
		var div = $('<div class="' + rowclass + '"/>')

		if (ready) {
			div.attr('id', 'status-' + data.uuid)
			div.css('cursor', 'pointer')
			div.click(self.openStatusPopupFn(div))

			var datacenters = function() {
				var d = {}
				$.each(data.success, function(i, req) {
					d[req.dcid] = true
				})

				return $.map(d, function(v, k) { return k }).join(', ')
			}()

			var request_count = data.success.length
			var statustext = ': ' + request_count + ' request' + ((request_count != 1)? 's': '') + ' (' + datacenters + '), click to open status popup';
		}
		else {
			var statustext = ": " + (statusmsg? statusmsg: "routing in progress, please wait...")
		}

		div.append($('<span class="wi-status-item-description">').text(description));
		div.append($('<span class="wi-status-item-progress">').text(statustext));
		div.append($('<span style="font-size:larger; font-weight:bold">').text(' [+]'));
		div.data(data);

		return div
	}

	function updateStatusDiv(div, data, statusmsg) {
		var self = this
		var description = div.children('.wi-status-item-description').first().text()
		var rowclass = (div.hasClass('wi-odd')? 'wi-odd': 'wi-even')

		if (data)
			var newDiv = self.renderStatusDiv(data, description, rowclass, true, statusmsg)
		else
			var newDiv = self.renderStatusDiv(div.data(), description, rowclass, false, statusmsg)

		div.replaceWith(newDiv)

		return newDiv
	}

	function removeStatusDiv(div) {
		div.remove()

		_statusListDiv.children().each(function(i, e) {
			if (i % 2) $(e).addClass('wi-odd').removeClass('wi-even')
			else $(e).addClass('wi-even').removeClass('wi-odd')
		})

		if (!_statusListDiv.children().length)
			_buttonsDiv.empty()
	}

	function addStatusDiv(description, statusmsg) {
		var self = this

		if (!_buttonsDiv.children().length) {
			var clearButton = $('<input class="wi-inline" type="button" value="Clear list"/>')
			var deleteCheckbox = $('<input type="checkbox" checked="checked">Delete requests</input>')
			clearButton.button().click(function() { self.clear(false, deleteCheckbox.prop('checked')) })

			_buttonsDiv.append(clearButton)
			_buttonsDiv.append(deleteCheckbox)
		}

		var rowclass = (_statusListDiv.children().length % 2)? 'wi-odd': 'wi-even'
		var div = self.renderStatusDiv(null, description, rowclass, false, statusmsg)

		_statusListDiv.append(div)

		return div
	}

	function checkWaveformSize(param) {
		var self = this
		var timewindows = JSON.parse(param.timewindows)
		var lineCount = timewindows.length
		var estimatedSize = 0

		$.each(timewindows, function(i, tw) {
			// [0] start [1] end [2] net [3] sta [4] cha [5] loc [6] size
			estimatedSize += tw[6]/(1024*1024)
		})

		estimatedSize = Math.ceil(estimatedSize)

		var totalLineLimit = configurationProxy.value('request.totalLineLimit', 10000)
		var totalSizeLimit = configurationProxy.value('request.totalSizeLimit', 10000)
		var lineLimit = configurationProxy.value('request.lineLimit', 990)
		var sizeLimit = configurationProxy.value('request.sizeLimit', 500)
		var partCount = Math.ceil(Math.max(lineCount/lineLimit, estimatedSize/sizeLimit))

		if (lineCount > totalLineLimit || estimatedSize > totalSizeLimit) {
			alert("You would request roughly " + estimatedSize + " MB of data (" +
				lineCount + " traces). Sorry, but this exceeds configured total limits (" +
				totalSizeLimit + " MB, " + totalLineLimit + " traces).")

			return false
		}

		if (!confirm("You are about to request roughly " + estimatedSize + " MB of data (" +
				lineCount + " traces)." +
				((partCount>1)? " The request will be split into at least " +
				partCount + " parts to avoid exceeding configured per-request limits (" +
				sizeLimit + " MB, " + lineLimit + " traces).": "") + "\n\nSend request?")) {

			return false
		}

		return true
	}

	function checkMetadataSize(param) {
		var self = this
		var timewindows = JSON.parse(param.timewindows)
		var lineCount = timewindows.length
		var totalLineLimit = configurationProxy.value('request.totalLineLimit', 10000)
		var localLineLimit = configurationProxy.value('request.localLineLimit', 4990)
		var partCount = Math.ceil(lineCount/localLineLimit)

		if (lineCount > totalLineLimit) {
			alert("You would request metadata for " + lineCount + " traces. " +
				"Sorry, but this exceeds configured total limits (" +
				totalLineLimit + " traces).")

			return false
		}

		if (!confirm("You are about to request metadata for " + lineCount + " traces." +
				((partCount>1)? " The request will be split into " +
				partCount + " parts to avoid exceeding per-request limits (" +
				localLineLimit + " traces).": "") + "\n\nSend request?")) {

			return false
		}

		return true
	}

	function presets(param) {
		switch (param.requesttype) {
			case "FDSNWS-dataselect": return {
				service: "dataselect",
				options: {},
				bulk: false,
				merge: true,
				contentType: "application/vnd.fdsn.mseed",
				filename: param.description.replace(' ', '_') + ".mseed"
			}

			case "FDSNWS-station-xml": return {
				service: "station",
				options: { format: "xml", level: param.level },
				bulk: true,
				merge: false,
				contentType: "application/xml",
				filename: param.description.replace(' ', '_') + ".xml"
			}

			case "FDSNWS-station-text": return {
				service: "station",
				options: { format: "text", level: param.level },
				bulk: true,
				merge: true,
				contentType: "text/plain",
				filename: param.description.replace(' ', '_') + ".txt"
			}

			default: return {}
		}
	}

	function submitRequest(param) {
		if (!_controlDiv) return

		var self = this

		if (param.requesttype.substr(0, 6) == "FDSNWS") {
			wiFDSNWS_Control.submitRequest($.extend(param, presets(param)))
			return true
		}

		if (param.requesttype == "FSEED" || param.requesttype == "MSEED") {
			if (!self.checkWaveformSize(param))
				return false
		}
		else {
			if (!self.checkMetadataSize(param))
				return false
		}

		// "routing in progress"
		var div = self.addStatusDiv(param.description)

		wiService.request.submit(function(data) {
			var failCount = 0

			wiConsole.info("Sent " + data.success.length + " request" + ((data.success.length != 1)? "s": ""))
			$.each(data.failure, function(i, req) {
				failCount += req.line.length
			})

			if (failCount > 0)
				wiConsole.warning("Routing of " + failCount + " lines failed")

			self.updateStatusDiv(div, data)

			// notify download tab that a request has been submitted
			if (_callback) _callback()
		}, function(jqxhr) {
			if (jqxhr.status == 500)
				var err = jqxhr.statusText
			else
				var err = jqxhr.responseText

			wiConsole.error("Failed to submit request: " + err)

			self.removeStatusDiv(div)
		}, false, param)

		// no more in sync, deactivate download and delete buttons
		wiStatusQueryControl.clear()

		return true
	}

	function reviewRequest(param) {
		if (!_controlDiv) return

		var self = this

		wiRequestReviewControl.review(param,
			function() {
				return self.submitRequest(param)
			},
			function() {
				return confirm("Discard request?")
			}
		)
	}

	function removeStatusItem(uuid) {
		if (!_controlDiv) return

		removeStatusDiv(_statusListDiv.children('#status-' + uuid))
	}

	function clear(force, deleteRequests) {
		if (!_controlDiv) return

		var self = this

		_popupDiv.dialog('close')

		_statusListDiv.children().each(function(i, e) {
			var data = $(e).data()

			if ('success' in data) {
				if (deleteRequests)
					$.each(data.success, function(i, req) {
						wiService.request.purge(null, null, false, req.dcid, self.user, req.id)
					})

				$(e).remove()
			}
			else if (force) {
				$(e).remove()
			}

		})

		if (!_statusListDiv.children().length)
			_buttonsDiv.empty()
	}

	function setCallback(callback) {
		_callback = callback
		wiFDSNWS_Control.setCallback(callback)
	}

	this.resubmitFailFn = resubmitFailFn
	this.resubmitDoneFn = resubmitDoneFn
	this.resubmitButtonFn = resubmitButtonFn
	this.deleteButtonFn = deleteButtonFn
	this.addOneRequestBase = this.addOneRequest
	this.addOneRequest = addOneRequest
	this.addRequests = addRequests
	this.openStatusPopupFn = openStatusPopupFn
	this.renderStatusDiv = renderStatusDiv
	this.updateStatusDiv = updateStatusDiv
	this.removeStatusDiv = removeStatusDiv
	this.addStatusDiv = addStatusDiv
	this.checkWaveformSize = checkWaveformSize
	this.checkMetadataSize = checkMetadataSize

	// Public
	this.submitRequest = submitRequest
	this.reviewRequest = reviewRequest
	this.removeStatusItem = removeStatusItem
	this.clear = clear
	this.setCallback = setCallback

	// Load the object into the HTML page
	load(htmlTagId)
}

WIStatusListControl.prototype = new WIStatusBase

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.wiStatusQueryControl = new WIStatusQueryControl("#wi-StatusQueryControl")
			window.wiStatusFullControl = new WIStatusFullControl("#wi-StatusFullControl")
			window.wiStatusListControl = new WIStatusListControl("#wi-StatusListControl")

			// Add hidden download frame, so clicking on download links will not cancel AJAX requests
			$(document.body).append('<iframe name="wi-DownloadFrame" style="display: none"/>')
			resolve()
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("status.js: " + e.message)

			wiConsole.error("status.js: " + e.message, e)
			reject()
		}
	})
}

