/*
 * GEOFON WebInterface
 *
 * review.js module: review/edit request before submission.
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Andres Heinloo, Javier Quinteros, GFZ Potsdam
 *  June/July 2013
 *
 */

/*
 * Implementation of the wiRequestReviewControl
 */
function WIRequestReviewControl(htmlTagId) {
	// Private
	//var _controlDiv = null
	var _popupDiv = null
	var _displayDiv = null
	var _doneButton = null
	var _cancelButton = null

	function buildControl() {
		_popupDiv = $('<div class="wi-review-popup"/>')
		_popupDiv.dialog({autoOpen: false, modal:true, width: 900})
		_displayDiv = $('<div class="wi-review-display"/>')

		var buttonsDiv = $('<div class="wi-control-item-last"/>')

		_cancelButton = $('<input class="wi-inline" type="button" value="Cancel"/>')
		_cancelButton.button()

		_doneButton = $('<input class="wi-inline" type="button" value="Submit"/>')
		_doneButton.button()

		buttonsDiv.append(_cancelButton)
		buttonsDiv.append(_doneButton)

		_popupDiv.append(_displayDiv)
		_popupDiv.append(buttonsDiv)
	}

	function load(htmlTagId) {
		//var control = $(htmlTagId)

		// If we don't find one div ...
		//if (control.length !== 1) {
		//	if (interfaceLoader.debug()) console.error("review.js: Cannot find a div with class '" + htmlTagId + "'")
		//	return
		//}

		// otherwise finish load ...
		//_controlDiv = control

		// build the interface
		buildControl()
	}

	// Convert timewindows list into a more conveniently editable structure
	function steepen(timewindows) {
		var twtree = { net: {}, netlist: [] }

		$.each(timewindows, function(i, twitem) {
			if (twitem[2] in twtree.net) {
				var net = twtree.net[twitem[2]]
			}
			else {
				var net = { sta: {}, stalist: [] }
				twtree.net[twitem[2]] = net
			}

			if (twitem[3] in net.sta) {
				var sta = net.sta[twitem[3]]
			}
			else {
				var sta = { tw: {}, twlist: [], str: {}, strlist: [], ch: {}, size: {} }
				net.sta[twitem[3]] = sta
			}

			sta.tw[twitem[0] + twitem[1]] = { enabled: true, start: twitem[0], end: twitem[1] }
			sta.ch[twitem[5] + twitem[4]] = { enabled: true, cha_code: twitem[4], loc_code: twitem[5] }
			sta.size[twitem[0] + twitem[1] + twitem[5] + twitem[4]] = twitem[6]
		})

		$.each(twtree.net, function(net_code, net) {
			twtree.netlist.push(net_code)

			$.each(net.sta, function(sta_code, sta) {
				net.stalist.push(sta_code)

				$.each(sta.tw, function(k, v) {
					sta.twlist.push(k)
				})

				sta.twlist.sort()

				$.each(sta.ch, function(k, v) {
					var sk = v.loc_code + v.cha_code.substr(0, 2)

					if (sk in sta.str)
						sta.str[sk].push(v.loc_code + v.cha_code)
					else
						sta.str[sk] = [v.loc_code + v.cha_code]
				})

				$.each(sta.str, function(k, v) {
					sta.strlist.push(k)
					v.sort()
				})

				sta.strlist.sort()
			})

			net.stalist.sort()
		})

		twtree.netlist.sort()

		return twtree
	}

	// Convert edited request back to timewindows list
	function flatten(twtree) {
		var timewindows = []

		$.each(twtree.netlist, function(i, net_code) {
			var net = twtree.net[net_code]

			$.each(net.stalist, function(i, sta_code) {
				var sta = net.sta[sta_code]

				$.each(sta.twlist, function(i, tk) {
					var tw = sta.tw[tk]

					if (!tw.enabled)
						return true

					$.each(sta.strlist, function(i, sk) {
						var chlist = sta.str[sk]

						$.each(chlist, function(i, ck) {
							var ch = sta.ch[ck]

							if (!ch.enabled)
								return true

							if (!((tk + ck) in sta.size))
								return true

							// assuming that data size did not change even if time window was changed
							timewindows.push([tw.start, tw.end, net_code, sta_code, ch.cha_code, ch.loc_code,
									sta.size[tk + ck]])
						})
					})
				})
			})
		})

		return timewindows
	}

	function toggleNetwork() {
		var tr = $(this).parent().parent()
		tr.find('input[name=station]').prop('checked', $(this).prop('checked')).change()
		tr.nextUntil('.wi-net-row').find('input[name=station]').prop('checked', $(this).prop('checked')).change()
	}

	function toggleStation() {
		var tr = $(this).parent().parent()
		tr.find('input[name=twsel]').prop('checked', $(this).prop('checked')).change()
	}

	function toggleTW() {
		var div = $(this).parent()
		var tw = div.data('tw')
		var td = div.parent()
		var tr = td.parent()
		var chdisable = true
		tw.enabled = $(this).prop('checked')
		td.find('input[name=twsel]').each(function(i, e) {
			if ($(e).prop('checked')) {
				chdisable = false
				return false
			}
		})
		tr.find('input[name=chsel]').prop('disabled', chdisable)
	}

	function changeTWStart() {
		var div = $(this).parent()
		var tw = div.data('tw')
		tw.start = $(this).val()
	}

	function changeTWEnd() {
		var div = $(this).parent()
		var tw = div.data('tw')
		tw.end = $(this).val()
	}

	function toggleChannel() {
		var ch = $(this).data('ch')
		ch.enabled = $(this).prop('checked')
	}

	function review(param, done, cancel) {
		var self = this
		var twtree = steepen(JSON.parse(param.timewindows))
		var haveStream = {}

		var html = ''
		html += '<table style="width: 100%">'
		html +=   '<tr class="wi-odd">'
		html +=     '<th>Network</th>'
		html +=     '<th>Station</th>'
		html +=     '<th>Time Windows</th>'
		html +=     '<th>Stream Selection'
		html +=	      '<table>'
		html +=         '<tr>'
		html +=           '<td rowspan="2"><select name="selstream" size="3" multiple="multiple"/></td>'
		html +=           '<td style="text-align: left">'
		html +=             '<div>'
		html +=               '<input type="button" value="All" name="allvert"/>'
		html +=               '<input type="button" value="None" name="novert"/> Vertical'
		html +=	            '</div>'
		html +=           '</td>'
		html +=         '</tr>'
		html +=         '<tr>'
		html +=           '<td style="text-align: left">'
		html +=             '<div>'
		html +=               '<input type="button" value="All" name="allhor"/>'
		html +=               '<input type="button" value="None" name="nohor"/> Horizontal'
		html +=             '</div>'
		html +=           '</td>'
		html +=         '</tr>'
		html +=       '</table>'
		html +=     '</th>'
		html +=   '</tr>'
		html += '</table>'

		var reviewTable = $(html)

		reviewTable.find('input[name=allvert]').click(function() {
			reviewTable.find('input.wi-comp-vert').prop('checked', true).change()
		})

		reviewTable.find('input[name=novert]').click(function() {
			reviewTable.find('input.wi-comp-vert').prop('checked', false).change()
		})

		reviewTable.find('input[name=allhor]').click(function() {
			reviewTable.find('input.wi-comp-horiz').prop('checked', true).change()
		})

		reviewTable.find('input[name=nohor]').click(function() {
			reviewTable.find('input.wi-comp-horiz').prop('checked', false).change()
		})

		var nrow = 'wi-odd'
		var srow = 'wi-odd'

		$.each(twtree.netlist, function(i, net_code) {
			var net = twtree.net[net_code]

			$.each(net.stalist, function(i, sta_code) {
				var sta = net.sta[sta_code]
				var tr, td

				if (i == 0) {
					srow = nrow = (nrow == 'wi-even')? 'wi-odd': 'wi-even'
					tr = $('<tr class="wi-net-row ' + nrow + '"/>')
					td = $('<td rowspan="' + net.stalist.length + '"/>')

					var networkCheckbox = $('<input type="checkbox" name="network" checked="checked"/>')
					networkCheckbox.change(toggleNetwork)
					td.append(networkCheckbox)
					td.append(document.createTextNode(net_code))
					tr.append(td)
				}
				else {
					srow = (srow == 'wi-even')? 'wi-odd': 'wi-even'
					tr = $('<tr class="' + srow + '"/>')
				}

				td = $('<td nowrap="nowrap"/>')
				var stationCheckbox = $('<input type="checkbox" name="station" checked="checked"/>')
				stationCheckbox.change(toggleStation)
				td.append(stationCheckbox)
				td.append(document.createTextNode(sta_code))
				tr.append(td)

				td = $('<td nowrap="nowrap">')
				$.each(sta.twlist, function(i, tk) {
					var tw = sta.tw[tk]
					var div = $('<div>')
					div.data('tw', tw)
					var twCheckbox = $('<input type="checkbox" name="twsel" checked="checked"/>')
					twCheckbox.change(toggleTW)
					var twStart = $('<input type="text" name="twstart" value="' + tw.start + '" size="22"/>')
					twStart.change(changeTWStart)
					var twEnd = $('<input type="text" name="twend" value="' + tw.end + '" size="22"/>')
					twEnd.change(changeTWEnd)
					div.append(twCheckbox)
					div.append(twStart)
					div.append('<span class="wi-to">-</span>')
					div.append(twEnd)
					td.append(div)
				})
				tr.append(td)

				td = $('<td>')
				var chTable = $('<table>')
				$.each(sta.strlist, function(i, sk) {
					var chlist = sta.str[sk]
					var chTr = $('<tr>')
					$.each(chlist, function(i, ck) {
						var ch = sta.ch[ck]
						var str_code = ch.cha_code.substr(0, 2)
						var comp = 'horiz'

						if (ch.cha_code.substr(2, 1) == 'Z')
							comp = 'vert'

						haveStream[str_code] = true

						var chTd = $('<td>')
						var chCheckbox = $('<input class="wi-stream-' + str_code + ' wi-comp-' + comp + '" type="checkbox" name="chsel" checked="checked"/>')
						chCheckbox.data('ch', ch)
						chCheckbox.change(toggleChannel)
						chTd.append(chCheckbox)
						chTd.append(document.createTextNode(ck))
						chTr.append(chTd)
					})
					chTable.append(chTr)
				})
				td.append(chTable)
				tr.append(td)
				reviewTable.append(tr)
			})
		})

		var existingStreams = []
		$.each(haveStream, function(k, v) { existingStreams.push(k) })
		existingStreams.sort()

		var selstream = reviewTable.find("select[name=selstream]")
		$.each(existingStreams, function(i, str_code) {
			selstream.append('<option selected="selected" value="' + str_code + '">' + str_code + '</option>')
		})

		selstream.change(function(item) {
			if ($(this).val()) {
				var selected = {}
				$.each($(this).val(), function(i, s) {
					selected[s] = true
				})
				$.each(existingStreams, function(i, s) {
					reviewTable.find('input.wi-stream-' + s).prop('checked', s in selected).change()
				})
			}
			else {
				reviewTable.find('input[name=chsel]').prop('checked', false)
			}
		})

		var closeRequested = false

		_doneButton.click(function() {
			param.timewindows = JSON.stringify(flatten(twtree))

			if (done()) {
				closeRequested = true
				_popupDiv.dialog('close')
			}
		})

		_cancelButton.click(function() {
			if (cancel()) {
				closeRequested = true
				_popupDiv.dialog('close')
			}
		})

		_popupDiv.on('dialogbeforeclose', function() {
			if (closeRequested || cancel())	{
				_doneButton.unbind('click')
				_cancelButton.unbind('click')
				_popupDiv.off('dialogbeforeclose')
				_displayDiv.empty()
				return true
			}

			return false
		})

		_displayDiv.append(reviewTable)

		_popupDiv.dialog('option', 'title', 'Review of ' + param.description)
		_popupDiv.dialog('open')
	}

	// Public
	this.review = review

	// Load the object into the HTML page
	load(htmlTagId)
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.wiRequestReviewControl = new WIRequestReviewControl("#wi-RequestReviewControl")
			resolve()
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("review.js: " + e.message)

			wiConsole.error("review.js: " + e.message, e)
			reject()
		}
	})
}

