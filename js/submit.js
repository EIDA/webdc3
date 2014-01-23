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
 * Page wide variable to provides the submit to all modules.
 */
var submitControl = undefined;

/*
 * Implementation of the submitControl
 */
function SubmitControl(htmlTagId) {
	// Private
	var _controlDiv = null;

	function reloadControl() {
		/*
		 * Reload the Request Types
		 */
		wiService.request.types(function(data) {
			fillRequesttype(_controlDiv.find('#scType'), data);
			_controlDiv.find("input[name=scType][id=scType-MSEED]").prop('checked', true);
		}, null, true, {});

		/*
		 * Reload the Phase List
		 */
		wiService.metadata.phases(function(data) {
			fillSelect(_controlDiv.find('#sbtPrePhase'),data);
			fillSelect(_controlDiv.find('#sbtPostPhase'),data);
		}, null, true, {});
	}

	function checkNumber(value, min, max) {
		if (value === "") return null;

		value = Number(value);
		
		if (isNaN(value)) return null;
	
		if (min && value < min) return null;
		if (max && value > max) return null;
		
		return value;
	};

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

		html += '<h3>Request Information:</h3>';
		html += "<div class='wi-control-item-first'>";
		html += '<div class="wi-spacer">Request type:</div>';
		html += '<div style="padding-left: 20px;" id="scType"></div>';
		html += '</div>';

		html += "<div class='wi-control-item'>";
		html += '<div class="wi-spacer"><a title="This will apply bzip2 compression.">Use compression?</a></div>';
		html += '<div style="padding-left: 20px;" id="scCompress">';
		html += '<input type="radio" value="yes" id="scCompress-yes" name="scCompress" />&nbsp;<label for="scCompress-yes">Yes</label>';
		html += '<input type="radio" value="no" id="scCompress-no" name="scCompress" />&nbsp;<label for="scCompress-no">No</label>';
		html += '</div>';
		html += '</div>';

		html += '<div id="scResponseBlock">';
		html += "<div class='wi-control-item'>";
		html += '<div class="wi-spacer"><a title="This will include SEED blockettes 4X in the generated volume.">Use response dictionary?</a></div>';
		html += '<div style="padding-left: 20px;" id="scResponse">';
		html += '<input type="radio" value="yes" id="scResponse-yes" name="scResponse" />&nbsp;<label for="scResponse-yes">Yes</label>';
		html += '<input type="radio" value="no" id="scResponse-no" name="scResponse" />&nbsp;<label for="scResponse-no">No</label></p>';
		html += '</div>';
		html += '</div>';
		html += '</div>';

		html += "<div class='wi-control-item'>";
		html += '<div class="wi-spacer">Your e-mail address:</div>';
		html += '<input type="text" class="wi-inline-full" id="scUser" /><br/>';
		html += '<input type="checkbox" id="scUserKeep"> Remember me?';
		html += '</div>';

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

		// username 
		_controlDiv.find("#scUser").bind("change", function(item) {
			if ( ! _controlDiv.find("#scUserKeep").is(":checked") ) return;

			var value = $(item.target).val();

			if(value) {
				$.cookie('scUser', value, { expires: 30 });
			} else {
				$.removeCookie('scUser');
			}
		});

		_controlDiv.find("#scUserKeep").bind("change", function(item) {
			$.removeCookie('scUser');
			if ($(item.target).is(":checked")) {
				_controlDiv.find("#scUser").change();
			}
		});

		_controlDiv.find("#scReset").button().bind("click", resetControl);
		_controlDiv.find("#scReview").button().bind("click", function() { submit(true) });
		_controlDiv.find("#scSubmit").button().bind("click", function() { submit(false) });

		// trigger cookie refresh
		_controlDiv.find("#scUser").change();
	};

	function fillRequesttype(div,data) {
		var html = '';
		div.empty();
		for(var i in data) {
			var id = data[i][0];
			var idl   = 'scType-' + id;
			var label = data[i][1];
			html += '<input id="' + idl + '" name="scType" type="radio" value="' + id + '" />&nbsp;<label for="' + idl + '">' + label + '</label><br/>';
		}
		div.append(html);

		// Request type 
		div.find("input[name=scType]").bind("change", function(item) {
			var key = $(item.target).val();
			if ( (key === "DSEED") || (key === "FSEED") ) {
				_controlDiv.find("#scResponseBlock").show();
			} else {
				_controlDiv.find("#scResponseBlock").hide();
			};
			if ( key === "INVENTORY" || (key === "DSEED") ) {
				_controlDiv.find("#scCompress-yes").prop('checked', true);
			} else {
				_controlDiv.find("#scCompress-no").prop('checked', true);
			}
		});

		// Set the default
		div.find("input[name=scType][id=scType-MSEED]").prop('checked', true);
	}

	function fillSelect(select, data) {
		var html = '';
		select.empty();
		for(var key in data) {
			html += '<option value='+ data[key][0] + '>' + data[key][1] + '</option>';
		};
		select.append(html);
	};

	function resetControl() {
		if (!_controlDiv) return;

		/*
		 * Compress flag
		 */
		_controlDiv.find("input[name=scCompress][id=scCompress-no]").prop('checked', true);

		/*
		 * Response dictionary
		 */
		_controlDiv.find("input[name=scResponse][id=scResponse-no]").prop('checked', true);

		/*
		 * User field
		 */
		if ($.cookie("scUser")) {
			_controlDiv.find("#scUser").val( $.cookie("scUser") );
			_controlDiv.find("#scUserKeep").prop('checked', $.cookie("scUser").length);
		} else {
			_controlDiv.find("#scUser").val('');
			_controlDiv.find("#scUserKeep").prop('checked', false);
		}

		/*
		 * Find the state for the response block
		 */
		var key = $("input[name=scType]:checked").val();
		if ( (key === "DATALESS") || (key === "FSEED") ) {
			$("#scResponseBlock").show();
		} else {
			$("#scResponseBlock").hide();
		};

		_controlDiv.find("#sbtTimeModeRelative").click();
		_controlDiv.find("#sbtStartDate").datepicker("setDate", "now");
		_controlDiv.find("#sbtEndDate").datepicker("setDate", "now");

		_controlDiv.find("#sbtPreSlider").slider("value", -2);
		_controlDiv.find("#sbtPostSlider").slider("value", 10);

		_controlDiv.find("#sbtStartSlider").slider("value", 0);
		_controlDiv.find("#sbtEndSlider").slider("value", 24 * 60 * 60 - 1);
		
		/*
		 * This would reload the phase list & Request type
		 */
		reloadControl();
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

		submitinfo.request.user = _controlDiv.find("#scUser").val();
		if ( ! submitinfo.request.user ) {
			alert("You need to supply your e-mail address to be able to send your request.");
			_controlDiv.find("#scUser").addClass("wi-warn");
			return;
		};

		submitinfo.request.requesttype = _controlDiv.find("#scType input:checked").val();
		submitinfo.request.compressed = ( _controlDiv.find("#scCompress input:checked").val() === "yes" ) ? true : false ;

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


		if (submitinfo.request.type === "DSEED" || submitinfo.request.type === "FSEED") {
			submitinfo.request.responsedictionary = ( _controlDiv.find("#scResponse input:checked").val() === "yes" ) ? true : false ;
		}

		// Associate
		requestControl.submit(submitinfo);
	};

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
	};

	// Public

	// Load the class into the HTML page
	load(htmlTagId);
}

$(document).ready(function() {
	try {
		submitControl = new SubmitControl("#wi-SubmitControl");
	}
	catch (e) {
		if (console.error !== wiConsole.error)
			console.error("submit.js: " + e.message);

		wiConsole.error("submit.js: " + e.message, e);
	}
});
