/*
 * GEOFON WebInterface
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, GFZ Potsdam
 *
 * mapping.js module: This is the mapping utilities.
 * 
 */

/*
 * Map Object implementation
 */
function MapControl(htmlTagId) {
	var that = this;

	// Private
	var _callbacks = { };
	var _controlDiv = null;
	var _map = null;

	/*
	 * This is the default projection used for all GPS style lon/lat applications
	 * The map will not always be in this coordinate and we must take care of convert to/from this projection
	 * before showing coordinates to the user or before setting bounds based on the user input
	 */
	var _wgs84 = 'EPSG:4326';

	// Those are OpenLayers.Layer.Vector
	var _items = undefined;

	// Those are stores for the styles used, later 
	// should be used for making the legend
	var _event_styles = { };
	var _station_styles = { };

	// feature used to mark the select box
	var _edges = undefined;

	function resetZoom(bounds) {
		if (!_map) return;
		if (typeof bounds === "undefined")
			_map.zoomToMaxExtent();
		else
			_map.zoomToExtent(bounds, true);
	}

	function makeWMSlayer(serverURL, layerName) {
		if (! serverURL) return;
		if (! layerName) return;
		var layer = new OpenLayers.Layer.WMS(
			layerName + "from " + serverURL,
			serverURL,
			{ layers: layerName },
			{ maxExtent: new OpenLayers.Bounds(-230, -95, 230, 95),
			  maxResolution: 'auto'}
		);
		return layer;
	}

	function makeGoogleLayer(layerName) {
		if (! layerName) return;

		var options = undefined;

		if (layerName === "Google Satellite" ) {
			options = { type: google.maps.MapTypeId.SATELLITE, numZoomLevels: 22 };
		} else if (layerName === "Google Physical") {
			options = { type: google.maps.MapTypeId.TERRAIN, numZoomLevels: 20};
		} else if (layerName === "Google Hybrid") {
			options = { type: google.maps.MapTypeId.HYBRID, numZoomLevels: 22};
		} else {
			layerName = "Google Street";
			options = { numZoomLevels: 20, visibility: false};
		}

		var layer = new OpenLayers.Layer.Google(layerName, options);
		return layer;
	}

	function makeOSMLayer(layerName) {
		if (! layerName) return;
		return new OpenLayers.Layer.OSM(layerName);
	}

	// Rounding is used to make the coordinates shown in the
	// selection box pleasant, but also to obscure the true
	// locations of the the stations for casual observers.
	function roundLatLon(x) {
		return Math.round(x * 100) / 100;
	}


	function makeMousePosition(digits) {
		var control = new OpenLayers.Control.MousePosition({
			displayProjection: _wgs84,
			numDigits: digits
		});
		return control;
	}

	function makeVectorLayer() {
		var options = { projection: _map.displayProjection };
		var layer = new OpenLayers.Layer.Vector("Events", options);
		return layer;
	}

	function getCallbacks(name) {
		if (typeof _callbacks[name] === "undefined" ) return [];
		return _callbacks[name];
	}

	function makeSelector() {
		var control = new OpenLayers.Control({
			draw: function () {
				this.hbox = new OpenLayers.Handler.Box(control, {'done': this.notice}, {'keyMask': OpenLayers.Handler.MOD_SHIFT});
				this.hbox.activate();
			},
			notice: function (bounds) {
				//boxLayer.destroyFeatures();
				var lb = _map.getLonLatFromPixel(new OpenLayers.Pixel(bounds.left, bounds.bottom));
				var rt = _map.getLonLatFromPixel(new OpenLayers.Pixel(bounds.right, bounds.top));


				/*
				 * Transform from MAP -> WGS84
				 */
				lb.transform(_map.getProjection(), _wgs84);
				rt.transform(_map.getProjection(), _wgs84);

				// Rounding to 2 digits
				lb.lon = roundLatLon(lb.lon);
				lb.lat = roundLatLon(lb.lat);
				rt.lon = roundLatLon(rt.lon);
				rt.lat = roundLatLon(rt.lat);

				// Save the selection box
				that.setSelect(lb.lat, lb.lon, rt.lat, rt.lon);
			}
		});
		return control;
	}

	function makeLimitBox() {
		var layer = new OpenLayers.Layer.Vector("Selection Limit");
		layer.setOpacity(0.3);
		return layer;
	}

	function disableMouseWheel() {
		var controls = _map.getControlsByClass('OpenLayers.Control.Navigation');
		for(var i = 0; i < controls.length; ++i) {
			controls[i].disableZoomWheel();
		}
	}

	function legendItem(flag, text) {
		var html = '';
		console.error(eidaCSSSource);
		html += '<td><img src="' + eidaCSSSource + "/" + flag+ '.png" title="' + text + '" width="15" height="15"></td><td>' + text + '</td>';
		return html;
	}

	function legend() {
		var html = '';

		html += '<h3>Stations</h3>';
		html += "<table cellspacing='5'>";
		html += "<tr>";
		html += legendItem('op', "Open and permanent");
		html += legendItem('rp', "Restricted and permanent");
		html += "</tr>";
		html += "<tr>";
		html += legendItem('ot', "Open and temporary");
		html += legendItem('rt', "Restricted and temporary");
		html += "</tr>";
		html += "<tr>" + legendItem('uu', "Uncategorized Station") + "<td colspan='2'>&nbsp;</td></tr>";
		html += "</table>";

		html += '<h3>Events</h3>';
		html += "<table cellspacing='5'>";
		html += "<tr>";

		html += legendItem('evdefault', "Magnitude &lt; 6.0");
		html += legendItem('evbig', "Magnitude &ge; 6.0");
		html += "</tr>";
		html += "</table>";

		return html;
	}

	function makeMap() {
		if (_controlDiv === null) return;

		// Empty the div just in case
		_controlDiv.empty();

		// Create the map place
		var html = '';

		html += '<div id="MapControlMap"></div>';
		html += '<div style="float: left;">Use left SHIFT + drag mouse to select regions.</div>';
		html += '<div style="float: right;"><a href="javascript:mapControl.showHelp();">Help</a></div>';
		html += '<div style="float: right;"><a href="javascript:mapControl.showLegend();">';
		html += 'Legend</a>&nbsp;</div>';
		html += '<br class="clear"/>';

		// Append HTML code
		_controlDiv.append(html);

		// Prepare the map area
		_controlDiv.find("#MapControlMap").css('padding', '0');
		_controlDiv.find("#MapControlMap").css('height', '300px');

		/*
		 * Here we force the map to go down to layer 0
		 */
		_controlDiv.find("#MapControlMap").css('z-index', 0);
		_controlDiv.find("#MapControlMap").css('position', 'relative');
		_controlDiv.find("#MapControlMap").width(_controlDiv.width());

		_controlDiv.find("#MapControlLegend").css('border', '0px Solid black');
		_controlDiv.find("#MapControlLegend").css('margin-top', '5px');
		_controlDiv.find("#MapControlLegend").css('min-height', '50px');
		_controlDiv.find("#MapControlLegend").css('padding', '5px 0 5px 0');

		/*
		 * Setup layers and controls
		 */

		var controls = [];
		var layers   = [];

		/*
		 * Base map
		*/
		var maptype = configurationProxy.value("maptype", null);
		_map = new OpenLayers.Map("MapControlMap", { controls: [ ] } );

		/*
		 * Base map layer
		 */
		if (maptype === "wms") {
			layers.push(makeWMSlayer(configurationProxy.value('wms.server', null) ,configurationProxy.value('wms.layer', null)));
		} else if (maptype === "google") {
			if (typeof google === 'undefined') {
				throw new WIError("mapping.js: No Google maps available.");
				return; /* without pushing anything */
			} else {
				layers.push(makeGoogleLayer(configurationProxy.value('google.layer', null)));
			}
		} else if (maptype === "osm") {
			layers.push(makeOSMLayer("OSMLayer"));
		} else {
			throw new WIError("mapping.js: Whoa! Improper maptype value in the configuration");
		}

		/*
		 * Add a zoom control and reset button (the order that the 
		 * controls are loaded matter - those should come before than
		 * the selector control otherwise the SHIFT+mouse stop working)
		 */
		controls.push(new OpenLayers.Control.PanPanel());
		controls.push(new OpenLayers.Control.ZoomPanel());
		controls.push(new OpenLayers.Control.Navigation());

		/*
		 * consider:
		 */
		// controls.push(new OpenLayers.Control.LayerSwitcher());

		/*
		 * Map position control (numbers on the bottom of the map)
		 */
		controls.push(makeMousePosition(2));

		/*
		 * Add a box controls
		 */
		controls.push(makeSelector());

		/*
		 * Items layer (events and stations)
		 */
		_items = makeVectorLayer();
		layers.push(_items);

		/*
		 * Create the SelectFeature Control and add it to the controls to be added
		 * Also connect the callbacks to the "_items" vector layer to respond on the
		 * controls signals
		 */
		var _itsel = new OpenLayers.Control.SelectFeature(_items);
		controls.push(_itsel);

		_items.events.on( { "featureselected": onItemSelect, "featureunselected": onItemUnselect } );

		/*
		 * Limiting box (marks the select region on the map)
		 */
		_edges = makeLimitBox();
		layers.push(_edges);

		/*
		 * Add controls
		 */
		_map.addControls(controls);

		/*
		 * Add layers
		 */
		_map.addLayers(layers);

		/*
		 * Disable mouse wheel over the map
		 */
		disableMouseWheel();

		/*
		 * Reset zoom
		 */
		resetZoom();

		/*
		 * Make coordinates more visible, at TR corner.
		 * FIXME Wrong way to set style - should be in a style sheet
		 */
		var loc = _controlDiv.find(".olControlMousePosition");
		loc.css('color', '#00589C'); /* GFZ dark blue */
		loc.css('background-color', '#aaaaaa80');
		loc.css('height', '1.4em');
		loc.css('min-width', '7em');
		loc.css('padding', '2px');
		/* loc.css('border', '1px Solid white'); */
		loc.css('font-size', 'larger');
		loc.css('font-weight', 'bold');
		loc.css('text-align', 'center');
		loc.css('top', '10px');

		/*
		 * Activate the selectors
		 */
		_itsel.activate();
	}

	function probemap(){
		if (_controlDiv.width() === 0) {
			setTimeout(probemap,500);
			return;
		}
		makeMap();
	}

	function load(htmlTagId) {
		var control = $(htmlTagId);

		if (control.length !== 1) {
			if (interfaceLoader.debug()) console.error("mapping.js: Cannot find a div with class '" + htmlTagId + "'");
			return;
		}

		// Save the main control div
		_controlDiv = control;

		// Because the map div has no width when the page is first
		// loaded we have to keep on trying until it is set to its
		// correct size. This is done on the probemap method.
		setTimeout(probemap, 500);

		return;
	}

	/*
	 * Those are related to the creation of the styles 
	 * and features per event/station
	 */
	function findStationStyle(id, net, sta, lon, lat, archive, restricted, type, selected) {
		var stname = "";

		// Restricted
		if (restricted === 1 && type === "p")
			stname += "rp";
		else if (restricted === 1 && type === "t")
			stname += "rt";
		else if ((restricted === 2 && type === "p") || (restricted === 3 && type === "p"))

			stname += "op";
		else if ((restricted === 2 && type === "t") || (restricted === 3 && type === "t"))
			stname += "ot";
		else
			stname += "uu";

		if (!selected)
			stname += "_uns"

		if (typeof _station_styles[stname] === "undefined" ) {
			var style = OpenLayers.Util.extend({}, OpenLayers.Feature.Vector.style['default']);
			style.externalGraphic = eidaCSSSource + "/" + stname + '.png';
			style.graphicOpacity = 0.8;
			_station_styles[stname] = style;
		}

		return _station_styles[stname];
	}

	function findEventStyle(id, lon, lat, depth, mag, region, date, selected) {
		var stname = undefined;

		if (mag > 6.0) {
			stname = "evbig";
		} else {
			stname = "evdefault";
		}

		if (!selected)
			stname += "_uns"

		if ( typeof _event_styles[stname] === "undefined" ) {
			var style = OpenLayers.Util.extend({}, OpenLayers.Feature.Vector.style['default']);

			// If styling doesn't work, we can always resort
			// to 'externalGraphic'.
			// Ref: <http://dev.openlayers.org/releases/OpenLayers-2.13.1/doc/apidocs/files/OpenLayers/Feature/Vector-js.html>
			switch (stname) {
				case "evbig":
					style.strokeWidth = 4;
					style.strokeDashstyle = "solid";
					style.fillOpacity = 0.5;
					style.fillColor = "#ffa000";
					break;

				case "evbig_uns":
					style.strokeWidth = 2;
					style.strokeDashstyle = "dashed";
					style.strokeColor = "#c08000";
					style.fillOpacity = 0.2;
					style.fillColor = "#000000";
					break;

				case "evdefault":
					style.strokeWidth = 1;
					style.strokeColor = "#ee9900";
					style.strokeDashstyle = "solid";
					style.fillOpacity = 0.4;
					style.fillColor = "#ffa000";
					break;

				case "evdefault_uns":
					style.strokeWidth = 1;
					style.strokeDashstyle = "dashed";
					style.strokeColor = "#c08000";
					style.fillOpacity = 0.2;
					style.fillColor = "#000000";
					break;
			}
			_event_styles[stname] = style;
		}

		return _event_styles[stname];
	}

	function createEventFeature(id, lon, lat, depth, mag, region, date, selected) {
		var pt = new OpenLayers.Geometry.Point(Number(lon), Number(lat));
		// (lon,lat) must be converted to the coordinate system map units.
		pt.transform(_wgs84, _map.getProjection());

		var ats = {
			name: date,
			description: "Region: " + region + "<br>Magnitude: " + mag + " Depth: " + depth,
			evst: "ev",
			selected: selected,
			key: id
		};
		var style = findEventStyle(id, lon, lat, depth, mag, region, date, selected);
		return new OpenLayers.Feature.Vector(pt, ats, style);
	}

	function createStationFeature(id, net, sta, lon, lat, archive, restricted, type, streams, selected) {
		var pt = new OpenLayers.Geometry.Point(Number(lon), Number(lat));
		// (lon,lat) must be converted to the coordinate system map units.
		pt.transform(_wgs84, _map.getProjection());

		var streamtypes = {}
		for (var n in streams) {
			var m = streams[n].match('(.[HLNG]).$')
			if (m)
				streamtypes[m[1]] = true;
		}

		var ats = {
			name: "Network: " + net + " / Station: " + sta,
			description: "Longitude: " + roundLatLon(Number(lon)) + " Latitude: " + roundLatLon(Number(lat)) + "<br/>Streams: " + $.map(streamtypes, function(v, k) { return k + '*' }).join(', ')  + "<br/>Archived at: " + archive ,
			evst: "st",
			selected: selected,
			key: id
		};
		var style = findStationStyle(id, net, sta, lon, lat, archive, restricted, type, selected);

		return new OpenLayers.Feature.Vector(pt, ats, style);
	}

	/*
	 * Those are the callbacks for the pop-ups
	 * ItemSelect/ItemUnselect calls onEventSelect/onStationSelect
	 */
	function onEventSelect(feature) {
		var button = "<div style='text-align: center; padding: 10px 5px 5px 5px;'><input type='button' id='" + feature.attributes.key + "' value='" + (feature.attributes.selected? "Unselect": "Select") + "' onclick='mapControl.toggleItem(this)'></div>";
		var popup = new OpenLayers.Popup.AnchoredBubble("description", 
				feature.geometry.getBounds().getCenterLonLat(),
				new OpenLayers.Size(250,100),
				"<div><b>" + feature.attributes.name + "</b><br>" + feature.attributes.description + button + "</div>",
				null, true, null);
		feature.popup = popup;
		_map.addPopup(feature.popup);
	}

	function onStationSelect(feature) {
		var button = "<div style='text-align: center; padding: 10px 5px 5px 5px;'><input type='button' id='" + feature.attributes.key + "' value='" + (feature.attributes.selected? "Unselect": "Select") + "' onclick=mapControl.toggleItem(this)></div>";
		var popup = new OpenLayers.Popup.AnchoredBubble("description", 
				feature.geometry.getBounds().getCenterLonLat(),
				new OpenLayers.Size(250,100),
				"<div><b>" + feature.attributes.name +"</b><br/>" + feature.attributes.description + button + "</div>",
				null, true, null);
		feature.popup = popup;
		_map.addPopup(popup);
	}

	function onItemUnselect(item) {
		closePopup(item.feature);
	}

	function onItemSelect(item) {
		if (item.feature.attributes.evst === "ev") return onEventSelect(item.feature);
		if (item.feature.attributes.evst === "st") return onStationSelect(item.feature);

		throw new WIError("mapping.js: Invalid feature");
	}

	function closePopup(feature) {
		_map.removePopup(feature.popup);
		feature.popup.destroy();
		delete feature.popup;
	}

	/*
	 * This is used by the removeStation/removeEvent 
	 * method when called from package
	 */
	function removeItem(evst, id) {
		if (!_items) return;

		if (typeof id === "undefined") {
			var items = _items.getFeaturesByAttribute('evst', evst);
			_items.destroyFeatures(items);
			return;
		}

		var item = _items.getFeaturesByAttribute('key', id);
		_items.destroyFeatures(item);
	}

	function findFeature(id) {
		var features = _items.getFeaturesByAttribute('key', id);
		if (features.length !== 1) throw new WIError("mapping.js: found more than one feature with id " + id);
		return features[0];
	}

	// Public
	this.showHelp = function() {
		var html = '';

		html += '<div>';
		html += '<h1>Map Control Usage</h1>';
		html += '<br/>';
		html += '<p>The mapping control is used to <b>display</b> and <b>further selected stations and events</b>. When you add a set of events or stations to compose your request the selected items will be marked on the map. Use the "Legend for Icons" link to see the meaning of the different symbols displayed.</p>';
		html += '<ul>';
		html += '<li>To <b>deselect</b> a station or event, click on it and click on the "Remove" button. This will disable the chosen item on the list, and it will be removed from the map. To add it again, simply select it again on the list in the "Event and Station List" control by checking the corresponding check box item.</li>';
		html += '<li>You can also use the <b>Shift+Left mouse</b> button to <b>set an area</b> for further restricting the searching of events and stations. (Note that for this region to affect the station search you should make sure to have the Explore Station by Region activated.)</li>';
		html += '<li>To zoom in once you have selected a region, double-click. To restore the whole-globe view, use the globe control on the top left. You can also use the "+" and "-" controls there to zoom in and out.</li>';
		html += '</ul>';
		html += '<p>The area selected will be automatically inserted into the coordinates area in the Events Control and Station Control. To clear your area selection, use the "Reset Region" button on any of those controls.</p>';
		html += '</div>';
		$(html).dialog({
			modal: true,
			closeOnEscape: true,
			width: 550,
			height: 500,
			buttons: [ {
					text: "Close help",
					click: function() { 
						$( this ).dialog( "close" );
						$( this ).dialog( "destroy" );
					} 
				} ]
		});
	};

	this.showLegend = function() {
		var html = '';

		html += '<div style="z-index:9999; position: relative;">';
		html += '<h1>Legend for Map icons</h1>';
		html += legend();
		html += '</div>';
		$(html).dialog({
			modal: false,
			closeOnEscape: true,
			width: 440,
			height: 330,
			buttons: [ {
					text: "Close legend",
					click: function() { 
						$( this ).dialog( "close" );
						$( this ).dialog( "destroy" );
					} 
				} ]
		});
	};

	/*
	 * This is a public method called by the remove popup button
	 */
	this.toggleItem = function(obj) {
		var id = $(obj).attr("id");
		var feature = findFeature(id);

		// First we remove the pop up otherwise the feature
		// object is destroyed ....
		closePopup(feature);

		// ... and we toggle the event on the request -> package
		// that will trigger the purge of the feature
		if (feature.attributes.evst === "ev")
			requestControl.toggleEvent(feature.attributes.key);
		else if (feature.attributes.evst === "st")
			requestControl.toggleStation(feature.attributes.key);
		else
			throw new WIError("mapping.js: Invalid evst type" + feature.attributes.evst);
	};

	this.addEvent = function(id, lon, lat, depth, mag, region, date, selected) {
		if (!_items) return;
		try {
			findFeature(id);
			// Event already on the map, just return !
			return;
		} catch (e) {
			var f = createEventFeature(id, lon, lat, depth, mag, region, date, selected);
			_items.addFeatures( [ f ] );
		}
	};

	this.removeEvent = function(id){
		removeItem("ev", id);
	};

	this.addStation = function(id, net, sta, lon, lat, archive, restricted, type, streams, selected) { 
		if (!_items) return;
		try {
			findFeature(id);
			// Station already on the map, just return !
			return;
		} catch (e) {
			var f = createStationFeature(id, net, sta, lon, lat, archive, restricted, type, streams, selected);
			_items.addFeatures( [ f ] );
		}
	};

	this.removeStation = function(id){
		removeItem("st", id);
	};

	/*
	 * Those two methods are used by the events.js/station.js to set the 
	 * red box marking the coordinates region active
	 */
	this.setSelect = function(bottom, left, top, right) {
		if (! this.enabled()) return;

		if (bottom <= -90 && top >=90 && left <= -180 && right >= 180) 
			return this.clearSelect();

		_edges.destroyFeatures();
		var bounds = new OpenLayers.Bounds(left, bottom, right, top);

		// transform projection
		bounds.transform(_wgs84, _map.getProjection());

		var box = new OpenLayers.Feature.Vector(bounds.toGeometry());
		_edges.addFeatures([box]);

		resetZoom(bounds);

		/*
		 * Process the callbacks
		 */
		var cb = getCallbacks("onChangeExtend");
		for(var key in cb)
			cb[key](bottom, left, top, right);
	};

	this.clearSelect = function() {
		_edges.destroyFeatures();

		resetZoom();

		/*
		 * Process the callbacks
		 */
		var cb = getCallbacks("onChangeExtend");
		for(var key in cb)
			cb[key](-90, -180, 90, 180);
	};

	this.enabled = function() {
		if (!_controlDiv) return false;
		if (!_items) return false;

		return true;
	};

	this.bind = function(name, method) {
		// The functions registered here will be called when the user 
		// finish to select an region with the SHIFT + Mouse
		if (name === "onChangeExtend") {
			if (typeof _callbacks[name] === "undefined") _callbacks[name] = [];
			_callbacks[name].push(method);
			return;
		}

		throw new WIError("Invalid callback name " + name);
	};

	// Main Implementation
	load(htmlTagId);
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			window.mapControl = new MapControl("#wi-MappingControl");
			resolve();
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("mapping.js: " + e.message);

			wiConsole.error("mapping.js: " + e.message, e);
			reject();
		}
	});
}
