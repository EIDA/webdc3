$(document).ready(function() {
        $(window).bind("resize", resizeMap);
        resizeMap();
        initMap();
    });

var map, select, kmlLayer, boxLayer, global;

function resizeMap() {
    $("#map").css("width", $("#right.resmodule").innerWidth());
    $("#map").css("height", Math.floor($(window).height()*0.4));
}

function initMap() {
    map = new OpenLayers.Map('map', 
                             {controls: [new OpenLayers.Control.Navigation(),
                                         new OpenLayers.Control.PanZoom(),
                                         new OpenLayers.Control.MousePosition(),
                                         new OpenLayers.Control.KeyboardDefaults({observeElement: 'map'})
                                        ],
                              restrictedExtent: new OpenLayers.Bounds(-210, -90, 210, 90)});

// BIANCHI 12-03-2012 Looks like that the metacarta has been down
    var baseLayer = new OpenLayers.Layer.WMS(
      "WMS base layer",
      "http://vmap0.tiles.osgeo.org/wms/vmap0",
      {layers: "basic"},
      {'maxExtent': new OpenLayers.Bounds(-210, -90, 210, 90), 'maxResolution': 'auto'}
    );

    boxLayer = new OpenLayers.Layer.Vector("Box Layer");
    boxLayer.setOpacity(0.3);
    var options = {projection: map.displayProjection};
    kmlLayer = new OpenLayers.Layer.Vector("KML Layer", options);
    var control = new OpenLayers.Control({
        draw: function () {
                this.hbox = new OpenLayers.Handler.Box(control, {'done': this.notice}, {'keyMask': OpenLayers.Handler.MOD_SHIFT});
                this.hbox.activate();
            },
        notice: function (bounds) {
                boxLayer.destroyFeatures();
                var lb = map.getLonLatFromPixel(new OpenLayers.Pixel(bounds.left, bounds.bottom)); 
                var rt = map.getLonLatFromPixel(new OpenLayers.Pixel(bounds.right, bounds.top));
                var bounds = new OpenLayers.Bounds(lb.lon, lb.lat, rt.lon, rt.lat);
                var box = new OpenLayers.Feature.Vector(bounds.toGeometry());
                boxLayer.addFeatures([box]);                
                $("input[name=latmin]").val(Math.round(lb.lat*100)/100);
                $("input[name=latmax]").val(Math.round(rt.lat*100)/100);
                $("input[name=lonmin]").val(Math.round(lb.lon*100)/100);
                $("input[name=lonmax]").val(Math.round(rt.lon*100)/100);
		if ($("input[name=zoom]").attr("checked")) map.zoomToExtent(bounds, true);
            }
        });
    select = new OpenLayers.Control.SelectFeature(kmlLayer);
    kmlLayer.events.on({"featureselected": onFeatureSelect,
                       "featureunselected": onFeatureUnselect});
    map.addLayers([baseLayer, boxLayer, kmlLayer]);
    map.zoomToMaxExtent();
    map.addControl(control);
    map.addControl(select);
    select.activate();
    $("body").css("cursor", "");
}

function onPopupClose() {
    select.unselectAll();
}

function onFeatureSelect(event) {
    var feature = event.feature;
    global = feature;
    var button = "<br><br><input type='button' id='removeButton' value='remove from map' name='remove' onclick=onRemoveFeature()></div>";
    var popup = new OpenLayers.Popup.FramedCloud("description", 
                                                 feature.geometry.getBounds().getCenterLonLat(),
                                                 new OpenLayers.Size(10,10),
                                                 "<div id='content'><b>" + feature.attributes.name + "</b><br>" + feature.attributes.description + button,
                                                 null, true, onPopupClose);
    feature.popup = popup;
    map.addPopup(popup);
}

function onFeatureUnselect(event) {
    var feature = event.feature;
    if (feature.popup) {
        map.removePopup(feature.popup);
        feature.popup.destroy();
        delete feature.popup;
    }
}

function onRemoveFeature() {
    map.removePopup(global.popup);
    global.popup.destroy();
    delete global.popup;
    global.style.display = "none";
    kmlLayer.redraw();
    $("input[name=onMap][value=" + global.attributes.name + "]").attr("checked", "");
}

