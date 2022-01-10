/*
 * GEOFON WebInterface
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, GFZ Potsdam
 *
 * request.js module: This the module that holds the returning
 *                    information from StationSearchControl and
 *                    EventSearchControl. He should be able to ...
 */

/*
 * Configuration proxy Object implementation
 */
function Pack(id) {
	// See <http://javascript.crockford.com/private.html>
	var that = this;

	var arrow;

	var _station_list = null;
	var _station_dictionary = null;

	var _event_list = null;
	var _event_dictionary = null;

	var _id = undefined;

	var _current_event_div = null;
	var _current_event_count_span = null;

	var _current_station_div = null;
	var _current_station_count_span = null;

	var _locations_index = null;
	var _orientations_index = null;
	var _gains_index = null;
	var _samplings_index = null;

	// Private Cell data formaters
	function fmtGeneric(rowid, value) {
		return value;
	}

	function fmtCoordinate(rowid, value) {
		return Number(value).toFixed(2);
	}

	function fmtStreams(rowid, value) {
		// Produce a <table>, each row is a group like "BHE, BHN, BHZ"
		var groups = { };

		var html = '<i>No Streams Selected</i>';

		if (value.length !== 0) {
			for(var key in value) {
				var fcode=value[key].trim();
				fcode = fcode.substr(0,fcode.length);
				var bcode = fcode.substr(0,fcode.length-1);
				if (typeof groups[bcode] === "undefined") groups[bcode] = [];
				if (groups[bcode].indexOf(fcode) === -1) groups[bcode].push(fcode);
			}

			html = '<table cellpadding="2" cellspacing="0">';
			for(var key in groups) {
				html += '<tr><td>' + $.map(groups[key], function(stream) { return '<span class="wi-stream-' + stream.replace('.', '-') + '">' + stream + '</span>' }) + '</td><tr>';
			}
			html += '</table>';
		}

		return html;
	}

	function fmtRestricted(rowid, value) {
		if (Number(value) === 1) {
			return '<span style="color: red;">R</span>';
		} else if (Number(value) === 2) {
			return '<span style="color: black;">O</span>';
		} else if (Number(value) === 3) {
			return '<span style="color: black;">O/</span><span style="color: red;">R</span>';
		} else {
			return '??';
		}
	}

	function fmtId(rowid, value) {
		return '<input class="toggle" title="' + value + '" checked="checked" type="checkbox" value="' + rowid + '"/>';
	}

	function fmtCheckbox(rowid, value) {
		var checked = (value === true) ? 'checked="checked"' : "";
		return '<input class="toggle" title="' + rowid + '" ' + checked + ' type="checkbox" value="' + rowid + '"/>';
	}

	function fmtDepth(rowid, value) {
		// Where those NaNs came from??
		return Number(value).toFixed(1);
	}

	function fmtMagnitude(rowid, value) {
	    // '--' can be returned by the event service when no magnitude is available.
	    if (value == '--') {
		return "";
	    } else {
		return Number(value).toFixed(1);
	    };
	}

	// Station and Event table specifications formatters
	var _station_format = {
		names     : [ "key", "netcode", "statcode", "latitude", "longitude", "restricted", "netclass", "archive", "netoperator" , "streams", "streams_restricted", "selected", "fstreams" ],
		shortnames: [ ""   , "Network", "Station" , "Lat."    , "Long."    , 'O/R'       , "Net.Type", "Archive", "Net.Operator", "Streams", "StreamsRestricted", "selected", "Streams" ],
		sortable  : [ false, true     , true      , true      , true       , false       , true      , true     , true          , false    , false     , false, false ],
		format    : [ fmtId, fmtGeneric, fmtGeneric, fmtCoordinate, fmtCoordinate, fmtRestricted, fmtGeneric, fmtGeneric, fmtGeneric, fmtStreams, fmtGeneric, fmtCheckbox, fmtStreams ],
		aligment  : [ "center", "center", "center", "center", "center", "center","center", "center", "center", "left", "center", "center", "center" ],
		order     : [ 11, 1, 2, 3, 4, 5, 12 ]
	};

	var _event_format = {
	    names     : [ "datetime"     , "magnitude", "magtype", "latitude", "longitude", "depth", "key", "region", "selected" ],
	    shortnames: [ "Origin Time"  , "Mag.",      "Type"   , "Lat."    , "Long."    , "Depth", ""   , "Region", 'selected' ],
	    sortable  : [ true           , true       , false    , true      , true       , true   , false, true    , false ],
	    format    : [ fmtGeneric, fmtMagnitude, fmtGeneric, fmtCoordinate, fmtCoordinate, fmtDepth, fmtId, fmtGeneric, fmtCheckbox ],
	    aligment  : [ "center"       , "center"   , "left"   , "center"  , "center"   , "center", "center", "left", "center" ],
	    order     : [ 8, 0, 1, 2, 3, 4, 5, 7 ]
	};

	// Private
	function sortFn(column, reverse) {
		var cindex = column;
		if (cindex === -1) {
			wiConsole.error("request.js: Cannot find column index for " + column);
			return null;
		}
		var flag = (reverse) ? 1 : -1;

		var fn = function(a,b) {
			if (a[cindex] > b[cindex]) return flag*1;
			if (a[cindex] == b[cindex]) return 0;
			if (a[cindex] < b[cindex]) return -1*flag;
		};

		return fn;
	}

	function buildChannelFilterIndex() {
		var locations = {};
		var samplings = {};
		var gains = {};
		var orientations = {};

		if (_station_list) {
			var cid = _station_format.names.indexOf("streams");

			for(var stkey in _station_list) {
				var stline = _station_list[stkey];
				for (var chkey in stline[cid]) {
					var channel = stline[cid][chkey];

					if (channel.indexOf(".") === -1) {
						wiConsole.error("request.js: Invalid location/channel pattern " + channel + ". It does not contains a dot (.)");
						continue;
					}

					var channelparts = channel.split(".");

					if (channelparts.length !== 2) {
						wiConsole.error("request.js: Invalid channel/location pattern " + channel + ". It has more than two fields.");
						continue;
					}

					if (channelparts[1].length !== 3) {
						wiConsole.error("request.js: Invalid channel pattern " + channel.split(".")[1] + ". It should have three letters long corresponding to sampling code, gain code and orientation code. ");
						continue;
					}

					var location = channelparts[0];
					var sampling = channelparts[1][0];
					var gain     = channelparts[1][1];
					var orientation = channelparts[1][2];

					if (typeof locations[location] === "undefined") locations[location] = true;
					if (typeof samplings[sampling] === "undefined") samplings[sampling] = true;
					if (typeof gains[gain] === "undefined") gains[gain] = true;
					if (typeof orientations[orientation] === "undefined") orientations[orientation] = true;
				}
			}
		}

		// Store the final results
		_locations_index = locations;
		_samplings_index = samplings;
		_gains_index = gains;
		_orientations_index = orientations;
	}

	// PLE Aug 2013: Can't the following four functions be combined?
	// They modify global variables - either _event_list or _station_list
	// They call either renderEvent() or renderStation()
	function sortEventUp(arrow) {
		var column = _event_format.names.indexOf($(arrow.target).parents("th").prop("id"));
		var _sorted_list = _event_list.sort(sortFn(column,false));
		_event_list = _sorted_list;

		that.renderEvent();
	}

	function sortEventDown(arrow) {
		var column = _event_format.names.indexOf($(arrow.target).parents("th").prop("id"));
		var _sorted_list = _event_list.sort(sortFn(column,true));
		_event_list = _sorted_list;

		that.renderEvent();
	}

	function sortStationUp(arrow) {
		var column = _station_format.names.indexOf($(arrow.target).parents("th").prop("id"));
		var _sorted_list = _station_list.sort(sortFn(column,false));
		_station_list = _sorted_list;
		that.renderStation();
	}

	function sortStationDown(arrow) {
		var column = _station_format.names.indexOf($(arrow.target).parents("th").prop("id"));
		var _sorted_list = _station_list.sort(sortFn(column,true));
		_station_list = _sorted_list;
		that.renderStation();
	}

	function render_header(format) {
		var html = '<tr class="wi-table-header">';
		var arrows = '<span class="wi-arrow-up"></span><span class="wi-arrow-down"></span>';
		for(var ckey in format.order) {
			var key = format.order[ckey];
			if (format.names[key] === "selected") {
				html += '<th class="wi-table-header-cell"><input class="table-toggle" type="checkbox" /></th>';
				continue;
			}
			// FIXME: (PLE Aug 2013) Common string apart from 'arrows'
			if (format.sortable[key]) {
				html += '<th class="wi-table-header-cell" id="' + format.names[key] + '">' + format.shortnames[key] + arrows + '</th>';
			} else {
				html += '<th class="wi-table-header-cell" id="' + format.names[key] + '">' + format.shortnames[key] + '</th>';
			}
		}
		html += '</tr>';
		return html;
	}

	function render_row(format, rowkey, data) {
		// From 'data', build table content as a string of <tr>s.
		// Format can be the station or event format objects
		// Set rowkey = 0 to generate a table header.

		var html = '';
		var rowid = data[ format.names.indexOf('key') ];

		// This is a "static" variable from a JS point of view (remember 
		// that each function is an object - sound confusing :s)
		var rowclass = (typeof rowclass === "undefined") ? "wi-odd" : rowclass;

		// We switch the last used style
		rowclass = (rowclass === "wi-odd") ? "wi-even" : "wi-odd";

		// Render the data row for the data content
		html += '<tr class="' + rowclass + '" id="' + rowid + '">';
		for(var ckey in format.order) {
			var key = format.order[ckey];
			html += '<td class="' + format.names[key] + '" valign="top" align="' + format.aligment[key] + '">' + format.format[key](rowid, data[key]) + '</td>';
		}
		html += '</tr>';

		// Return the results from the render
		return html;
	}

	function connectEvent() {
		// This is a speed-up access to the methods created here
		var skey = _event_format.names.indexOf('selected');

		/*
		 * Connects the check boxes on the table
		 */
		_current_event_div.find("table").find(".table-toggle").bind("change", function(item) { 
			var obj = $(item.target);
			obj.parents("table").find(".toggle").prop('checked', obj.is(':checked') ).change();
		});

		_current_event_div.find("table").find(".toggle").bind("change", function(item){
			var obj = $(item.target);

			var evline = _event_dictionary[obj.val()];
			evline[skey] = obj.is(':checked');

			if ( ! obj.is(':checked') )
				obj.parents("table").find(".table-toggle").prop('checked', false);

			mapEvent(obj.val());
		});

		/*
		 * Connect the sorting arrows
		 */
		_current_event_div.find(".wi-arrow-up").bind("click", sortEventUp);
		_current_event_div.find(".wi-arrow-down").bind("click", sortEventDown);
	}

	function connectStation() {
		// This is a speed-up access to the methods created here
		var skey = _station_format.names.indexOf('selected');
		var fkey = _station_format.names.indexOf('fstreams');

		/*
		 * Connects the check boxes on the table
		 */
		_current_station_div.find("table").find(".table-toggle").bind("change", function(item) { 
			var obj = $(item.target);
			obj.parents("table").find(".toggle").prop('checked', obj.is(':checked') ).change();
		});

		_current_station_div.find("table").find(".toggle").bind("change", function(item){
			var obj = $(item.target);

			var stline = _station_dictionary[obj.val()];
			stline[skey] = obj.is(':checked');

			if ( ! obj.is(':checked') )
				obj.parents("table").find(".table-toggle").prop('checked', false);

			mapStation(obj.val());
		});

		/*
		 * Connect the sorting arrows
		 */
		_current_station_div.find(".wi-arrow-up").bind("click", sortStationUp);
		_current_station_div.find(".wi-arrow-down").bind("click", sortStationDown);

		/*
		 * Connect the Stream filters
		 */
		_current_station_div.find("#station-filter-toggle").button().bind("click", function(obj) {
			_current_station_div.find("#station-filter-toggle").hide();
			_current_station_div.find("#wi-station-filter-row").show();
		});

		_current_station_div.find("#station-filter-close").button().bind("click", function(obj) {
			_current_station_div.find("#station-filter-toggle").show();
			_current_station_div.find("#wi-station-filter-row").hide();
		});

		_current_station_div.find("#station-filter-apply").button().bind("click", function(obj) {
			applyStreamFilter();
			that.renderStation();
		});

		_current_station_div.find("#wi-station-filter-row").hide();

		for (var key in _locations_index) {
			_current_station_div.find('#location-' + ((key === "")? '--': key)).change((function(key) {
				return function() {
					_locations_index[key] = $(this).prop('checked')
				}
			})(key))
		}

		for (var key in _samplings_index) {
			_current_station_div.find('#sampling-' + key).change((function(key) {
				return function() {
					_samplings_index[key] = $(this).prop('checked')
				}
			})(key))
		}

		for (var key in _gains_index) {
			_current_station_div.find('#gain-' + key).change((function(key) {
				return function() {
					_gains_index[key] = $(this).prop('checked')
				}
			})(key))
		}

		for (var key in _orientations_index) {
			_current_station_div.find('#orientation-' + key).change((function(key) {
				return function() {
					_orientations_index[key] = $(this).prop('checked')
				}
			})(key))
		}
	}

	function applyStreamFilter() {
		var stri = _station_format.names.indexOf('streams')
		var restri = _station_format.names.indexOf('restricted')
		var fstri = _station_format.names.indexOf('fstreams')
		var srestri = _station_format.names.indexOf('streams_restricted')
		var seli = _station_format.names.indexOf('selected')

		for (var i in _station_list) {
			var streams_filtered = []
			var restricted = 0

			for (var j in _station_list[i][stri]) {
				var stream = _station_list[i][stri][j]
				var sep = stream.indexOf('.')
				var loc = stream.substr(0, sep)
				var samp = stream.substr(sep+1, 1)
				var gain = stream.substr(sep+2, 1)
				var ornt = stream.substr(sep+3, 1)

				if (_locations_index[loc] &&
						_samplings_index[samp] &&
						_gains_index[gain] &&
						_orientations_index[ornt]) {
					streams_filtered.push(stream)
					// restricted: 1 for restricted; 2 for open; 3 for both
					restricted = (restricted | _station_list[i][srestri][j])
				}
			}

			_station_list[i][fstri] = streams_filtered;

			// If every stream is filtered out deselect a station
			if (streams_filtered.length === 0)
				_station_list[i][seli] = false
			else
				_station_list[i][restri] = restricted
		}
	}

	function mapStation(id) {
		if (!mapControl.enabled()) return;
		/*
		 * Clear the events before adding it again !
		 */
		if (!_station_list)
			mapControl.removeStation(undefined);

		var idi  = _station_format.names.indexOf("key");
		var neti = _station_format.names.indexOf("netcode");
		var stai = _station_format.names.indexOf("statcode");
		var loni = _station_format.names.indexOf("longitude");
		var lati = _station_format.names.indexOf("latitude");
		var arci = _station_format.names.indexOf("archive");
		var resi = _station_format.names.indexOf("restricted");
		var typi = _station_format.names.indexOf("netclass");
		var stri = _station_format.names.indexOf("streams");
		var selected = _station_format.names.indexOf("selected");

		for(var key in _station_list) {
			var line = _station_list[key];
			if (typeof id !== "undefined" && line[idi] !== id) continue;

			// mapControl.addEvent(line[idi], line[loni], line[lati], line[depi], line[magi], line[regi], line[dati]);
			mapControl.removeStation(line[idi]);
			mapControl.addStation(line[idi], line[neti], line[stai], line[loni], line[lati], line[arci], line[resi], line[typi], line[stri], line[selected]);
		}
	}

	function mapEvent(id) {
		if (!mapControl.enabled()) return;

		/*
		 * Clear the events before adding it again !
		 */
		if (!_event_list) 
			mapControl.removeEvent(undefined);

		var idi  = _event_format.names.indexOf("key");
		var lati = _event_format.names.indexOf("latitude");
		var loni = _event_format.names.indexOf("longitude");
		var depi = _event_format.names.indexOf("depth");
		var regi = _event_format.names.indexOf("region");
		var dati = _event_format.names.indexOf("datetime");
		var magi = _event_format.names.indexOf("magnitude");
		var selected = _event_format.names.indexOf("selected");

		for(var key in _event_list) {
			var line = _event_list[key];
			if (typeof id !== "undefined" && line[idi] !== id) continue;

			// mapControl.addEvent(line[idi], line[loni], line[lati], line[depi], line[magi], line[regi], line[dati]);
			mapControl.removeEvent(line[idi]);
			mapControl.addEvent(line[idi], line[loni], line[lati], line[depi], line[magi], line[regi], line[dati], line[selected]);
		}
	}

	function renderStationFilter(fieldname, table) {
		var html = '';

		var keys = Object.keys(table).sort();
		for(var keyid in keys) {
			var key = keys[keyid];
			var checked = ((table[key]) ? 'checked="checked"' :"");

			if (key === "") key = '--';
			html += '<div id="wi-' + fieldname + '-filter-group" style="float: left; margin: 2px 2px 0 0;">';
			html += '<input type="checkbox" id="'+ fieldname + "-" + key +'" value="' + key + '" ' + checked + '/><label for="' + fieldname + "-" + key + '">' + key + '</label>';
			html += '</div>';
		}
		return html;
	}

	function renderStationFilters(format) {
		var html = '';

		html += '<tr><td style="font-size: 0.8em; text-align: right; padding: 5px; 35px 5px 0;" colspan="' + format.order.length + '"><input id="station-filter-toggle" type="button" value="Filters"/></td></tr>';
		html += '<tr id="wi-station-filter-row"><td class="wi-station-filter" colspan="' + format.order.length + '">';

		html += '<div style="width: 135px; margin: 0 2px 0 0; float: left;">';
		html += '<h3>Location Code</h3>';
		html += renderStationFilter('location', _locations_index);
		html += '</div>';

		html += '<div style="width: 135px; margin: 0 2px 0 0; float: left;">';
		html += '<h3>Sampling Code</h3>';
		html += renderStationFilter('sampling', _samplings_index);
		html += '</div>';

		html += '<div style="width: 135px; margin: 0 2px 0 0; float: left;">';
		html += '<h3>Instrument Code</h3>';
		html += renderStationFilter('gain', _gains_index);
		html += '</div>';

		html += '<div style="width: 135px; margin: 0 2px 0 0; float: left;">';
		html += '<h3>Orientation Code</h3>';
		html += renderStationFilter('orientation', _orientations_index);
		html += '</div>';

		html += '<div style="text-align: right; float: right; font-size: 0.8em;">';
		html += '<input style="margin: 5px 0 0 0" id="station-filter-close" type="button" value="Close"/><br/>';
		html += '<input style="margin: 5px 0 0 0" id="station-filter-apply" type="button" value="Filter"/>';
		html += '</div>';
		html += '</td></tr>';

		return html;
	}

	// Public
	this.toggleEvent = function (id) {
		if (!_event_list) return;
		var checkbox = _current_event_div.find("table").find(".toggle[value="+id+"]")
		checkbox.prop('checked', !checkbox.prop('checked')).change();
	};

	this.toggleStation = function (id) {
		if (!_station_list) return;
		var checkbox = _current_station_div.find("table").find(".toggle[value="+id+"]")
		checkbox.prop('checked', !checkbox.prop('checked')).change();
	};

	this.saveStation = function() {
		// Prepare a JSON object containing
		// the stream codes, and POST to back end
		// which prepares a file for downloading.
		// These streams are the ones left after
		// selection and filtering.
		// For doof historical reasons, we transmit to the back end
		// as ["N", "S", "C", "L"].  FIXME.

		wiConsole.info("Building the list of selected streams...");
		var streams = Array();
		var neti = _station_format.names.indexOf("netcode");
		var stai = _station_format.names.indexOf("statcode");
		var fstreamsi = _station_format.names.indexOf("fstreams");
		var seli = _station_format.names.indexOf("selected")
		var t;
		for (var k in _station_list) {
			if (_station_list[k][seli] === false) {
				continue;
			}
			var loccha = _station_list[k][fstreamsi];
			if (typeof loccha !== "undefined" && loccha.length > 0) {
				var loc_list = Array();
				var cha_list = Array();
				var words;
				for (var i=0; i < loccha.length; i++) {
					words = loccha[i].split('.');
					loc_list.push(words[0]);
					cha_list.push(words[1]);
				}
				for (var i=0; i < loc_list.length; i++) {
					var t = Array(_station_list[k][neti],
						      _station_list[k][stai],
						      cha_list[i],
						      loc_list[i]);
					streams.push(t);
				}
			}
		}
		var streams_json = JSON.stringify(streams);

		// ISSUE: What happens when there are multiple packs?
		// There's only one exportForm.
		$('form[name="exportForm"]').find('input[name="streams"]')[0].value = streams_json;
		$('form[name="exportForm"]').submit();
		wiConsole.info(" ...exported stream(s)");
	};

	this.reduceEventsRows = function(rowkeys) {
		// Either delete the rows with ~~~keys in rowkeys~~~
		// rows which are checked,
		// or else keep only those.
		// I'm not sure what's the better interface.
		var remove_checked = true;
		var retain_checked = !remove_checked;

		var data = _event_list;

		//alert('Inside reduceRows');
		if (data) {
			alert('Data length:' + data.length);
		} else {
			alert('Data is null');
		}
		var count = 0;
		var count_checked = 0;
		var new_data = Array();
		for (var key in data) {
			var row = data[key];
			count += 1;
			var checked = row[7]; // should be looked up in index
			if ((retain_checked && checked) || (remove_checked && !checked)) {
				count_checked += 1;
				new_data.push(row);
				console.log('Added ' + row);
				alert('Added ' + count + ':' + row);
			}
		}

		_event_list = new_data;
		alert('Checked: ' + count_checked + '/' + count);
		console.log('New length: ' + new_data.length);
		return;
	};

	this.addEvent = function(data) {
		if (_event_list === null) {
			_event_list = [];
			_event_dictionary = {};
		}

		var eidkey = _event_format.names.indexOf('key');

		// Deep copy of it
		var datacopy = Array();
		$.extend(true, datacopy, $.grep(data, function(evline) { return !(evline[eidkey] in _event_dictionary) }));

		// Strip and check header
		var header = datacopy.shift();
		for(var key in header) {
			if (header[key] !== _event_format.names[key])
				console.error("request.js: Event header " + header[key] + " format does not match current implementation.");
		}

		for(var key in datacopy) {
			var evline = datacopy[key];

			// We add a control column to this line that 
			// should bind to the checkbox of the line
			evline.push(true);

			if ( evline.length !== _event_format.names.length ) {
				throw new RequestError("Shut down!");
			}
			for(var key2 in evline) {
				if (typeof evline[key2] === "object")
					throw new RequestError("Shut down! -- " + _event_format.names[key2] + " it is a object");
			}

			// Setup a points structure to the duplicated list elements from the evID
			if (typeof _event_dictionary[evline[eidkey]] !== "undefined" ) {
				throw new RequestError("request.js: OOOPS -- Duplicated ID in event list.");
			}

			_event_dictionary[ evline[ eidkey ] ] = evline;
		}

		_event_list = _event_list.concat(datacopy);
		return true;
	};

	this.addStation = function(data) {
		if (_station_list === null) {
			_station_list = [];
			_station_dictionary = {};
		}

		/*
		 * Deep copy
		 */
		var datacopy = Array();
		$.extend(true, datacopy, data);

		/*
		 * Strip and check header
		 */
		var header = datacopy.shift();
		for(var key in header) {
			if (header[key] !== _station_format.names[key])
				wiConsole.error("request.js: Station header " + header[key] + " format does not match current implementation.");
		}

		/*
		 * Check for duplicates
		 */
		var eidkey = _station_format.names.indexOf('key');
		var duplicates = Array();
		for(var key in datacopy) {
			var stline = datacopy[key];

			// We add a control column to this line that 
			// should bind to the checkbox of the line
			stline.push(true);

			// Set up a points structure to the duplicated list elements from the evID
			if (typeof _station_dictionary[stline[eidkey]] !== "undefined" ) {
				wiConsole.error("request.js: Ignoring duplicate station item ID" + stline[ eidkey ])
				duplicates.push(key);
			}
		}

		/*
		 * Remove the dupplicates array
		 */
		duplicates.reverse();
		for(var key in duplicates) {
			datacopy.splice(duplicates[key],1);
		}

		/*
		 * Concatenate the data to the _station_list
		 */
		_station_list = _station_list.concat(datacopy);

		/*
		 * Rebuild the _station_dictionary
		 */
		_station_dictionary = {};
		for(var key in _station_list) {
			var stline = _station_list[key];
			_station_dictionary[ stline[ eidkey ] ] = stline;
		}

		/*
		 * Rebuild the index for filtering channels
		 */
		buildChannelFilterIndex();

		/*
		 * Compute the filter results for initializing the
		 * fstreams field
		 */
		applyStreamFilter();

		return true;
	};

	this.hasStation = function() {
		return (_station_list !== null);
	};

	this.hasEvent = function() {
		return (_event_list !== null);
	};

	this.eventsCount = function() {
		return (this.hasEvent()) ? _event_list.length : "-";
	};

	this.eventsSelectedCount = function() {
		var n = 0;
		for (var key in _event_list) {
			var checked = _event_list[key][7];  // should be looked up in the event table index
			if (checked) { n += 1; }
		}
		return n;
	};

	this.stationsCount = function() {
		return (this.hasStation()) ? _station_list.length : "-";
	};

	this.id = function() {
		return _id;
	};

	this.eventLines = function() {
		var lines = Array();

		var latitude  = _event_format.names.indexOf("latitude");
		var longitude = _event_format.names.indexOf("longitude");
		var depth = _event_format.names.indexOf("depth");
		var time  = _event_format.names.indexOf("datetime");
		var selected = _event_format.names.indexOf("selected");

		for(var key in _event_list) {
			var line = _event_list[key];
			if ( line[selected] === false ) continue;

			// This "Z" is a hack to send the string to UTC !
			lines.push( [ Number(line[latitude]), Number(line[longitude]), Number(line[depth]), (new Date(line[time] + "Z")).toISOString() ] );
		}

		return lines;
	}

	this.stationLines = function() {
		var lines = Array();

		var networkKey = _station_format.names.indexOf("netcode");
		var stationKey = _station_format.names.indexOf("statcode");
		// 
		// We use the filtered streams instead of the streams 
		// when building submission
		var streamKey  = _station_format.names.indexOf("fstreams");
		var selected = _station_format.names.indexOf("selected");

		for(var rowindex in _station_list) {
			var line = _station_list[rowindex];

			if ( line[selected] === false ) continue;

			// This is very ugly because I keep on removing 
			// the duplicate entries from the metadata service.
			var items = Array();
			for(var key in line[streamKey]) {
				if (items.indexOf(line[streamKey][key]) === -1) items.push(line[streamKey][key]);
			}

			for(var key in items) {
				var location = items[key].split(".")[0];
				var stream = items[key].split(".")[1];
				lines.push( [line[networkKey], line[stationKey], stream, location] )
			}
		}

		return lines;
	};

	this.renderStation = function(div, countspan) {
		if (_current_station_div === null && div === null) throw new RequestError("request.js: Unknown div for rendering station.");
		var html = "<i> No Stations loaded </i>";

		if (_current_station_div)
			_current_station_div.empty();

		if (div)
			_current_station_div = div;

		if (countspan) 
			_current_station_count_span = countspan;

		if (_station_list) {
			html = '<table cellpadding="0" cellspacing="0" width="100%">';
			html += render_header(_station_format);
			html += renderStationFilters(_station_format);
			for(var key in _station_list) {
				html += render_row(_station_format, key, _station_list[key]);
			}
			html += '</table>';
		}

		_current_station_div.append(html);

		/*
		 * Update the counter
		 */
		var text = this.stationsCount() + (this.hasStation() ? ((this.stationsCount() === 1) ? " station" : " stations") : "");
		_current_station_count_span.text(text);

		/*
		 * Local connecting stuff
		 */
		connectStation();

		/*
		 * Map Stations
		 */
		mapStation();

	};

	this.renderEvent = function(div, countspan) {
		if (_current_event_div === null && div === null) throw new RequestError("request.js: Unknown div for rendering event.");
		var html = '<i> No Events loaded </i>';

		if (_current_event_div)
			_current_event_div.empty();

		if (div)
			_current_event_div = div;

		if (countspan)
			_current_event_count_span = countspan;

		if (_event_list) {
			html = '<table cellpadding="0" cellspacing="0" width="100%">';
			html += render_header(_event_format);
			for(var key in _event_list) {
				html += render_row(_event_format, key, _event_list[key]);
			}
			html += '</table>';
		}

		_current_event_div.append(html);

		/*
		 * Update the counter
		 */

		/* Selected count not updated properly
		var text = this.eventsSelectedCount() + '/' + this.eventsCount() + (this.hasEvent() ? ((this.eventsCount() === 1) ? " event" : " events") : "");
		text += " selected"; */
		var text = this.eventsCount() + (this.hasEvent() ? ((this.eventsCount() === 1) ? " event" : " events") : "");
		_current_event_count_span.text(text);

		/*
		 * Local connecting stuff
		 */
		connectEvent();

		/*
		 * Map Events
		 */
		mapEvent();
	};

	this.removeStation = function() {
		_station_list = null;
		this.renderStation(null,null);
	};

	this.removeEvent = function() {
		_event_list = null;
		this.renderEvent(null,null);
	};

	this.freeze = function(div) {
		var id = div.attr('id')

		if (this.hasEvent()) {
			var seli = _event_format.names.indexOf('selected')
			var _event_list_frozen = []

			for(var key in _event_list) {
				var line = _event_list[key]
				if (line[seli])
					_event_list_frozen.push(line)
			}

			_event_list = _event_list_frozen

			this.renderEvent(div.find("#" + id + "-events-div"), div.find("#" + id + "-events-count"));
		}

		if (this.hasStation()) {
			var seli = _station_format.names.indexOf('selected')
			var _station_list_frozen = []

			for(var key in _station_list) {
				var line = _station_list[key]
				if (line[seli])
					_station_list_frozen.push(line)
			}

			_station_list = _station_list_frozen

			this.renderStation(div.find("#" + id + "-stations-div"), div.find("#" + id + "-stations-count"));
		}
	}

	// Main
	if (id === undefined || id === null) throw new RequestError("Invalid supplied id.");
	_id = id;
};

