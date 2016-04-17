/*
 * GEOFON WebInterface
 *
 * station.js module: set up a control module to bring channels to the request.
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, GFZ Potsdam
 *
 */

var persistentNetwork = undefined;
var persistentStation = undefined;

/*
 * Implementation of the stationSearchControl
 */
function StationSearchControl(htmlTagId) {
	//
	// Private
	//
	var _controlDiv = null;
	var _dont_trigger = false;

	var _network_types = undefined;
	var _sensor_types  = undefined;
	var _network_list  = undefined;
	var _station_list  = undefined;
	var _stream_list   = undefined;

	// URL builders
	function buildNetworkURL(start, end, networktype) {
		var options = { };
		if (typeof start !== "undefined" && start !== null) options.start=start;
		if (typeof end && end !== null) options.end=end;
		if (typeof networktype && networktype !== null) options.networktype=networktype;

		return { url: _url_networks, options: options }
	}

	function buildStationURL(start, end, networktype, network) {
		var options = { };
		if (typeof start !== "undefined" && start !== null) options.start=start;
		if (typeof end && end !== null) options.end=end;
		if (typeof networktype && networktype !== null) options.networktype=networktype;
		if (typeof network && network !== null) options.network=network;

		return { url: _url_stations, options: options};
	}

	function buildStreamURL(start, end, networktype, network, station) {
		var options = { };
		if (typeof start !== "undefined" && start !== null) options.start=start;
		if (typeof end && end !== null) options.end=end;
		if (typeof networktype && networktype !== null) options.networktype=networktype;
		if (typeof network && network !== null) options.network=network;
		if (typeof station && station !== null) options.station=station;

		return { url: _url_streams, options: options};
	}

	// Loaders
	function loadNetworkTypes() {
		if (_dont_trigger) return;
		if (interfaceLoader.debug()) console.error("Load Networks Types");

		makeGenericSelect(_controlDiv.find("#sscNetworkTypeDiv"), "sscNetworkType", "Loading ... ");
		wiService.metadata.networktypes(function(data) {
			fillNetworkType(data);
			loadNetworkList();
		}, null, true, {});
	}

	function loadSensorType() {
		if (_dont_trigger) return;
		if (interfaceLoader.debug()) console.error("Load Sensor type");

		makeGenericSelect(_controlDiv.find("#sscSensorTypeDiv"), "sscSensorType", "Loading ... ");
		wiService.metadata.sensortypes(fillSensorType, null, true, {});
	}

	function loadStreamList() {
		if (_dont_trigger) return;
		if (interfaceLoader.debug()) console.error('Loading Stream List');

		// Loading message
		makeMultiGenericSelect(_controlDiv.find("#sscStreamListDiv"), "sscStreamList", '100px', "Loading ...");

		// Find the parameters to query
		var start = _controlDiv.find("#sscYear").slider('values',0);
		var end   =   _controlDiv.find("#sscYear").slider('values',1);
		var networktype =_controlDiv.find("#sscNetworkType option:selected").val();
		var network = _controlDiv.find("#sscNetworkList option:selected").val();
		var station = _controlDiv.find("#sscStationList option:selected").val();

		_stream_list = Array();

		// Trigger the request
		wiService.metadata.streams(fillStreamList, function() {
			makeMultiGenericSelect(_controlDiv.find("#sscStreamListDiv"), "sscStreamList", '100px', "Failed to load data !");
		}, true, start, end, networktype, network, station);
	}

	function loadStationList() {
		if (_dont_trigger) return;
		if (interfaceLoader.debug()) console.error('Loading Station List');

		// Loading message
		makeGenericSelect(_controlDiv.find("#sscStationListDiv"), "sscStationList", "Loading ...");

		// Find the parameters to query
		var start = _controlDiv.find("#sscYear").slider('values',0);
		var end   =   _controlDiv.find("#sscYear").slider('values',1);
		var networktype =_controlDiv.find("#sscNetworkType option:selected").val();
		var network = _controlDiv.find("#sscNetworkList option:selected").val();

		_station_list = Array();
		_stream_list = Array();

		// Trigger the request
		wiService.metadata.stations(function(data) {
			fillStationList(data);
			loadStreamList();
		}, function() {
			makeGenericSelect(_controlDiv.find("#sscStationListDiv"), "sscStationList", "Failed to load data !");
			makeMultiGenericSelect(_controlDiv.find("#sscStreamListDiv"), "sscStreamList", '100px', "Failed to load data !");
		}, true, start, end, networktype, network);
	}

	function loadNetworkList() {
		if (_dont_trigger) return;

		if (interfaceLoader.debug()) console.error('Loading Network List');

		// Save actual selections to preserve them (if posible) after resetting lists
		persistentNetwork = _controlDiv.find("#sscNetworkList option:selected").val();
		persistentStation = _controlDiv.find("#sscStationList option:selected").val();

		makeGenericSelect(_controlDiv.find("#sscNetworkListDiv"), "sscNetworkList", "Loading ... ");
		makeGenericSelect(_controlDiv.find("#sscStationListDiv"), "sscStationList", "Loading ... ");
		makeMultiGenericSelect(_controlDiv.find("#sscStreamListDiv"), "sscStreamList", '100px', "Loading ... ");

		// Find the parameters to query
		var start = _controlDiv.find("#sscYear").slider('values',0);
		var end   =   _controlDiv.find("#sscYear").slider('values',1);
		var networktype =_controlDiv.find("#sscNetworkType option:selected").val();

		// Reset the data current loaded
		_network_list = Array();
		_station_list = Array();
		_stream_list = Array();

		// Trigger the request
		wiService.metadata.networks(function(data) {
			fillNetworkList(data);
			loadStationList();
		}, function() {
			makeGenericSelect(_controlDiv.find("#sscNetworkListDiv"), "sscNetworkList", "Failed to load data !");
			makeGenericSelect(_controlDiv.find("#sscStationListDiv"), "sscStationList", "Failed to load data !");
			makeMultiGenericSelect(_controlDiv.find("#sscStreamListDiv"), "sscStreamList", '100px', "Failed to load data !");
		}, true, start, end, networktype);

	}

	// Selects
	function makeMultiGenericSelect(container, id, height, message) {
		_controlDiv.find("#" + id).remove();
		var html = '<select multiple="multiple" id="' + id + '" style="width: 100%; height: ' + height + ';">';
		html += "<option>" + message + "</option>";
		html += "</select>";
		container.append(html);
	}

	function makeMultiSelectFromArray(data, container, id, height) {
		_controlDiv.find("#" + id).remove();
		var html = '<select multiple="multiple" id="' + id + '" style="width: 100%;" height: ' + height + ';">';
		var first = 'selected="selected"';
		for(var key in data) {
			var item = data[key];
			if (typeof(item) === "string" ) {
				html += '<option ' + first + ' value="' + item + '">' + item + '</option>';
			} else {
				html += '<option ' + first + ' value="' + item[0] + '">' + item[1] + '</option>';
			}
			first = "";
		}
		html += "</select>";
		container.append(html);
	}

	function makeSelectFromArray(data, container, id) {
		// We return a list of IDS loaded into the select
		var ids = Array();

		// Clean the current one
		_controlDiv.find("#" + id).remove();

		// Build the complete select
		var html = '';
		var first = 'selected="selected"';
		html += "<select style='font-family: monospace; width: 100%;' id='" + id + "'>";
		for(var key in data) {
			// item = data[key]; // Fails in IE8 but not others.
			var item = data[key];

			html += '<option ' + first + ' value="' + item[0] + '">' + (item[1]).replace(/ /g, "&nbsp;") + '</option>';
			// Save the id
			ids.push(item[0]);
			// Only the first is selected
			first = "";
		}
		html += "</select>";

		// Insert
		container.append(html);

		return ids;
	}

	function makeGenericSelect(container, id, message) {
		// Clean the existing
		_controlDiv.find("#" + id).remove();

		// Prepare the replacement
		var html = "<select style='font-family: monospace; width: 100%' id='" + id + "'>";
		html += "<option value=''>" + message + "</option>";
		html += "</select>";

		// Put it in
		container.append(html);
	}

	// Fillers
	function fillNetworkType(data) {
		if (_controlDiv === null) return;
		if (!data) return;

		if (interfaceLoader.debug()) console.error('Fill Netowrk Type');

		_network_types = data;

		// Find the right DIV
		var div = _controlDiv.find('#sscNetworkTypeDiv');

		// Create the select inside
		makeSelectFromArray(_network_types, div, "sscNetworkType");

		// Re-connect the signal
		_controlDiv.find("#sscNetworkType").bind("change", function() {
			loadNetworkList();
		});

		return;
	}

	function fillSensorType(data) {
		if (_controlDiv === null) return;
		if (!data) return;

		_sensor_types = data;

		if (interfaceLoader.debug()) console.error('Fill Sensor Type');

		// Find the DIV
		var div = _controlDiv.find('#sscSensorTypeDiv');

		// Re-create the select
		makeSelectFromArray(_sensor_types, div, "sscSensorType");

		return;
	}

	function fillNetworkList(data) {
		if (_controlDiv === null) return;
		if (!data) return;

		if (interfaceLoader.debug()) console.error('Fill Network');

		_network_list = data;

		// Find the DIV
		var div = _controlDiv.find('#sscNetworkListDiv');

		// Re-create the select
		makeSelectFromArray(_network_list, div, "sscNetworkList");

		// Try to select the same network as before if posible
		_controlDiv.find('#sscNetworkList option[value="' + persistentNetwork + '"]').prop('selected', true)

		// Re-connects
		_controlDiv.find("#sscNetworkList").bind("change", function() {
			loadStationList();
		});

		return;
	}

	function fillStationList(data) {
		if (_controlDiv === null) return;
		if (!data) return;

		if (interfaceLoader.debug()) console.error('Fill Station');

		_station_list = data;

		// Find the DIV
		var div = _controlDiv.find('#sscStationListDiv');

		makeSelectFromArray(_station_list, div, "sscStationList");

		// Try to select the same station as before if posible
		_controlDiv.find('#sscStationList option[value="' + persistentStation + '"]').prop('selected', true)
		// and update the value with the selected station
		persistentStation = _controlDiv.find('#sscStationList option:selected').val()

		// Re-connect
		_controlDiv.find("#sscStationList").bind("change", function() {
			// reselectNetworkList();
			loadStreamList();
		});

		return;
	}

	function fillStreamList(data) {
		if (_controlDiv === null) return;
		if (!data) return;

		if (interfaceLoader.debug()) console.error('Fill Stream');

		var div = _controlDiv.find("#sscStreamListDiv");

		_stream_list = data;

		makeMultiSelectFromArray(_stream_list, div, "sscStreamList", '100px');
		_controlDiv.find('#sscStreamList option').attr('selected', 'selected');
	}

	function reselectNetworkList() {
		if (_controlDiv === null) return;

		if (interfaceLoader.debug()) console.error('Reselect network');

		var currentStation    = _controlDiv.find("#sscStationList option:selected").val();
		var currentStationNet = currentStation.substr(0,12);

		_controlDiv.find("#sscNetworkList").val(currentStationNet);
	}

	function query() {
		if ( _controlDiv === null ) return;

		// 
		// Initialize all variables
		// 

		// Network
		var start = undefined;
		var end   = undefined;
		var networktype = undefined;
		var network = undefined;

		// Network
		// Code
		var station = undefined;

		// Region
		var minlat  = undefined;
		var maxlat  = undefined;
		var minlon  = undefined;
		var maxlon  = undefined;

		// Events
		var minradius = undefined;
		var maxradius = undefined;
		var minazimuth  = undefined;
		var maxazimuth  = undefined;

		// Streams
		// Code
		var streams = undefined;

		// Sampling
		var sensortype   = undefined;
		var preferredsps  = undefined;

		// Need to implement those
		var events = undefined;

		//
		// Collect the information from the page
		//
		start      = _controlDiv.find("#sscYear").slider("values", 0);
		end        = _controlDiv.find("#sscYear").slider("values", 1);
		networktype= _controlDiv.find("#sscNetworkType").val();
		network    =  _controlDiv.find("#sscNetworkList").val();

		var stationMode = _controlDiv.find("#sscStationSelectionMode input:checked").val();
		if (stationMode === "Code") {
			station = _controlDiv.find("#sscStationList").val();
		} else if (stationMode === "Region") {
			minlat  = _controlDiv.find("#sscLatitudeMin").val();
			maxlat  = _controlDiv.find("#sscLatitudeMax").val();
			minlon  = _controlDiv.find("#sscLongitudeMin").val();
			maxlon  = _controlDiv.find("#sscLongitudeMax").val();
		} else if (stationMode === "Events") {
			minradius = _controlDiv.find("#sscDistance").slider("values",0);
			maxradius = _controlDiv.find("#sscDistance").slider("values",1);
			minazimuth  = _controlDiv.find("#sscAzimuth").slider("values",0);
			maxazimuth  = _controlDiv.find("#sscAzimuth").slider("values",1);
		}

		var streamMode  = _controlDiv.find("#sscStreamMode input:checked").val();
		if (streamMode === "Code") {
			streams = _controlDiv.find("#sscStreamList").val();
			if (!streams) {
				alert("No channels selected");
				return;
			}
			streams = streams.toString();
		} else if (streamMode === "Sps") {
			sensortype = _controlDiv.find("#sscSensorType").val();
			preferredsps        = _controlDiv.find("#sscSamplingRate").slider('value');
		}

		/*
		 * Depending on the stationMode a different approach to load stations should be used
		 */
		if (stationMode === "Events") {
			try {
				if (! requestControl.hasEvent()) {
					wiConsole.notice("Request has no events associated.");
					return;
				}

				// Find the events lines associated (and selected) with 
				// the current package.
				events = requestControl.eventLines();

				// Check that we have at least one event
				if (events.length === 0) { 
					wiConsole.notice("Request has no events lines selected.");
					return;
				}

				// to JSON string for submission
				events = JSON.stringify(events);
			} catch (e) {
				wiConsole.error(e.message);
				return;
			}
		}

		// One query for each selected package
		wiService.metadata.query(function(data, statustext, jqxhr) {
			if (jqxhr.status == 204) {
				alert("Got no stations for the selected day and options");
			}
			else {
				requestControl.appendStation(data);
				_controlDiv.find("#sscSearch").button("option", "label", "Append");
			}
		}, null, true, start, end,
				network, networktype, station, sensortype,
				preferredsps, streams, minlat, maxlat, minlon,
				maxlon, minradius, maxradius, minazimuth, 
				maxazimuth, events);
	}

	// Reseters
	function resetCoordinates() {
		if ( _controlDiv === null ) return;

		// Disabled updates on webpage
		_dont_trigger = true;

		// Coordinates
		_controlDiv.find("#sscLatitudeMin").val("-90");
		_controlDiv.find("#sscLatitudeMax").val("90");
		_controlDiv.find("#sscLongitudeMin").val("-180");
		_controlDiv.find("#sscLongitudeMax").val("180");

		// Ask to clear the select
		if (mapControl.enabled())
			mapControl.clearSelect();

		// Enable trigger again
		_dont_trigger = false;
	}

	function resetControl() {
		if ( _controlDiv === null ) return;

		// Disabled updates on webpage
		_dont_trigger = true;

		// Restore event sliders
		_controlDiv.find("#sscAzimuth").slider('values', [0,360]);
		_controlDiv.find("#sscDistance").slider('values', [0,180]);

		// Restore year slider
		// This will make the network list to update itself twice :(
		var year = _controlDiv.find("#sscYear");
		year.slider('values', [ year.slider('option','min'), year.slider('option', 'max')]);

		_controlDiv.find("#sscStationModeCatalog").click()
		_controlDiv.find("#sscStationSelectionModeCode").click()
		_controlDiv.find("#sscStreamModeCode").click();

		_controlDiv.find("#sscSamplingRate").slider('value',20.0);

		// Enable trigger again
		_dont_trigger = false;

		// Reset the coordinates
		resetCoordinates();

		// Restoring all ... 

		// Restore the Network Type
		loadNetworkTypes();

		// Restore sensor Type
		loadSensorType();
	}

	// Parsers & Utils (sometimes replicates methods on other classes
	function validateCoordinates() {
		var bottom = _controlDiv.find("#sscLatitudeMin").val();
		var top    = _controlDiv.find("#sscLatitudeMax").val();
		var left   = _controlDiv.find("#sscLongitudeMin").val();
		var right  = _controlDiv.find("#sscLongitudeMax").val();

		if (Number(bottom) >= Number(top)) {
			alert("Invalid latitude interval.");
			return;
		}

		// Update the map
		if (mapControl.enabled()) mapControl.setSelect(bottom, left, top, right);
	}

	function checkNumber(value, min, max) {
		if (value === "") return null;

		value = Number(value);

		if (isNaN(value)) return null;

		if (value < min) return null;
		if (value > max) return null;

		return value;
	}

	// Main toolbar render
	function buildControl() {
		if ( _controlDiv === null ) return;

		//
		// Create the controls
		//
		var html='';

		html += '<h3>Station Information</h3>';
		html += '<div id="sscStationMode" align="center">';
		html += '<input type="radio" value="Catalog" id="sscStationModeCatalog" name="sscStationMode" /><label for="sscStationModeCatalog">Browse Inventory</label>';
		html += '<input type="radio" value="File" id="sscStationModeFile" name="sscStationMode" /><label for="sscStationModeFile">User Supplied</label>';
		html += '</div>';

		html += '<div id="sscStationDiv">';
		html += '<div style="padding: 8px;" id="sscStationCatalogDiv"></div>';
		html += '<div style="padding: 8px; text-align: center;" id="sscStationFileDiv"></div>';
		html += '<div style="padding: 8px; text-align: center; background: pink;" id="sscStationPresetDiv">[CLICK HERE!]</div>';
		html += '</div>';

		_controlDiv.append(html);

		// Catalog
		_controlDiv.find("#sscUserCatalog").button().bind('click', function() {
			$("#sscChannelLoader").dialog('open');
		});

		/*
		 * Normal Pre-Defined Catalog Search Controls
		 */
		html = '';
		html += "<h3>Networks</h3>";
		html += '<div class="wi-control-item-first">';
		html += '<div class="wi-spacer">Year from <u><span id="sscStart"></span></u> to <u><span id="sscEnd"></span></u>:</div>';
		html += '<div id="sscYear"></div>';
		html += '</div>';

		// Here we just create the div placeholders for the selects ....
		html += "<div class='wi-control-item'>";
		html += "<div class='wi-spacer'>Network Type:</div>";
		html += "<div id='sscNetworkTypeDiv'></div>";
		html += "</div>";

		html += "<div class='wi-control-item'>";
		html += "<div class='wi-spacer'>Network Code:</div>";
		html += "<div id='sscNetworkListDiv'></div>";
		html += "* = temporary network; + = restricted access";
		html += "</div>";

		// Stations Placeholders
		html += "<h3>Stations</h3>";
		html += "<div class='wi-control-item'>";

		html += '<div class="wi-spacer" id="sscStationSelectionMode" align="center">';
		html += '<input type="radio" value="Code" id="sscStationSelectionModeCode" name="sscStationSelectionMode" /><label for="sscStationSelectionModeCode">by Code</label>';
		html += '<input type="radio" value="Region" id="sscStationSelectionModeRegion" name="sscStationSelectionMode" /><label for="sscStationSelectionModeRegion">by Region</label>';
		html += '<input type="radio" value="Events" id="sscStationSelectionModeEvents" name="sscStationSelectionMode" /><label for="sscStationSelectionModeEvents">by Events</label>';
		html += '</div>';

		html += '<div id="sscStationSelectionDiv">';
		html += '<div style="padding: 10px;" id="sscStationSelectionCodeDiv"></div>';
		html += '<div style="padding: 10px;" id="sscStationSelectionRegionDiv"></div>';
		html += '<div style="padding: 10px;" id="sscStationSelectionEventsDiv"></div>';
		html += '</div>';

		html += '</div>';

		// Streams Placeholders
		html += "<h3>Streams</h3>";
		html += "<div class='wi-control-item'>";

		html += '<div id="sscStreamMode" align="center">';
		html += '<input type="radio" value="Code" id="sscStreamModeCode" name="sscStreamMode" /><label for="sscStreamModeCode">by Code</label>';
		html += '<input type="radio" value="Sps" id="sscStreamModeSps" name="sscStreamMode" /><label for="sscStreamModeSps">by Sampling</label>';
		html += '</div>';

		html += '<div id="sscStreamDiv">';
		html += "<div style='padding: 10px;' id='sscStreamCodeDiv'></div>";
		html += '<div style="padding: 10px;" id="sscStreamSpsDiv"></div>';
		html += '</div>';

		html += '<div class="wi-control-item-last">';
		html += '<input id="sscReset" class="wi-inline" type="button" value="Reset" />';
		html += '<input id="sscSearch" class="wi-inline" type="button" value="Search" />';
		html += '</div>';
		html += '</div>';


		// Append the standard Inventory Control
		_controlDiv.find("#sscStationCatalogDiv").append(html);

		requestControl.bind("onDeleteStations", function() {
			_controlDiv.find("#sscSearch").button("option", "label", "Search");
		})

		html = '<div class="wi-spacer">'
		// Form to upload the file with the station list
		var importURL = configurationProxy.serviceRoot() + 'metadata/import';
		html += '<form id="importForm" name="importForm" action="' + importURL + '" target="importIframe" method="post" enctype="multipart/form-data">';
		html += '<input type="file" name="file" value="" class="wi-inline-full" />';
		html += '<div style="padding: 8px; text-align: left;" class="wi-spacer"><br>You can upload <i>text</i> files in one of the following two formats:<ul><li>A list of stations previously saved here. (Use the "Save Stations"  button in the "Event and Station List").</li><li>A file retrieved from any FDSN compliant fdsnws-station Web Service in text format.</li></ul></div><br>'
		html += '<input id="sscSendList" class="wi-inline" type="submit" value="Send List" />';
		html += '</form>';
		html += '<iframe name="importIframe" src="#" style="display: none;" ></iframe>';

		html += '</div>';
		_controlDiv.find("#sscStationFileDiv").append(html)

		_controlDiv.find("#importForm").submit(function () {
			var formdata = new FormData($(this)[0]);
			$.ajax({
				url: importURL,
				type: 'POST',
				data: formdata,
				processData: false,
				encType: 'multipart/form-data',
				contentType: false,
				success: function (returndata, textStatus, jqxhr) {
					if (jqxhr.status == 204) {
						alert("Got no stations from the uploaded file.\nHas the file the proper format?");
					}
					else {
						var data = (returndata !== undefined)? $.parseJSON(returndata): undefined
						requestControl.appendStation(data);
					}
				},
				error: function(){
					wiConsole.notice("Something went wrong with AJAX");
				}
			});
			return false;
		});

		/*
		 * Station Mechanism Mode
		 */
		_controlDiv.find("#sscStationMode").buttonset();
		_controlDiv.find("#sscStationMode").change(function(item) {
			_controlDiv.find("#sscStationDiv").children("div").hide();
			_controlDiv.find("#sscStation" + ($(item.target).val()) + 'Div').show();
		});


		// Station Controls by Code
		html  = '<div class="wi-spacer">Filter stations by station code:</div>';
		html += '<div id="sscStationListDiv"></div>';
		_controlDiv.find("#sscStationSelectionCodeDiv").append(html);

		// Station Controls by Region
		html  = '<div class="wi-spacer">Filter stations by region:</div>';
		html += '<div style="position: relative; text-align: center;">';
		html += 'N<br/>';
		html += '<input style="text-align: center; width: 50px; margin: .5em;" id="sscLatitudeMax" value="" title="Northernmost latitude for the region of interest (-90&#176; to 90&#176;)"><br/>';
		html += 'W<input style="text-align: center; width: 50px; margin: .5em 1.5em .5em .5em;" id="sscLongitudeMin" value="" title="Westernmost longitude for the region of interest (-180 to 180 degrees)">';
		html += '<input style="text-align: center; width: 50px; margin: .5em .5em .5em 1.5em;" id="sscLongitudeMax" value="" title="Easternmost longitude for the region of interest (-180&deg; to 180&deg;)"/>E<br/>';
		html += '<input style="text-align: center; width: 50px; margin: .5em;" id="sscLatitudeMin" value="" title="Southernmost latitude for the region of interest (-90&#176; to 90&#176;)">';
		html += '<br/>S';
		html += '<input style="position: absolute; bottom: 2em; right: 0;" type="button" id="sscCoordinateReset" value="Clear" />';
		html += '</div>';
		_controlDiv.find("#sscStationSelectionRegionDiv").append(html);

		// Station Controls by Events
		html = '<div class="wi-spacer">Filter stations by:</div>';
		html += '<div class="wi-spacer">Event Distance (<u><span id="sscDistanceMin"></span></u> to <u><span id="sscDistanceMax"></span></u> degrees)</div>';
		html += '<div id="sscDistance"></div>';
		html += '<br />';
		html += '<div class="wi-spacer">Event Azimuth (<u><span id="sscAzimuthMin"></span></u> to <u><span id="sscAzimuthMax"></span></u> degrees)</div>';
		html += '<div id="sscAzimuth"></div>';
		_controlDiv.find("#sscStationSelectionEventsDiv").append(html);

		// Stream Controls by Code
		html = '<div>';
		html += '<div class="wi-spacer">Choose the desired set of channels:<br />Use SHIFT and CTRL to extend the set.</div>';
		html += '<div id="sscStreamListDiv"></div>'
		html += '</div>';
		_controlDiv.find("#sscStreamCodeDiv").append(html);

		// Stream Controls by Sampling Rate / Sensor Type
		html += "<div class='wi-spacer'>Sensor Type:</div>";
		html += "<div id='sscSensorTypeDiv'></div>";
		html += '<br />';
		html += '<div class="wi-spacer">Target Sampling rate: <u><span id="sscSamplingRateValue"></span></u> sps</div>';
		html += '<div class="wi-spacer" id="sscSamplingRate"></div>'
		_controlDiv.find("#sscStreamSpsDiv").append(html);

		// 
		// Bind controls & Special jQuery-ui controls
		//

		// Sampling rate
		_controlDiv.find("#sscSamplingRate").slider({
			min: 0,
			max: 150,
			step: 1,
			slide: function(event, ui) {
				_controlDiv.find('#sscSamplingRateValue').text( ui.value );
			},
			change: function(event, ui) {
				_controlDiv.find('#sscSamplingRateValue').text( ui.value );
			}
		});

		_controlDiv.find("#sscStreamMode").buttonset();
		_controlDiv.find("#sscStreamMode").change(function(item) {
			_controlDiv.find("#sscStreamDiv").children("div").hide();
			_controlDiv.find("#sscStream" + ($(item.target).val()) + 'Div').show();
		});

		// Station Selection Mode
		_controlDiv.find("#sscStationSelectionMode").buttonset();
		_controlDiv.find("#sscStationSelectionMode").change(function(item) {
			_controlDiv.find("#sscStationSelectionDiv").children("div").hide();
			_controlDiv.find("#sscStationSelection" + ($(item.target).val()) + 'Div').show();
		});

		// Year Slider
		var today = new Date();
		_controlDiv.find("#sscYear").slider({
			range: true,
			min: 1980,
			max: today.getFullYear(),
			step: 1,
			slide: function(event, ui) {
				_controlDiv.find('#sscStart').text( ui.values[0] );
				_controlDiv.find('#sscEnd').text( ui.values[1] );
			},
			change: function(event, ui) {
				_controlDiv.find('#sscStart').text( ui.values[0] );
				_controlDiv.find('#sscEnd').text( ui.values[1] );
				loadNetworkList();
			}
		});
		_controlDiv.find('#sscStart').text( _controlDiv.find("#sscYear").slider("values", 0) );
		_controlDiv.find('#sscEnd').text( _controlDiv.find("#sscYear").slider("values", 1) );

		// Stream List

		// Azimuth Control
		_controlDiv.find("#sscAzimuth").slider({
			range: true,
			min: 0,
			max: 360,
			step: 1,
			values: [ 0, 360 ],
			slide: function(event, ui) {
				_controlDiv.find('#sscAzimuthMin').text( ui.values[0] );
				_controlDiv.find('#sscAzimuthMax').text( ui.values[1] );
			},
			change: function(event, ui) {
				_controlDiv.find('#sscAzimuthMin').text( ui.values[0] );
				_controlDiv.find('#sscAzimuthMax').text( ui.values[1] );
			}
		});
		_controlDiv.find('#sscAzimuthMin').text( _controlDiv.find("#sscAzimuth").slider("values", 0) );
		_controlDiv.find('#sscAzimuthMax').text( _controlDiv.find("#sscAzimuth").slider("values", 1) );

		// Distance Control
		_controlDiv.find("#sscDistance").slider({
			range: true,
			min: 0.0,
			max: 180,
			step: 1,
			values: [ 0, 180 ],
			slide: function(event, ui) {
				_controlDiv.find('#sscDistanceMin').text( ui.values[0] );
				_controlDiv.find('#sscDistanceMax').text( ui.values[1] );
			},
			change: function(event, ui) {
				_controlDiv.find('#sscDistanceMin').text( ui.values[0] );
				_controlDiv.find('#sscDistanceMax').text( ui.values[1] );
			}
		});
		_controlDiv.find('#sscDistanceMin').text( _controlDiv.find("#sscDistance").slider("values", 0) );
		_controlDiv.find('#sscDistanceMax').text( _controlDiv.find("#sscDistance").slider("values", 1) );

		// Coordinates part
		_controlDiv.find("input[id*=sscLatitude]").bind("change", function(item) {
			var value = checkNumber($(item.target).val(),-90,90);
			if (value === null) {
				alert("Invalid latitude value, " + $(item.target).val());
				$(item.target).val('');
				return;
			}
			validateCoordinates();
		});

		_controlDiv.find("input[id*=sscLongitude]").bind("change", function(item) {
			var value = checkNumber($(item.target).val(),-180,180);
			if (value === null) {
				alert("Invalid longitude value, " + $(item.target).val());
				$(item.target).val('');
				return;
			}
			validateCoordinates();
		});

		_controlDiv.find("#sscCoordinateReset").button().bind("click", resetCoordinates);

		// Control Buttons
		_controlDiv.find("#sscReset").button().bind("click", resetControl);
		_controlDiv.find("#sscSearch").button().bind("click", query);
	}

	function load(htmlTagId) {
		var control = $(htmlTagId);

		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("station.js: Cannot find a div with class '" + htmlTagId + "'");
			return;
		}

		// Save the main control div
		_controlDiv = control;

		// Build
		buildControl();

		// Conect to the mapping 
		if (typeof mapControl !== "undefined") {
			mapControl.bind("onChangeExtend", function(bottom, left, top, right) {
				_controlDiv.find("#sscLatitudeMax").val(top);
				_controlDiv.find("#sscLatitudeMin").val(bottom);
				_controlDiv.find("#sscLongitudeMax").val(right);
				_controlDiv.find("#sscLongitudeMin").val(left);
				_controlDiv.find("#sscStationSelectionModeRegion").prop('checked',true);
				_controlDiv.find("#sscStationSelectionModeRegion").button("refresh");
				_controlDiv.find("#sscStationSelectionDiv").children("div").hide();
				_controlDiv.find("#sscStationSelectionRegionDiv").show();

			});
		}

		// Reset
		resetControl();
	}

	//
	// Public
	//

	//
	// Main implementation
	//
	load(htmlTagId)
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.stationSearchControl = new StationSearchControl("#wi-StationSearchControl");
			resolve();
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("station.js: " + e.message);

			wiConsole.error("station.js: " + e.message, e);
			reject();
		}
	});
}