function eventsMap(count, start) {
    if (global && global.popup) {
        map.removePopup(global.popup);
        global.popup.destroy();
        delete global.popup;
    }
    if (count && start != -1) kmlLayer.removeFeatures(kmlLayer.features.slice(start,start+count));
    $("#eqinfo table tr").each(function(index) {
            if (index > 0) {
                if ($(this).css("display") != "none") {
                    var chdren = $(this).children();
                    var date = chdren.slice(0,1).text();
                    var mag = chdren.slice(1,2).text();
                    var lat = chdren.slice(2,3).html().split(" ");
                    lat[1] == "S" ? lat = parseFloat(lat[0]) * -1 : lat = parseFloat(lat[0]);
                    var lon = chdren.slice(3,4).html().split(" ");
                    lon[1] == "W" ? lon = parseFloat(lon[0]) * -1 : lon = parseFloat(lon[0]);
                    var depth = chdren.slice(4,5).html();
                    var region = chdren.slice(5,6).html();
                    var evstyle = OpenLayers.Util.extend({}, OpenLayers.Feature.Vector.style['default']);
                    evstyle.strokeColor = "#000000";
                    evstyle.strokeWidth = 1;
                    evstyle.fillColor = "#000000"; 
                    evstyle.fillOpacity = 0.1;
                    if ($(this).hasClass("bigevt")) { 
                        evstyle.strokeWidth = 4; evstyle.fillOpacity = 0.4;
                    }
                    if ($(this).hasClass("xxlevt")) {
                        evstyle.strokeColor = "#ff0000"; evstyle.strokeWidth = 4;
                        evstyle.fillColor = "#ff0000"; evstyle.fillOpacity = 0.4;
                    }
                    kmlLayer.addFeatures([new OpenLayers.Feature.Vector(new OpenLayers.Geometry.Point(lon, lat), {name: date,
                                        description: "region: " + region + "<br>mag: " + mag + " depth: " + depth}, evstyle)]);
                }
            }
        });
    $("body").css("cursor", "");
}

function stationsMap(count, start) {
    if (global && global.popup) {
        map.removePopup(global.popup);
        global.popup.destroy();
        delete global.popup;
    }
    if (count && start != -1) kmlLayer.removeFeatures(kmlLayer.features.slice(start,start+count));
    $.get("data/" + $("input[name=sesskey]").val() + ".kml", function(data) { 
            var kml = new OpenLayers.Format.KML({extractStyles: true, extractAttributes: true});
            var parsed = kml.read(data);
            kmlLayer.addFeatures(parsed);
        });    
 }

function destroyMapFeatures(count, start) {
    if (count && start != -1) kmlLayer.removeFeatures(kmlLayer.features.slice(start,start+count));
}

function displayAllFeatures(displ, count, start) {
    var features = kmlLayer.features.slice(start, start+count);
    var len = features.length;
    do {
        var feature = features[--len];
	displ ? feature.style.display = "" : feature.style.display = "none";
    } while (len);
    kmlLayer.redraw();
}

function displayFeature(displ, val, count, start) {
    var features = kmlLayer.features.slice(start, start+count);
    var len = features.length;
    do {
        var feature = features[--len];
        if (feature.attributes.name == val) {
            displ ? feature.style.display = "" : feature.style.display = "none";
            kmlLayer.redraw();
            break;
        }
    } while (len);
}

function resetMapRegion() {
    boxLayer.destroyFeatures();
    map.zoomToMaxExtent();
}

function zoomMap(bool) {
    if (!bool) map.zoomToMaxExtent();
    else {
	var bounds = boxLayer.getDataExtent();
	if (!bounds) {
	    bounds = new OpenLayers.Bounds(parseFloat($("#station_form input[name=lonmin]").val()), parseFloat($("#station_form input[name=latmin]").val()),
					   parseFloat($("#station_form input[name=lonmax]").val()), parseFloat($("#station_form input[name=latmax]").val()));
	    var box = new OpenLayers.Feature.Vector(bounds.toGeometry());
	    boxLayer.addFeatures([box]);                
	}
	map.zoomToExtent(bounds, true);
    }
}
