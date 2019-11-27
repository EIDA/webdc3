/*
 * GEOFON WebInterface
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Andres Heinloo, Javier Quinteros, GFZ Potsdam
 *
 * submit.js module: This is the submit module for the web-interface. It is used
 *                   to offer the user the appropriate controls to submit the 
 *                   request.
 */

/*
 * Implementation of the submitControl
 */
function SubmitControl(htmlTagId) {
	// Private
	var _controlDiv = null;

	function checkNumber(value, min, max) {
		if (value === "") return null;

		value = Number(value);

		if (isNaN(value)) return null;

		if (min && value < min) return null;
		if (max && value > max) return null;

		return value;
	}

	function seconds2time(seconds) {
		var value = new Date("2010-01-01T00:00:00Z");
		value.setSeconds( seconds );
		return value.toISOString().substr(11,8);
	}

	function time2seconds(time) {
		var h = 0;
		var m = 0;
		var s = 0;

		var hms = time.split(":");
		if (typeof hms[0] !== "undefined") h = Number(hms[0]);
		if (typeof hms[1] !== "undefined") m = Number(hms[1]);
		if (typeof hms[2] !== "undefined") s = Number(hms[2]);

		if (isNaN(h)) return null;
		if (isNaN(m)) return null;
		if (isNaN(s)) return null;

		return (h*60 + m)*60 + s;
	}

	function buildControl() {
		if (!_controlDiv) return;

		var html = '';

		/*
		 * Time window mode
		 */
		html += '<h3>Time Window selection:</h3>';
		html += '<div class="wi-control-item">';
		html += '<div id="sbtTimeMode" align="center">';
		html += '<input type="radio" value="Relative" id="sbtTimeModeRelative" name="sbtTimeMode" /><label for="sbtTimeModeRelative">Relative Mode</label>';
		html += '<input type="radio" value="Absolute" id="sbtTimeModeAbsolute" name="sbtTimeMode" /><label for="sbtTimeModeAbsolute">Absolute Mode</label>';
		html += '</div>';

		html += '<div id="sbtTimeDiv">';
		html += "<div style='padding: 10px;' id='sbtTimeAbsoluteDiv'></div>";
		html += '<div style="padding: 10px;" id="sbtTimeRelativeDiv"></div>';
		html += '</div>';
		html += '</div>';

		html += '<br/>';

		html += '<h3>Request Type:</h3>';

		if (typeof wiFDSNWS_Control.submitRequest !== 'undefined') {
			html += '<div id="scType">';
			html += "<div class='wi-control-item-first'>";
			html += '<div style="padding-left: 20px;">';
			html += '<input id="scType-FDSNWS-dataselect" name="scType" type="radio" value="FDSNWS-dataselect" />&nbsp;<label for="scType-FDSNWS-dataselect">Waveform (Mini-SEED)</label><br/>';
			html += '<input id="scType-FDSNWS-station-xml" name="scType" type="radio" value="FDSNWS-station-xml" />&nbsp;<label for="scType-FDSNWS-station-xml">Metadata (StationXML)</label><br/>';
			html += '<input id="scType-FDSNWS-station-text" name="scType" type="radio" value="FDSNWS-station-text" />&nbsp;<label for="scType-FDSNWS-station-text">Metadata (Text)</label><br/>';
			html += '</div>';
			html += '</div>';
			html += '</div>';

			html += '<div id="scLevel">';
			html += '<div id="scLevelRespBlock" style="display:none">';
			html += '<div class="wi-control-item">';
			html += '<div class="wi-spacer"><a title="This will determine the amount of info returned.">Metadata level?</a></div>';
			html += '<div style="padding-left: 20px;">';
			html += '<input type="radio" value="station" id="scLevelResp-station" name="scLevel" />&nbsp;<label for="scLevelResp-station">Station</label>';
			html += '<input type="radio" value="channel" id="scLevelResp-channel" name="scLevel" />&nbsp;<label for="scLevelResp-channel">Channel</label>';
			html += '<input type="radio" value="response" id="scLevelResp-response" name="scLevel" />&nbsp;<label for="scLevelResp-response">Response</label>';
			html += '</div>';
			html += '</div>';
			html += '</div>';

			html += '<div id="scLevelNoRespBlock" style="display:none">';
			html += '<div class="wi-control-item">';
			html += '<div class="wi-spacer"><a title="This will determine the amount of info returned.">Metadata level?</a></div>';
			html += '<div style="padding-left: 20px;">';
			html += '<input type="radio" value="station" id="scLevelNoResp-station" name="scLevel" />&nbsp;<label for="scLevelNoResp-station">Station</label>';
			html += '<input type="radio" value="channel" id="scLevelNoResp-channel" name="scLevel" />&nbsp;<label for="scLevelNoResp-channel">Channel</label>';
			html += '</div>';
			html += '</div>';
			html += '</div>';
			html += '</div>';
		} else {
			html += "<div class='wi-control-item-first'>";
			html += '<div class="wi-spacer">Offline storage of the web browser must be enabled to use FDSNWS.</div>';
			html += '</div>';
		}

		/* Final row of buttons */
		html += '<div class="wi-control-item">';
		html += '<input id="scReset" class="wi-inline" type="button" value="Reset"/>';
		html += '</div>';

	 	html += '<br/>';

		html += '<div class="wi-control-item-last">';
		html += '<input id="scReview" class="wi-inline" type="button" value="Review"/>';
		html += '<input id="scSubmit" class="wi-inline" type="button" value="Submit"/>';
		html += '</div>';

		_controlDiv.empty();
		_controlDiv.append(html);

		/*
		 * Relative time window definition
		 */
		html = '<div class="wi-spacer">Use time windows relative to events, by phase and onset time.</div>';

		html += '<div class="wi-control-item">';

		html += '<div style="float: left;">';
		html += '<div class="wi-spacer" align="left">Start <span style="font-size: 0.8em;">(minutes before)</span></div>';
		html += '</div>';

		html += '<div style="clear: left; float: left;">';
		html += '<select id="sbtPrePhase" class="wi-inline"></select>-';
		html += '</div>';

		html += '<div style="float: left;">';
		html += '<div class="wi-spacer"><input class="wi-inline" id="sbtPreValue" /></div>';
		html += '<div class="wi-spacer"><div class="wi-inline" id="sbtPreSlider"></div></div>';
		html += '</div>';

		html += '<div style="clear: left; float: left;">';
		html += '<div class="wi-spacer" align="left">End <span style="font-size: 0.8em;">(minutes after)</span></div>';
		html += '</div>';

		html += '<div style="clear: left; float: left;">';
		html += '<select id="sbtPostPhase" class="wi-inline"></select>+';
		html += '</div>';

		html += '<div style="float: left;">';
		html += '<div class="wi-spacer"><input class="wi-inline" id="sbtPostValue" /></div>';
		html += '<div class="wi-spacer"><div class="wi-inline" id="sbtPostSlider"></div></div>';
		html += '</div>';


		html += '<br class="wi-clear"/>';

		html += "</div>";
		_controlDiv.find("#sbtTimeRelativeDiv").append(html);

		/*
		 * Absolute time window definition
		 */
		html = '<div class="wi-spacer">Use an absolute time window.</div>';

		html += '<div class="wi-control">';
		html += '<div style="float: left;">';
		html += '<div class="wi-spacer" align="center">Start</div>';
		html += '<div class="wi-spacer"><input style="position: relative; z-index: 2" class="wi-inline" id="sbtStartDate" /></div>';
		html += '</div>';

		html += '<div style="float: right;">';
		html += '<div class="wi-spacer" align="center">End</div>';
		html += '<div class="wi-spacer"><input style="position: relative; z-index: 2" class="wi-inline" id="sbtEndDate" /></div>';
		html += '</div>';

		html += '<div style="clear: left; float: left;">';
		html += '<div class="wi-spacer"><input class="wi-inline" id="sbtStart" maxlength="8" /></div>';
		html += '<div class="wi-spacer"><div class="wi-inline" id="sbtStartSlider"></div></div>';
		html += '</div>';

		html += '<div style="clear: right; float: right;">';
		html += '<div class="wi-spacer"><input class="wi-inline" id="sbtEnd" maxlength="8"/></div>';
		html += '<div class="wi-spacer"><div class="wi-inline" id="sbtEndSlider"></div></div>';
		html += '</div>';

		html += '<br class="wi-clear"/>';

		html += "</div>";
		_controlDiv.find("#sbtTimeAbsoluteDiv").append(html);

		// Basic button set for mode
		_controlDiv.find("#sbtTimeMode").buttonset();
		_controlDiv.find("#sbtTimeMode").change(function(item) {
			_controlDiv.find("#sbtTimeDiv").children("div").hide();
			_controlDiv.find("#sbtTime" + ($(item.target).val()) + 'Div').show();
		});

		// Pre Phase
		_controlDiv.find("#sbtPreSlider").slider({
			min: -60,
			max: 0,
			value: -2,
			slide: function(event, ui) {
				_controlDiv.find('#sbtPreValue').val(Math.abs(ui.value));
			},
			change: function(event, ui) {
				_controlDiv.find('#sbtPreValue').val(Math.abs(ui.value));
			}
		});
		_controlDiv.find('#sbtPreValue').val( Math.abs(_controlDiv.find("#sbtPreSlider").slider("value")) );
		_controlDiv.find("#sbtPreValue").bind("change", function(obj) {
			var value = Number($(obj.target).val());
			if (isNaN(value)) {
				alert("Invalid value, " + $(obj.target).val());
				$(obj.target).val(Math.abs($("#sbtPreSlider").slider("value")));
				return;
			}
			_controlDiv.find("#sbtPreSlider").slider('value', -1 * Math.abs(value));
		});

		// Post Phase
		_controlDiv.find("#sbtPostSlider").slider({
			min: 0,
			max: 3 * 60,
			value: 10,
			slide: function(event, ui) {
				_controlDiv.find('#sbtPostValue').val(ui.value);
			},
			change: function(event, ui) {
				_controlDiv.find('#sbtPostValue').val(ui.value);
			}
		});
		_controlDiv.find('#sbtPostValue').val( _controlDiv.find("#sbtPostSlider").slider("value") );
		_controlDiv.find("#sbtPostValue").bind("change", function(obj) {
			var value = Number($(obj.target).val());
			if (isNaN(value)) {
				alert("Invalid value, " + $(obj.target).val());
				$(obj.target).val($("#sbtPostSlider").slider("value"));
				return;
			}
			_controlDiv.find("#sbtPostSlider").slider('value', Math.abs(value) );
		});

		// Start
		_controlDiv.find("#sbtStartDate").datepicker({
			showButtonPanel: true,
			changeMonth: true,
			changeYear: true,
			dateFormat: "yy-mm-dd"
		});
		_controlDiv.find("#sbtStartSlider").slider({
			min: 0,
			max: 24*60*60 - 1,
			step: 1,
			value: 0,
			slide: function(event, ui) {
				_controlDiv.find('#sbtStart').val(seconds2time(ui.value));
			},
			change: function(event, ui) {
				_controlDiv.find('#sbtStart').val(seconds2time(ui.value));
			}
		});
		_controlDiv.find('#sbtStart').val( seconds2time(_controlDiv.find("#sbtStartSlider").slider("value")) );
		_controlDiv.find("#sbtStart").bind("change", function(obj) {
			var value = time2seconds($(obj.target).val())
			if (value !== null)
				_controlDiv.find('#sbtStartSlider').slider('value', value);
			$(obj.target).val(seconds2time(_controlDiv.find('#sbtStartSlider').slider('value')));
		});

		// End
		_controlDiv.find("#sbtEndDate").datepicker({
			showButtonPanel: true,
			changeMonth: true,
			changeYear: true,
			dateFormat: "yy-mm-dd"
		});
		_controlDiv.find("#sbtEndSlider").slider({
			min: 0,
			max: 24*60*60 - 1,
			step: 1,
			value: 24*60*60 - 1,
			slide: function(event, ui) {
				_controlDiv.find('#sbtEnd').val(seconds2time(ui.value));
			},
			change: function(event, ui) {
				_controlDiv.find('#sbtEnd').val(seconds2time(ui.value));
			}
		});
		_controlDiv.find('#sbtEnd').val( seconds2time(_controlDiv.find("#sbtEndSlider").slider("value")) );
		_controlDiv.find("#sbtEnd").bind("change", function(obj) {
			var value = time2seconds($(obj.target).val())
			if (value !== null)
				_controlDiv.find('#sbtEndSlider').slider('value', value);
			$(obj.target).val(seconds2time(_controlDiv.find('#sbtEndSlider').slider('value')));
		});

		_controlDiv.find("#scReset").button().bind("click", resetControl);
		_controlDiv.find("#scReview").button().bind("click", function() { submit(true) });
		_controlDiv.find("#scSubmit").button().bind("click", function() { submit(false) });

		requestControl.bind("onDeleteEvents", reselect);
		requestControl.bind("onAddEvents", reselect);
	}

	function reselect() {
		var mode = null;
		try {
			mode = requestControl.hasEvent() ? "sbtTimeModeRelative" : "sbtTimeModeAbsolute"
		} catch(e) {
			mode = "sbtTimeModeAbsolute";
		}
		_controlDiv.find("#" + mode).click();
	}

	function fillSelect(select, data) {
		var html = '';
		select.empty();
		for(var key in data) {
			html += '<option value='+ data[key][0] + '>' + data[key][1] + '</option>';
		}
		select.append(html);
	}

	function resetControl() {
		if (!_controlDiv) return;

		var mode = null;
		try {
			mode = requestControl.hasEvent() ? "sbtTimeModeRelative" : "sbtTimeModeAbsolute"
		} catch(e) {
			mode = "sbtTimeModeAbsolute";
		}
		_controlDiv.find("#" + mode).click();
		_controlDiv.find("#sbtStartDate").datepicker("setDate", "now");
		_controlDiv.find("#sbtEndDate").datepicker("setDate", "now");

		_controlDiv.find("#sbtPreSlider").slider("value", -2);
		_controlDiv.find("#sbtPostSlider").slider("value", 10);

		_controlDiv.find("#sbtStartSlider").slider("value", 0);
		_controlDiv.find("#sbtEndSlider").slider("value", 24 * 60 * 60 - 1);

		if (typeof wiFDSNWS_Control.submitRequest !== 'undefined') {
			_controlDiv.find("input[name=scType]").bind("change", function(item) {
				var key = $(item.target).val();
				if ( (key === "FDSNWS-station-xml") ) {
					_controlDiv.find("#scLevelResp-station").prop('checked', true);
					_controlDiv.find("#scLevelRespBlock").show();
				} else {
					_controlDiv.find("#scLevelRespBlock").hide();
				}
				if ( (key === "FDSNWS-station-text") ) {
					_controlDiv.find("#scLevelNoResp-station").prop('checked', true);
					_controlDiv.find("#scLevelNoRespBlock").show();
				} else {
					_controlDiv.find("#scLevelNoRespBlock").hide();
				}
			});

			_controlDiv.find("#scType-FDSNWS-dataselect").prop('checked', true);
			_controlDiv.find("#scLevelRespBlock").hide();
			_controlDiv.find("#scLevelNoRespBlock").hide();
		}

		/*
		 * Reload the Phase List
		 */
		wiService.metadata.phases(function(data) {
			fillSelect(_controlDiv.find('#sbtPrePhase'),data);
			fillSelect(_controlDiv.find('#sbtPostPhase'),data);
		}, null, true, {});
	}

	function submit(review) {
		var submitinfo = { };

		submitinfo.review = review;
		submitinfo.request = {};
		submitinfo.timewindow = {};

		// Clean the warn class
		_controlDiv.find(".wi-warn").removeClass("wi-warn");

		// This is the data package to be send over

		submitinfo.mode = _controlDiv.find("#sbtTimeMode input:checked").val();;

		submitinfo.request.requesttype = _controlDiv.find("#scType input:checked").val();
		submitinfo.request.level = _controlDiv.find("#scLevel input:checked").val();

		if (!submitinfo.request.requesttype) {
			wiConsole.error("submit.js: request type is undefined");
			return;
		}

		// Load in values
		if (submitinfo.mode === "Absolute") {
			var sdate = _controlDiv.find('#sbtStartDate').datepicker('getDate');
			var edate = _controlDiv.find('#sbtEndDate').datepicker('getDate');
			var start = _controlDiv.find('#sbtStartSlider').slider('value');
			var end   = _controlDiv.find('#sbtEndSlider').slider('value');
			submitinfo.timewindow.start = $.datepicker.formatDate('yy-mm-dd',sdate) + "T" + seconds2time(start) + "Z";
			submitinfo.timewindow.end   = $.datepicker.formatDate('yy-mm-dd',edate) + "T" + seconds2time(end) + "Z";
		} else {
			submitinfo.timewindow.startphase  = _controlDiv.find('#sbtPrePhase').val();
			submitinfo.timewindow.endphase    = _controlDiv.find('#sbtPostPhase').val();
			submitinfo.timewindow.startoffset = _controlDiv.find('#sbtPreSlider').slider('value');
			submitinfo.timewindow.endoffset   = _controlDiv.find('#sbtPostSlider').slider('value');
		}

		// Associate
		requestControl.submit(submitinfo);
	}

	function load(htmlTagId) {
		var control = $(htmlTagId);

		// If we don't find one div ...
		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("submit.js: Cannot find a div with class '" + htmlTagId + "'");
			return;
		}

		// otherwise finish load ...
		_controlDiv = control;

		// build the interface
		buildControl();

		// Reset
		resetControl();
	}

	// Public

	// Load the class into the HTML page
	load(htmlTagId);
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.submitControl = new SubmitControl("#wi-SubmitControl");
			resolve();
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("submit.js: " + e.message);

			wiConsole.error("submit.js: " + e.message, e);
			reject();
		}
	});
}

