/*
 * GEOFON WebInterface
 *
 * events.js module: set up a control module to bring events to the page.
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, GFZ Potsdam
 *  June/July 2013
 *
 */

/*
 * Implementation of the eventSearchControl
 */
function EventSearchControl(htmlTagId) {
	//
	// Private
	//

	// The main <div> element where the controls will reside
	var _controlDiv = null;

	// The catalog list array
	var _catalogList = Array();

	function checkNumber(value, min, max) {
		if (value === "") return null;

		value = Number(value);

		if (isNaN(value)) return null;
		if (value < min) return null;
		if (value > max) return null;

		return value;
	}

	function fillCatalogList(cataloglist) {
		if ( _controlDiv === null ) return;
		if (!cataloglist) return;

		_catalogList = cataloglist;

		if (interfaceLoader.debug()) console.error("Catalog rebuild");

		var select = _controlDiv.find("#escCatalog");
		select.empty();

		for(var key in _catalogList) {
			var item = _catalogList[key];
			select.append('<option value="' + key + '">' + item.description + '</option>');
		}

		updateControlState();
	}

	function reloadCatalogs() {
		wiService.event.catalogs(fillCatalogList, null, true, {});
	}

	function validateCoordinates() {
		var bottom = _controlDiv.find("#escLatitudeMin").val();
		var top    = _controlDiv.find("#escLatitudeMax").val();
		var left   = _controlDiv.find("#escLongitudeMin").val();
		var right  = _controlDiv.find("#escLongitudeMax").val();

		if (Number(bottom) >= Number(top)) {
			alert("Invalid latitude interval.");
			return;
		}

		if (Number(left) >= Number(right)) {
			alert("Invalid longitude interval.");
			return;
		}

		// Update the map
		if (mapControl.enabled()) mapControl.setSelect(bottom, left, top, right);
	}

	// Called by the reset (on the coordinate area) button is triggered
	function resetCoordinates() {
		// Coordinates
		_controlDiv.find("#escLatitudeMin").val("-90");
		_controlDiv.find("#escLatitudeMax").val("90");
		_controlDiv.find("#escLongitudeMin").val("-180");
		_controlDiv.find("#escLongitudeMax").val("180");

		// Map select
		if (mapControl.enabled()) mapControl.clearSelect();
	}

	// Called by the main reset button is triggered
	function resetControl() {
		if (_controlDiv === null) return;

		// Magnitude
		var mag = configurationProxy.value('events.magnitudes.minimum', 4.0)
		_controlDiv.find( "#escMagnitudeSlider" ).slider("value", mag);

		// Depth Values
		var dmin = configurationProxy.value('events.depth.minimum', 0.0)
		var dmax = configurationProxy.value('events.depth.maximum', 1000.0)
		_controlDiv.find( "#escDepthSlider" ).slider("values", [dmin, dmax]);

		// Date interval.
		// NOTE: End date here means the last day on which events
		// should be sought. Events with a UTC date on this day should
		// be returned. In querying an FDSN-style web service, we need
		// to set the end parameter to the *end* of this day.
		var startoffset = configurationProxy.value("events.date.startoffset", "-7d");
		_controlDiv.find("#escStart").datepicker("setDate", startoffset);
		_controlDiv.find("#escEnd").datepicker("setDate", "now");

		// Reset catalog mode
		_controlDiv.find("#escEventModeCatalog").click();

		// Coordinate reset
		resetCoordinates();

		return;
	}

	function buildQueryURL(catalog, start, end, minmag, maxmag, mindepth, maxdepth, minlat, maxlat, minlon, maxlon, limit) {
		var options = { };

		options.catalog = undefined;

		options.start = undefined;
		options.end = undefined;

		options.minmag = undefined;
		options.maxmag = undefined;

		options.mindepth = undefined;
		options.maxdepth = undefined;

		options.minlat = undefined;
		options.minlon = undefined;
		options.maxlat = undefined;
		options.maxlon = undefined;

		options.limit = undefined;

		// HACK
		options.format= "json";
		options.catalog = catalog;

		// Check that we get catalog preferences
		var catalogPrefs = _catalogList[catalog];
		if (!catalogPrefs) {
			alert("Invalid Catalog.");
			return;
		}

		if (catalogPrefs.hasDate) {
			try {
				if (start !== undefined) start = $.datepicker.parseDate("yy-mm-dd", start);
			} catch (err) {
				alert(start + " is not a valid start date (" + err + ")");
				return;
			}

			try {
				if (end !== undefined) {
				    end = $.datepicker.parseDate("yy-mm-dd", end);
				    // We set the end date to the next day to make sure that the
				    // search will include the complete data for the chosen date.
				    end.setDate(end.getDate() + 1);
				}
			} catch (err) {
				alert(end + " is not a valid end date (" + err + ").");
				return;
			}

			if (start > end) {
				start = $.datepicker.formatDate("yy-mm-dd", start);
				end = $.datepicker.formatDate("yy-mm-dd", end);

				alert("Invalid date interval, " + start + " &gt; " + end + ".");
				return;
			}

			if ((start !== null) & (start !== undefined)) options.start= $.datepicker.formatDate("yy-mm-dd", start);
			if ((end   !== null) & (  end !== undefined)) options.end =  $.datepicker.formatDate("yy-mm-dd", end);
		}

		if (catalogPrefs.hasMagnitude) {
			if (minmag === null) {
				alert(_controlDiv.find('#escMagnitudeSlider').slider('value') + " is invalid as magnitude.");
				return;
			}
			if (minmag !== null) options.minmag=minmag;
			if (maxmag !== null) options.maxmag=maxmag;
		}

		if (catalogPrefs.hasDepth) {
			if (mindepth === null) {
				alert(_controlDiv.find('#escDepthSlider').slider('values',0) + " is invalid as depth.");
				return;
			}
			if (maxdepth === null) {
				alert(_controlDiv.find('#escDepthSlider').slider('values',1) + " is invalid as depth.")
				return;
			}
			if (mindepth >= maxdepth) {
				alert("Invalid depth interval, " + mindepth + " >= " + maxdepth + ".");
				return;
			}

			if (mindepth !== null) options.mindepth=mindepth;
			if (maxdepth !== null) options.maxdepth=maxdepth;
		}

		if (catalogPrefs.hasRectangle) {
			if (minlat === null) {
				alert(_controlDiv.find('#escLatitudeMin').val() + " is invalid as latitude.");
				return;
			}
			if (maxlat === null) {
				alert(_controlDiv.find('#escLatitudeMax').val() + " is invalid as latitude.")
				return;
			}
			if (minlon === null) {
				alert(_controlDiv.find('#escLongitudeMin').val() + " is invalid as longitude.");
				return;
			}
			if (maxlon === null) {
				alert(_controlDiv.find('#escLongitudeMax').val() + " is invalid as longitude.");
				return;
			}

			if (minlat >= maxlat) {
				alert("Invalid latitude interval, " + minlat + " >= " + maxlat + ".");
				return;
			}
			// FIXME: The following fails to allow for regions crossing the date line:
		    if ((minlon >= maxlon) && (maxlon !== null)) {
				alert("Invalid longitude interval, " + minlon + " >= " + maxlon + ".");
				return;
			}

			if (minlat !== null) options.minlat=minlat;
			if (minlon !== null) options.minlon=minlon;
			if (maxlat !== null) options.maxlat=maxlat;
			if (maxlon !== null) options.maxlon=maxlon;
			if (limit !== null) options.limit=limit;
		}

		return options;
	}

	// A quick "one-click" button to search for the last few events
	// with M>6.0.
	function quick6() {
		if (!_controlDiv) return;

		var start=undefined;
		var end=undefined;
		var catalog=_controlDiv.find('#escCatalog').val();
		var mindepth=0.001;
		var maxdepth=999.0;
		var minlat=checkNumber(_controlDiv.find('#escLatitudeMin').val(),-90,90);
		var maxlat=checkNumber(_controlDiv.find('#escLatitudeMax').val(),-90,90);
		var minlon=checkNumber(_controlDiv.find('#escLongitudeMin').val(),-180,180);
		var maxlon=checkNumber(_controlDiv.find('#escLongitudeMax').val(),-180,180);

		var options = buildQueryURL(catalog, start, end, 6.0, 10.0, mindepth, maxdepth, minlat, maxlat, minlon, maxlon, 10);
		if (typeof options === "undefined") return;

		wiService.event.query(function(data, statustext, jqxhr) {
		    if (jqxhr.status == 204) {
			alert("Got no events for the selected day and options");
			wiConsole.notice("Got no events for the selected day and options: " + $.param(options));
		    } else {
			requestControl.appendEvent(data);
			_controlDiv.find("#escSearch").button("option", "label", "Append");
		    }
		}, null, true, options);
	}

	// Called when Search button is used
	function query() {
		if (!_controlDiv) return;

		// Get and parse the values currently on the page
		var start=_controlDiv.find('#escStart').val();
		var end=_controlDiv.find('#escEnd').val();
		var catalog=_controlDiv.find('#escCatalog').val();
		var minmag=checkNumber(_controlDiv.find('#escMagnitudeSlider').slider('value'), -2, 10);
		var mindepth=checkNumber(_controlDiv.find('#escDepthSlider').slider('values',0), -15, 1000);
		var maxdepth=checkNumber(_controlDiv.find('#escDepthSlider').slider('values',1), -15, 1000);
		var minlat=checkNumber(_controlDiv.find('#escLatitudeMin').val(),-90,90);
		var maxlat=checkNumber(_controlDiv.find('#escLatitudeMax').val(),-90,90);
		var minlon=checkNumber(_controlDiv.find('#escLongitudeMin').val(),-180,180);
		var maxlon=checkNumber(_controlDiv.find('#escLongitudeMax').val(),-180,180);

		// Since the Page does not implement a maxmag we hardcode a value of 10. Bugfix: a value of 12 or 11 crashes everthing (JQ)
		var options = buildQueryURL(catalog, start, end, minmag, 10.0, mindepth, maxdepth, minlat, maxlat, minlon, maxlon, null);
		if (typeof options === "undefined") return;

		// So far no event query depends on the selected station list
		// when this happens the loop over selected packages should 
		// be done here and the pushEventDatafn should be used instead of the
		// pushEventDataSimplefn as done today.
		wiService.event.query(function(data, statustext, jqxhr) {
			if (jqxhr.status == 204) {
				alert("Got no events for the selected day and options");
				wiConsole.notice("Got no events for the selected day and options: " + $.param(options));
			}
			else {
				requestControl.appendEvent(data);
				_controlDiv.find("#escSearch").button("option", "label", "Append");
			}
		}, null, true, options);
	}

	function updateControlState() {
		return;
		var catalog = _catalogList[_controlDiv.find("#escCatalog option:selected").val()];
		if (catalog === undefined) return;

		// Depth
		_controlDiv.find("#escDepthSlider").slider( ((!catalog.hasDepth) ? 'disable' : 'enable') );
		_controlDiv.find("#escDepthMin").prop('disabled', !catalog.hasDepth);
		_controlDiv.find("#escDepthMax").prop('disabled', !catalog.hasDepth);

		// Magnitude
		_controlDiv.find("#escMagnitudeSlider").slider( ((!catalog.hasMagnitude) ? 'disable' : 'enable') );
		_controlDiv.find("#escMagnitudeValue").prop('disabled', !catalog.hasMagnitude);

		// Date
		_controlDiv.find("#escStart").prop('disabled', !catalog.hasDate);
		_controlDiv.find("#escEnd").prop('disabled', !catalog.hasDate);

		// Coordinates (Rectangle)
		_controlDiv.find("input[id*=escLatitude]").prop('disabled', !catalog.hasRectangle);
		_controlDiv.find("input[id*=escLongitude]").prop('disabled', !catalog.hasRectangle);
		_controlDiv.find("#escCoordinateReset").prop('disabled', !catalog.hasRectangle);
	}

	function parseUserCatalog() {
		// After the user has ended the catalog data,
		// check it, and send on to the /event/parse service.
		// Return { status: [0 on success], header: string }
		var result = { status: 1, message: "FAIL", header: "" };

		var time      = Number($("#escColumnTime").val());
		var latitude  = Number($("#escColumnLatitude").val());
		var longitude = Number($("#escColumnLongitude").val());
		var depth     = Number($("#escColumnDepth").val());
		var nmax      = Math.max(time, latitude, longitude, depth);
		var nmin      = Math.min(time, latitude, longitude, depth);

		//msg = "time = " + time + " lat = " + latitude + " lon = " + longitude + " depth = " + depth + " (min:" + nmin + " max:" + nmax + ")";
		//console.log("parseUserCatalog: " + msg);

		if ((nmin < 1) || isNaN(nmax)) {
			alert("Error: column indices must be integers starting from 1.");
			return result;
		}

		// Build the format, columns and input parameters prior to
		// sending to the event service.
		var format = "csv";
		var columns = Array();
		// FIXME: UNVALIDATED USER INPUT??
		var input = $("#escCatalogInput").val();

		if (input === null || input === undefined || input === "") {
			alert("Please paste your catalog inside the text area before pressing 'Send'.");
			return result;
		}

		// Build the columns variable.
		// Each element is 'ignore' except for the four required ones.
		var col_indices = Array(time, latitude,   longitude,   depth);
		var col_tags = Array("time", "latitude", "longitude", "depth");
		for (var i=0; i < nmax; i++) columns[i] = "ignore";
		for (var i = 0 ; i < col_indices.length; i++) {
			if (col_indices[i] === undefined) {
				console.warn('Item ' + i + ':' + col_tags[i] + ' is undefined');
			}
		}
		for (var i = 0 ; i < col_tags.length; i++) {
			var index = col_indices[i]-1;
			if (columns[index] === "ignore") {
				columns[index] = col_tags[i];
			} else {
				var msg = "Error: " + columns[index] + " and " + col_tags[i] +
					  " can't both be given in column " + (index+1) + ".";
				alert(msg);
				var msg2 = "parseUserCatalog: indices were " + col_indices + "; " + columns.length + " columns: '" + columns + "')";
				console.log(msg2);
				columns = columns.toString();
				result = { status: 1, message: "Index problem", header: columns };
				return result; // {status: 1; header: columns};
			}
		}

		columns = columns.toString();  // A comma-separated string

		// This will add the result returned from the server 
		// directly into a new package in the
		// request control

		// FIXME: It should be changed that the information is only 
		// added when the user press "Search".
		wiService.event.parse(function(data, statustext, jqxhr) {
			if (jqxhr.status == 204) {
				alert("No events could be imported from the User catalog");
				wiConsole.notice("No events could be imported from the User catalog");
			}
			else {
				requestControl.appendEvent(data);
				_controlDiv.find("#escSearch").button("option", "label", "Append");
			}
		}, null, true, format, columns, input);

		var br = "\n"; // "<br>";
		var msg = "OK, params are:" + br;
		msg += " format: '" + format + "'" + br;
		msg += " columns: '" + columns + "'" + br;
		msg += " input: '" + input + "'" + br;
		result = {status: 0, message: msg, header: columns };
		return result; // { status: 0, header: columns };
	}

	function buildControl() {
		if (_controlDiv === null) return;

		// Create the HTML
		var html='';

		html += '<h3>Event Information</h3>';
		html += '<div id="escEventMode" align="center">';
		html += '<input type="radio" value="Catalog" id="escEventModeCatalog" name="escEventMode" /><label for="escEventModeCatalog">Catalog Services</label>';
		html += '<input type="radio" value="File" id="escEventModeFile" name="escEventMode" /><label for="escEventModeFile">User Supplied</label>';
		html += '</div>';

		html += '<div id="escEventDiv">';
		html += '<div style="padding: 8px;" id="escEventCatalogDiv"></div>';
		html += '<div style="padding: 8px; text-align: center;" id="escEventFileDiv"></div>';
		html += '</div>';

		html += '<div class="wi-control-item-last">';
		html += '<input id="escReset" class="wi-inline" type="button" value="Reset" />';
		html += '<input id="escSearch" class="wi-inline" type="button" value="Search" />';
		html += '</div>';
		_controlDiv.append(html);

		requestControl.bind("onDeleteEvents", function() {
			_controlDiv.find("#escSearch").button("option", "label", "Search");
		})

		/*
		 * Normal Pre-Defined Catalog Search Controls
		 */
		html =  '<div class="wi-control-item-first wi-short-div">';
		html += '<div class="wi-short-spacer">Catalog Service:</div>';
		html += '<div class="wi-short-right"><select style="width: 100%;" id="escCatalog"></select></div>';
		html += '</div>';

		/*
		 * Here we set the z-index to:
		 *  (1) keep it above the sliders
		 *  (2) keep it above the map -- layer 0
		 *  (3) Keep it below the pop-up dialog.
		 */

		html += '<div class="wi-control-item">';
		html += '<div class="wi-spacer">Date Interval (yyyy-mm-dd):</div>';
		html += '<input style="position: relative; z-index: 100" class="wi-inline" type="text" id="escStart"  title="Start date in yyyy-mm-dd format."/>';
		html += '&ndash;<input style="position: relative; z-index: 100" class="wi-inline" type="text" id="escEnd" title="End date in yyyy-mm-dd format."/>';
		html += '</div>';

		html += '<div class="wi-control-item">';
		html += '<div class="wi-spacer">Minimum Magnitude:<input class="wi-inline-small" id="escMagnitudeValue" value="-" title="Minimum allowed magnitude (-2.0 to 10.0)" /></div>';
		html += '<div id="escMagnitudeSlider"></div>';
		html += '</div>'

		html += '<div class="wi-control-item">';
		html += '<div class="wi-spacer">Depth from<input class="wi-inline-small" id="escDepthMin" value="">to<input class="wi-inline-small" id="escDepthMax" value="">km</div>';
		html += '<div id="escDepthSlider"></div>';
		html += '</div>';

		html += '<div class="wi-control-item">';
		html += '<div class="wi-spacer">Coordinates: (Use -ve for S/W; +ve for N/E)</div>';
		html += '<div style="text-align: center;">';
		html += 'N<br/>';
		html += '<input style="text-align: center; width: 50px; margin: .5em;" id="escLatitudeMax" value="" title="Northernmost latitude for the region of interest (-90&#176; to 90&#176;)"><br/>';
		html += 'W<input style="text-align: center; width: 50px; margin: .5em 1.5em .5em .5em;" id="escLongitudeMin" value="" title="Westernmost longitude for the region of interest (-180 to 180&deg;)">';
		html += '<input style="text-align: center; width: 50px; margin: .5em .5em .5em 1.5em;" id="escLongitudeMax" value="" title="Easternmost longitude for the region of interest (-180 to 180 degrees)"/>E<br/>';
		html += '<input style="text-align: center; width: 50px; margin: .5em;" id="escLatitudeMin" value="" title="Southernmost latitude for the region of interest (-90&#176; to 90&#176;)">';
		html += '<br/>S';
		html += '<input style="position: absolute; bottom: 2.0em; right: 0;" type="button" id="escCoordinateReset" value="Clear" />';
		html += '</div>';
		html += '</div>';
		_controlDiv.find("#escEventCatalogDiv").append(html)

		html = '<div class="wi-spacer"><input id="escUserCatalog" class="wi-inline-full" type="button" value="Upload Catalog" /></div>';
		_controlDiv.find("#escEventFileDiv").append(html)

		/*
		 * Event Mechanism Mode
		 */
		_controlDiv.find("#escEventMode").buttonset();
		_controlDiv.find("#escEventMode").change(function(item) {
			_controlDiv.find("#escEventDiv").children("div").hide();
			_controlDiv.find("#escEvent" + ($(item.target).val()) + 'Div').show();
		});

		/*
		 * Text area for customized catalog upload
		 */
		html = '<div id="escCatalogLoader">';
		html += '<p style="margin: 5px 0 5px 0; font-size: 0.85em;">Use this control to upload your personal event catalog to be processed by our system. The catalog should be in CSV (comma-separated value) format and may contain as many events as you want, one per line, with the same number of columns. You must also indicate which columns contain the Latitude, Longitude, Depth and Origin Time for the event. All other columns will be ignored.</p>';
		html += '<p><i>Example:</i> <tt>2011-03-11T05:46:23;38.23;142.53;15;Tohoku</tt></p>';
		html += '<br/><h3>Column Number Specification:</h3>';
		html += '<div>';
		html += 'Time: <input class="wi-inline-small" id="escColumnTime" value="1" />';
		html += 'Latitude: <input class="wi-inline-small" id="escColumnLatitude" value="2"/>';
		html += 'Longitude: <input class="wi-inline-small" id="escColumnLongitude" value="3"/>';
		html += 'Depth: <input class="wi-inline-small" id="escColumnDepth" value="4"/>';
		html += '</div>';

		html += '<br/><h3>Copy and paste your catalog into the area below:</h3>';
		html += '<div id="escCatalogHeader">[No format specified. Press "Send" first.]</div><br>';
		html += '<div style="margin: 5px 0 10px 0;"><textarea style="width: 100%; height: 4em;" id="escCatalogInput">2011-03-11T05:46:23;38.23;142.53;15;Tohoku</textarea></div>';
		html += '</div>';
		$("body").append(html);


		$("body").find("#escCatalogLoader").dialog({
			title: "Catalog Input Dialog",
			autoOpen: false,
			height: 450,
			width: 550,
			modal: true,
			buttons: {
				Send: function() {
				    alert("Thank you, your upload is being checked.");
				    var result = parseUserCatalog();
				    console.log("parseUserCatalog: " + result.message);
				    if (result.header !== undefined) {
					var text = "Format: " + result.header;
					$("body").find("#escCatalogHeader").empty().append(text);
				    }
				},
				Close: function() {
					$( this ).dialog( "close" );
				}
			}
		});

		// Catalog
		_controlDiv.find("#escUserCatalog").button().bind('click', function() {
			$("#escCatalogLoader").dialog('open');
		});

		_controlDiv.find("#escSearch").button().bind("click", query);

		_controlDiv.find("#escQuick6").button().bind("click", quick6);

		_controlDiv.find("#escReset").button().bind("click", resetControl);

		_controlDiv.find("#escCatalog").bind("click", updateControlState);

		_controlDiv.find("#escStart").datepicker({
			showButtonPanel: true,
			changeMonth: true,
			changeYear: true,
			dateFormat: "yy-mm-dd"
		});

		_controlDiv.find("#escEnd").datepicker({
			showButtonPanel: true,
			changeMonth: true,
			changeYear: true,
			dateFormat: "yy-mm-dd"
		});

		// Depth Slider
		_controlDiv.find("#escDepthSlider" ).slider({
			range: true,
			min: 0.0,
			max: 1000.0,
			step: 1.0,
			slide: function(event, ui) {
				_controlDiv.find('#escDepthMin').val(ui.values[0]);
				_controlDiv.find('#escDepthMax').val(ui.values[1]);
			},
			change: function(event, ui) {
				_controlDiv.find('#escDepthMin').val(ui.values[0]);
				_controlDiv.find('#escDepthMax').val(ui.values[1]);
			}
		});

		_controlDiv.find("#escDepthMin").bind("change", function(obj) {
			var values = _controlDiv.find('#escDepthSlider').slider('values');
			values[0] = $(obj.target).val();
			 _controlDiv.find('#escDepthSlider').slider('values', values);
		});

		_controlDiv.find("#escDepthMax").bind("change", function(obj) {
			var values = _controlDiv.find('#escDepthSlider').slider('values');
			values[1] = $(obj.target).val();
			 _controlDiv.find('#escDepthSlider').slider('values', values);
		});

		// Magnitude Slider
		_controlDiv.find("#escMagnitudeSlider").slider({
			min: -2.0,
			max: 10.0,
			step: 0.1,
			slide: function(event, ui) {
				_controlDiv.find('#escMagnitudeValue').val(ui.value);
			},
			change: function(event, ui) {
				_controlDiv.find('#escMagnitudeValue').val(ui.value);
			}
		});

		_controlDiv.find("#escMagnitudeValue").bind("change", function (obj) {
			 _controlDiv.find('#escMagnitudeSlider').slider('value', $(obj.target).val());
		});

		// Coordinate Box
		_controlDiv.find("input[id*=escLatitude]").bind("change", function(item) {
			var value = checkNumber($(item.target).val(),-90,90);
			if (value === null) {
				alert("Invalid latitude value, " + $(item.target).val());
				$(item.target).val('');
				return;
			}
			validateCoordinates();
		});

		_controlDiv.find("input[id*=escLongitude]").bind("change", function(item) {
			var value = checkNumber($(item.target).val(),-180,180);
			if (value === null) {
				alert("Invalid longitude value, " + $(item.target).val());
				$(item.target).val('');
				return;
			}
			validateCoordinates();
		});

		_controlDiv.find("#escCoordinateReset").button().bind("click", resetCoordinates);
	}

	function load(htmlTagId) {
		var control = $(htmlTagId);

		// If we don't find one div ...
		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("event.js: Cannot find a div with class '" + htmlTagId + "'");
			return;
		}

		// otherwise finish load ...
		_controlDiv = control;

		// Build it
		buildControl();

		// Connect to the mapping
		if (typeof mapControl !== "undefined") {
			mapControl.bind("onChangeExtend", function(bottom, left, top, right) {
				_controlDiv.find("#escLatitudeMax").val(top);
				_controlDiv.find("#escLatitudeMin").val(bottom);
				_controlDiv.find("#escLongitudeMax").val(right);
				_controlDiv.find("#escLongitudeMin").val(left);
			});
		}

		// Reset the control
		resetControl();

		// Trigger the first load of the catalog
		reloadCatalogs();
	}

	//
	// Public
	//

	//
	// Load the class into the HTML page
	//
	load(htmlTagId);
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.eventSearchControl = new EventSearchControl("#wi-EventSearchControl");
			resolve();
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("events.js: " + e.message);

			wiConsole.error("events.js: " + e.message, e);
			reject();
		}
	});
}