function RequestControl(htmlTagId) {
	// Private
	var _controlDiv = null;
	var _data = undefined;
	var _callbacks = { };

	function buildControl() {
		if (!_controlDiv) return;

		var html = '';
		html += '<div id="requestControlControls"></div>';
		html += '<div id="requestControlTables"></div>';
		_controlDiv.append(html);
	}

	function load(htmlTagId) {
		var control = $(htmlTagId);

		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("request.js: Cannot find a div with class '" + htmlTagId + "'.");
			return;
		}

		// Save the main control div
		_controlDiv = control;

		// Build
		buildControl();
	}

	function generate_id() {
		var timestamp = (new Date()).getTime();
		return timestamp;
	}

	function newPackage() {
		var package_id = generate_id();
		_data = new Pack(package_id);
		return getPackage();
	}

	function getPackage() {
		if ( (typeof _data === "undefined") ) {
			throw new RequestError("request.js: No Request to return.");
		}
		return _data;
	}

	function remove(id) {
		try {
			var datapack = getPackage();

			/*
			 * Ask the pack to remove Events and Stations
			 */
			datapack.removeEvent();
			datapack.removeStation();

			/*
			 * Local exclusion from the list
			 */
			_data = undefined;

			/*
			 * Remove the Request div (and all nested elements if any)
			 */
			_controlDiv.find("#" + id).remove();

		} catch (e) {
			wiConsole.error("No request to remove.");
		}
	}

	function connect(id) {
		_controlDiv.find('#' + id + '-delete-events').button().bind("click", function(item){
			var id = $(item.target).parent("div").attr('id');
			var pkg = null;

			try {
				pkg = getPackage();
			} catch (e) {
				return;
			}

			if (! pkg.hasEvent()) {
				alert("Request has no events currently associated.");
				return;
			}

			pkg.removeEvent();

			if (pkg.hasStation() === false && pkg.hasEvent() === false) {
				remove(id);
			}

			var cb = getCallbacks("onDeleteEvents");
			for(var key in cb) cb[key]();
		});

		_controlDiv.find('#' + id + '-delete-stations').button().bind("click", function(item){
			var id = $(item.target).parent("div").attr('id');
			var pkg = null;

			try {
				pkg = getPackage();
			} catch (e) {
				return;
			}

			if (! pkg.hasStation()) {
				alert("Request has no stations currently associated.");
				return;
			}

			pkg.removeStation();
			if (pkg.hasStation() === false && pkg.hasEvent() === false) {
				remove(id);
			}

			var cb = getCallbacks("onDeleteStations");
			for(var key in cb) cb[key]();
		});

		_controlDiv.find('#' + id + '-save-stations').button().bind("click", function(item){
			var id = $(item.target).parent("div").attr('id');
			var pkg = null;

			try {
				pkg = getPackage();
			} catch (e) {
				return;
			}

			if (! pkg.hasStation()) {
				alert("Request has no stations currently associated.");
				return;
			}

			pkg.saveStation();
		});

		_controlDiv.find('#' + id + '-freeze').button().bind("click", function(item){
			var id = $(item.target).parent("div").attr('id');
			var pkg = null;

			try {
				pkg = getPackage();
			} catch (e) {
				return;
			}

			pkg.freeze($(item.target).parent("div"));
		});
	}

	function render() {
		// This is to help on the rendering of the events.
		// It was used when we had multiple packages. Now it 
		// is hardcoded here to not change the rendering and the 
		// Id of the objects used to control the widgets.
		var id = "theone";

		/*
		 * Create the pack controls
		 */
		var html = '';
		var size = 150; // Default size for tables ?
		var datapack = undefined;
		try {
			datapack = getPackage();
		} catch (e) {
			wiConsole.error("request.js: No request loaded to render.");
		}

		/*
		 * We make sure that it is not rendered ... 
		 */
		// This should be the package id
		if (_controlDiv.find("#" + id).length === 0) {
			var exportURL = configurationProxy.serviceRoot() + 'metadata/export';
			html += '<div class="wi-request-pack-div" id="' + id + '">';

			html += '<input style="float: right;" id="' + id + '-delete-events" type="button" value="Delete Events" />';
			html += '<input style="float: right;" id="' + id + '-save-stations" type="button" value="Save Stations" />';
			html += '<input style="float: right;" id="' + id + '-delete-stations" type="button" value="Delete Stations" />';
			html += '<input style="float: right;" id="' + id + '-freeze" type="button" value="Freeze" />';
			html += '<form id="exportForm" name="exportForm" action="' + exportURL + '" target="exportIframe" method="post" enctype="multipart/form-data">';
			html += '<input type="text" name="streams" value="" style="display: none;" />';
			html += '</form>';
			html += '<iframe name="exportIframe" src="#" style="display: none;" ></iframe>';

			html += '<div style="float: left;"><h2>Request: </h2></div>';
			html += '<br class="wi-clear"/>';

			html += '<div style="padding-left: 10px;">'

			// Add the Events table
			html += '<h3>Events (<span id="' + id + '-events-count"></span>)</h3>';
			html += '<div id="' + id + '-events-div" style="width: 100%; max-height: 180px; overflow: auto; margin: 0 0 10px 0;"></div>';

			// Add the Stations table
			html += '<h3>Stations (<span id="' + id + '-stations-count"></span>)</h3>';
			html += '<div id="' + id + '-stations-div" style="width: 100%; max-height: 270px; overflow: auto; margin: 0 0 10px 0;"></div>';

			html += '</div>';

			html += '</div>';

			/*
			 * Insert the controls back to the end of requests
			 */
			_controlDiv.find("#requestControlTables").append(html);

			/*
			 * Activate the generated HTML controls
			 */
			connect(id);
		}

		/*
		 * Call the pack renders
		 */
		datapack.renderEvent(_controlDiv.find("#" + id + "-events-div"), _controlDiv.find("#" + id + "-events-count"));
		datapack.renderStation(_controlDiv.find("#" + id + "-stations-div"), _controlDiv.find("#" + id + "-stations-count"));
	}

	function _presets(param) {
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

	function _submit(info) {
		wiConsole.info("Fetching the list of time windows...");
		wiService.metadata.timewindows(function(tw) {
			wiConsole.info("...done");

			if (tw.length > 0) {
				info.request.timewindows = JSON.stringify(tw);

				if (info.review) {
					wiRequestReviewControl.review(info.request,
						function() {
							wiFDSNWS_Control.submitRequest($.extend(info.request, _presets(info.request)));
							return true;
						},
						function() {
							return confirm("Discard request?");
						}
					)
				} else {
					wiFDSNWS_Control.submitRequest($.extend(info.request, _presets(info.request)));
				}
			}
			else {
				wiConsole.warning("None of the requested streams were available in the given time period.");
			}
		}, function(jqxhr) {
			if (jqxhr.status == 500)
				var err = jqxhr.statusText;
			else
				var err = jqxhr.responseText;

			// Display a more user-friendly alert box in the common case
			if (err == "maximum request size exceeded") {
				var totalLineLimit = configurationProxy.value('request.totalLineLimit', 10000);
				alert("Limit of " + totalLineLimit + " traces exceeded.\n\nPlease deselect some stations, streams and/or events.");
				return;
			}

			wiConsole.error("Failed to get timewindows: " + err);
		}, true, info.timewindow);
	}

	// Public
	/*
	 * Methods to handle the connection with the Pack object.
	 * In this implementation I tried to hide the Pack object
	 * from outside so all calls for information are done
	 * through the requestControl method.
	 */
	this.appendEvent = function(event_data) {
		var node = null;

		try {
			node = getPackage();
		} catch (e) {
			node = newPackage();
		}
		if (!node) throw new RequestError("request.js: Cannot create a new request.");

		node.addEvent(event_data);

		render();

		var cb = getCallbacks("onAddEvents");
		for(var key in cb) cb[key]();
	};

	this.appendStation = function(station_data) {
		var node = null;
		try {
			node = getPackage();
		} catch (e) {
			node = newPackage();
		}
		if (!node) throw new RequestError("request.js: Cannot create a new request.")

		node.addStation(station_data);

		render();

		var cb = getCallbacks("onAddStations");
		for(var key in cb) cb[key]();
	};

	this.hasEvent = function() {
		return getPackage().hasEvent();
	};

	this.hasStation = function() {
		return getPackage().hasStation();
	};

	this.eventLines = function() {
		return getPackage().eventLines();
	};

	this.stationLines = function() {
		return getPackage().stationLines();
	};

	this.toggleEvent = function(id) {
		return getPackage().toggleEvent(id);
	};

	this.toggleStation = function(id) {
		return getPackage().toggleStation(id);
	};

	/*
	 * requestControl public methods
	 */
	this.submit = function(submit_info) {
		// Check that timewindow mode fits packages ...
		var pkg = getPackage();

		// Reject package without stations
		if ( ! pkg.hasStation() ) {
			alert("Cannot submit Request: it has no station list associated.\n\nPlease associate one station list to this package.");
			return;
		}

		// Reject package without events when relative mode
		if ( submit_info.mode === "Relative" && ! pkg.hasEvent() ) {
			alert("Cannot submit Request: it has no events associated.\n\nYou cannot use relative time windows with requests without events associated. Please associate one event list to this request.");
			return;
		}

		// Run the requests through the timewindows method
		var info = { };

		// Deep copy of the the submit_info.timewindow object
		$.extend(true, info, submit_info);

		// Add stations
		info.timewindow.streams = JSON.stringify(pkg.stationLines());

		// Add events only if needed
		if (submit_info.mode === "Relative") {
			info.timewindow.events  = JSON.stringify(pkg.eventLines());
		}

		// Add request description. This will be used for:
		// * status list item;
		// * title of status popup window;
		// * part of filename when downloading;
		// * SEED request label.
		info.request.description = "Package " + pkg.id();

		// Send for processing
		_submit(info);
	};

	// Load the main module
	load(htmlTagId);

	this.bind = function(name, method) {
		var valid = [ "onAddEvents", "onAddStations", "onDeleteEvents", "onDeleteStations", "onSaveStations" ]

		// The functions registered here will be called when the user 
		if (valid.indexOf(name) === -1) {
			throw new WIError("Invalid callback name " + name);
		}

		if (typeof _callbacks[name] === "undefined") _callbacks[name] = [];

		_callbacks[name].push(method);
	};

	function getCallbacks(name) {
		if (typeof _callbacks[name] === "undefined" ) return [];
		return _callbacks[name];
	}

};

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.RequestError = function(message) {
				this.message = message;
			//	this.name = "RequestErrorException";
			};

			window.RequestError.prototype = new WIError;
			window.requestControl = new RequestControl("#wi-RequestManagerControl");
			resolve();
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("request.js: " + e.message);

			wiConsole.error("request.js: " + e.message, e);
			reject();
		}
	});
}
