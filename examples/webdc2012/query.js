/* 
 * js/query.js
 * JavaScript for the EIDA web interface.
 *
 * Initial version by Doreen Pahlke (pahlke), GFZ Potsdam, 2009 or earlier
 *
 */

$(document).ready(function() {
    console.log("This is js/query.js - JavaScript for the EIDA web interface");
        $("input[name^=lat][type=text]").bind("change", function() { 
                if (isNaN($(this).val()) || parseFloat($(this).val()) < -90 || parseFloat($(this).val()) > 90) {
                    alert("Please insert a value between -90 and 90 degrees!");
                    $("input[name=latmin]").val("-90");
                    $("input[name=latmax]").val("90");
                }});
        $("input[name^=lon][type=text]").bind("change", function() {
                if (isNaN($(this).val()) || parseFloat($(this).val()) < -180 || parseFloat($(this).val()) > 180) {
                    alert("Please insert a value between -180 and 180 degrees!");
                    $("input[name=lonmin]").val("-180");
                    $("input[name=lonmax]").val("180");
                }});
        $("#station_form select[name$=sel]").bind("change", function() {
                var selidx = $("#station_form select[name$=sel]").index(this);
                $("body").addClass("wait");
                window.setTimeout("loadStationForm(" + selidx + ", true);", 500);
            });
        $("#event_form input[name=Bevents]").bind("click", function() {
                setRegion("event_form");
		if (!restore) {
		    $("body").addClass("wait");
		    window.setTimeout("getEvents();", 500);
		} else getEvents();
            });
        $("#station_form input[name=Bstations]").bind("click", function() {
                setRegion("station_form");
		if (!restore) {
		    $("body").addClass("wait");
		    window.setTimeout("getStations();", 500);
		} else getStations();
            });
        $("#event_form input[name=Breset]").bind("click", function() {
                resetMapRegion();
                resetRegion("event_form");
            });
        $("#station_form input[name=Breset]").bind("click", function() {
                resetMapRegion();
                resetRegion("station_form");
            });
	$("input[name=zoom]").bind("click", function() {zoomMap($(this).attr("checked"));});
        $("input[name$=minmax]").bind("click", function() {displayModule($(this).attr("name"), $(this).val());});
        $("input[name$=clear]").bind("click", function() {clearModule($(this).attr("name").slice(0,-5))});
	$("input[name$=all]").bind("click", function() {selectAll($(this).attr("name").slice(0,-3), $(this).attr("checked"));});
	$("input[name$=freeze]").bind("click", function() {
		var name = $(this).attr("name");
		var check = $(this).attr("checked");
		$("body").addClass("wait");
		window.setTimeout(function() {freeze(name, check, true);}, 500);
	    });	
        $("input[name=Bsubmit]").bind("click", function() {saveState(); completeRequest();});
	$("input[name=Bresetall]").bind("click", function() {window.location.href="query?" + $("input[name=sesskey]").serialize();});
        if (!window.location.hash) {
            $("body").addClass("wait");
            window.setTimeout("loadStationForm(1, true);", 500);
        } else {
            $("body").addClass("wait");
	    restore = true;
            window.setTimeout("restoreState();", 500);
        }
    });

var evcount = 0, stacount = 0;
var evstart = -1, stastart = -1;
var eRegion = new Array("-90", "90", "-180", "180");
var sRegion = new Array("-90", "90", "-180", "180");
var restore = false;

function saveState() {
    var hash = "";
    hash += saveDate() + saveEvents() + saveStations();
    var pattern = /(&evfreeze=\[[0-9,]+\])/;
    var result = "";
    if (result = pattern.exec(window.location.hash)) hash += result[1];
    if (window.location.hash.indexOf("&stfreeze=1") != -1) hash += "&stfreeze=1";    
    window.location.hash = hash;
}

function saveEvents() {
    if ($("#eqinfo table").length) {
        var args = new Array();
        args.push("mag=" + $("#event_form input[name=mag]").val());
        args.push("depth=" + $("#event_form input[name=depth]").val());
	args.push("dbsel=" + $("#event_form select[name=dbsel]").val());
        args.push("elatmin=" + eRegion[0]);
        args.push("elatmax=" + eRegion[1]);
        args.push("elonmin=" + eRegion[2]);
        args.push("elonmax=" + eRegion[3]);
	args.push("before=" + $("#tw_form input[name=before]").val());
	args.push("after=" + $("#tw_form input[name=after]").val());
        return "&" + args.join("&");
    }
    return "";
}

function saveStations() {
    if ($("#stalist table").length) {
        var args = new Array();
        args.push("typesel=" + $("#station_form select[name=typesel]").val());
        args.push("netsel=" + $("#station_form select[name=netsel]").val());
        args.push("statsel=" + $("#station_form select[name=statsel]").val());
        args.push("sensor=" + $("#station_form select[name=sensor]").val());	
        args.push($("#station_form input[name=stream]").serialize());
	if (!$("#station_form input[name=loc]").val().length) args.push("loc=+");
        else args.push($("#station_form input[name=loc]").serialize());
        args.push("slatmin=" + sRegion[0]);
        args.push("slatmax=" + sRegion[1]);
        args.push("slonmin=" + sRegion[2]);
        args.push("slonmax=" + sRegion[3]);
	if ($("#eqinfo input[name=onMap]:checked").length) {
	    args.push("azmin=" + $("#station_form .disaz_form input[name=azmin]").val());
	    args.push("azmax=" + $("#station_form .disaz_form input[name=azmax]").val());
	    args.push("dismin=" + $("#station_form .disaz_form input[name=dismin]").val());
	    args.push("dismax=" + $("#station_form .disaz_form input[name=dismax]").val());
	}
        return "&" + args.join("&");
    }
    return "";
}

function restoreState() {
    var hash = window.location.hash.substr(1);
    restoreDate();
    restoreEvents();
    restoreStations();
    restore = false;
}

function restoreEvents() {
    var hash = window.location.hash.substr(1);
    var pattern = /mag=([0-9.]+)/;
    var result = "";
    var click = false;
    if (result = pattern.exec(hash)) {
        $("#event_form input[name=mag]").val(result[1]); click = true;
    } else $("#event_form input[name=mag]").val("1");
    pattern = /depth=([0-9.]+)/;
    if (result = pattern.exec(hash)) {
        $("#event_form input[name=depth]").val(result[1]); click = true;
    } else $("#event_form input[name=depth]").val("1000");
    pattern = /dbsel=(\w+)/;
    if (result = pattern.exec(hash)) {
	$("#event_form select[name=dbsel][value=" + result[1] + "]").attr("selected", "selected"); click = true;
    } else $("#event_form select[name=dbsel][value=GFZ]").attr("selected", "selected");
    pattern = /elatmin=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
        $("#event_form input[name=latmin]").val(result[1]); click = true;
    } else  $("#event_form input[name=latmin]").val("-90");
    pattern = /elatmax=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
        $("#event_form input[name=latmax]").val(result[1]); click = true;
    } else $("#event_form input[name=latmax]").val("90");
    pattern = /elonmin=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
        $("#event_form input[name=lonmin]").val(result[1]); click = true;
    } else $("#event_form input[name=lonmin]").val("-180");
    pattern = /elonmax=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
        $("#event_form input[name=lonmax]").val(result[1]); click = true; 
    } else $("#event_form input[name=lonmax]").val("180");
    pattern = /before=([0-9]+)/;
    (result = pattern.exec(hash)) ? $("tw_form input[name=before]").val(result[1]) : $("tw_form input[name=before]").val("2");
     pattern = /after=([0-9]+)/;
    (result = pattern.exec(hash)) ? $("tw_form input[name=after]").val(result[1]) : $("tw_form input[name=after]").val("10");
    if (click) $("input[name=Bevents]").trigger("click");    
}

function restoreFreezedEvents() {
    var hash = window.location.hash.substr(1);
    var pattern = /evfreeze=\[([0-9,]+)\]/;
    var result = "";
    if (result = pattern.exec(hash)) {
	var arr = result[1].split(",");
	$.each(arr, function(index, value) {
		$("#eqinfo table tr:eq(" + value + ")").css("display", "none").find(":checkbox").attr("checked", "").trigger("change");		
	    });
	$(".eqinfo input[name=eqinfofreeze]").attr("checked", "checked");
    }
}

function restoreStations() {
    var hash = window.location.hash.substr(1);
    var pattern = /typesel=(\w+)/;
    var result = "";
    var click = false;
    if (result = pattern.exec(hash)) {
	$("#station_form select[name=typesel] option[value=" + result[1] + "]").attr("selected", "selected"); click = true;
    } else $("#station_form select[name=typesel] option[value=open]").attr("selected", "selected");
    loadStationForm(0, false);
    pattern = /netsel=([a-zA-Z0-9-]+)/;
    if (result = pattern.exec(hash)) {
	$("#station_form select[name=netsel] option[value=" + result[1] + "]").attr("selected", "selected"); 
	loadStationForm(1, false); click = true;
    } else $("#station_form select[name=netsel] option[value=*]").attr("selected", "selected");    
    pattern = /statsel=([a-zA-Z0-9-]+)/;
    if (result = pattern.exec(hash)) {
	$("#station_form select[name=statsel] option[value=" + result[1] + "]").attr("selected", "selected"); click = true;
    } else $("#station_form select[name=statsel] option[value=*]").attr("selected", "selected");
    pattern = /sensor=(.+?)&/;
    if (result = pattern.exec(hash)) {
	$("#station_form select[name=sensor] option[value=" + result[1] + "]").attr("selected", "selected"); click = true;
    } else $("#station_form select[name=sensor] option[value=all]").attr("selected", "selected");
    pattern = /stream=(.+?)&/;
    if (result = pattern.exec(hash)) {
	var temp = result[1].replace(/\+/g, " ");
	$("#station_form input[name=stream]").val(temp); click = true;
    } else $("#station_form input[name=stream]").val("*");
    pattern = /loc=(.+?)&/;
    if (result = pattern.exec(hash)) {
	var temp = result[1].replace(/\+/g, " ");
	$("#station_form input[name=loc]").val(temp); click = true;
    } else $("#station_form input[name=loc]").val("*");
    pattern = /slatmin=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
	$("#station_form input[name=latmin]").val(result[1]); click = true;
    } else $("#station_form input[name=latmin]").val("-90");
    pattern = /slatmax=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
	$("#station_form input[name=latmax]").val(result[1]); click = true;
    } else $("#station_form input[name=latmax]").val("90");
    pattern = /slonmin=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
	$("#station_form input[name=lonmin]").val(result[1]); click = true;
    } else $("#station_form input[name=lonmin]").val("-180");
    pattern = /slonmax=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
	$("#station_form input[name=lonmax]").val(result[1]); click = true;
    } else $("#station_form input[name=lonmax]").val("180");
    pattern = /azmin=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
	$(".disaz_form input[name=azmin]").val(result[1]); click = true;
    } else $(".disaz_form input[name=azmin]").val("0");
    pattern = /azmax=([0-9-.]+)/;
    if (result = pattern.exec(hash)) {
	$(".disaz_form input[name=azmax]").val(result[1]); click = true;
    } else $(".disaz_form input[name=azmax]").val("360");
    pattern = /dismin=([0-9.]+)/;
    if (result = pattern.exec(hash)) {
	$(".disaz_form input[name=dismin]").val(result[1]); click = true;
    } else $(".disaz_form input[name=dismin]").val("0");
    pattern = /dismax=([0-9.]+)/;
    if (result = pattern.exec(hash)) {
	$(".disaz_form input[name=dismax]").val(result[1]); click = true;
    } else $(".disaz_form input[name=dismax]").val("180");
    if (click) $("input[name=Bstations]").trigger("click");
    if ($("input[name=zoom]").attr("checked")) $("input[name=zoom]").triggerHandler("click");
    else $("body").removeClass("wait");
}

function restoreFreezedStations() {
    if (window.location.hash.indexOf("&stfreeze=1") != -1)
	$(".stalist input[name=stalistfreeze]").attr("checked", "checked");
}

function displayModule(name, value) {
    if (value == "-") {
        $("." + name).css("display", "none");
        $("input[name=" + name + "]").attr("value", "+");
	if (name == "stalistminmax") $("#modlist").css("display", "none");
    } else {
        $("." + name).css("display", "");
        $("input[name=" + name + "]").attr("value", "-");
	if (name == "stalistminmax") $("#modlist").css("display", "");
    }
}

function clearModule(name) {
    $("#" + name).empty();
    $(".module." + name).css("display", "none");
    $("." + name + "buttons").css("display", "none");
    $("." + name + "legend").css("display", "none");
    if (name == "stalist") {
        destroyMapFeatures(stacount, stastart);
        stacount = 0; stastart = -1;
        if (evstart != -1) evstart = 0;
        $("#modlist").css("display", "none");
	if (window.location.hash.length) window.location.hash = window.location.hash.replace(/&stfreeze=1/, "");
    } else {
        destroyMapFeatures(evcount, evstart);
        evcount = 0; evstart = -1;
        if (stastart != -1) stastart = 0;
	setTimeWindow("usedate");
	$("#station_form .disaz_form").css("display", "none");
	$("#station_form input[name=Breset]").parent().attr("rowspan", "2");
	if (window.location.hash.length) window.location.hash = window.location.hash.replace(/&evfreeze=\[([0-9,]+)\]/, "");
    }
}

function getEvents() {
    var startdate=$("#date_form input[name=startdate]").val();
    var enddate=$("#date_form input[name=enddate]").val();
    var mag=parseFloat($("#event_form input[name=mag]").val());
    var depth=parseFloat($("#event_form input[name=depth]").val());

    switch ( $("#event_form select[name=dbsel]").val() ) {
    case "GFZ":
	getEventsFromGFZ(startdate, enddate, mag, depth,
			 eRegion[0], eRegion[1], eRegion[2], eRegion[3])
	break;
    case "NEIC":
	getEventsFromNEIC(startdate, enddate, mag, depth,
			  eRegion[0], eRegion[1], eRegion[2], eRegion[3]);
	break;
    case "IRIS":
	getEventsFromIRIS(startdate, enddate, mag, depth,
			  eRegion[0], eRegion[1], eRegion[2], eRegion[3]);
	break;
    default:
	print("Crash and burn!");
	break;
    }
    $("#station_form input[name=Breset]").parent().attr("rowspan", "4");
    $("#station_form .disaz_form").css("display", "");
}

function getEventsFromGFZ(start, end, mag, depth, latmin, latmax, lonmin, lonmax) {
    var local = restore; // because of asyncronous Ajax call
    var oldcount = evcount;
    evcount = 0;
    var url = "http://geofon.gfz-potsdam.de/eqinfo/list.php?datemin=" + start + "&datemax=" + end;
    url += "&magmin=" + mag + "&latmin=" + latmin + "&latmax=" + latmax + "&lonmin=" + lonmin + "&lonmax=" + lonmax;
    url += "&fmt=txt&nmax=1000";
    $("#eqinfo").load("proxy?url=" + url, function () {
            filterEventsFromGFZ(mag, depth, latmin, latmax, lonmin, lonmax);
            eventsMap(oldcount, evstart);
            if (stastart != -1) stastart = 0;
            if (evcount > 0) {
                stastart == -1 ? evstart = 0 : evstart = stacount;
                $(".module.eqinfo").css("display", "");
                $(".eqinfobuttons").css("display", "");
                $("#legend").css("display", "");
		$(".eqinfolegend td:eq(1)").css("display", "none");
		$(".eqinfolegend td:gt(1)").css("display", "");
                $(".eqinfolegend").css("display", "");
		setTimeWindow("useevents");
		if (local) restoreFreezedEvents();
            } else {
                alert("Got no events for the selected day and options!");
		evcount = oldcount;
		clearModule("eqinfo");
                if ($(".stalistlegend").css("display") == "none") $("#legend").css("display", "none");
            }
	    if (!local) {
		saveState();
		$("body").removeClass("wait");
	    }
        });
}

function filterEventsFromGFZ(mag, depth, latmin, latmax, lonmin, lonmax) {
    var newcontent = "<table class='fullwidth'><tr><th>Origin Time<br>UTC</th><th class='mag'>Mag</th><th>Latitude<br>degrees</th><th>Longitude<br>degrees</th><th>Depth<br>km</th><th>Region Name</th></tr>";
    var content = $("#eqinfo").text();
    $("#eqinfo").empty();
    var pattern = /gfz.*?\s+?(.*?)\s+?([0-9.]+)\s+?[ACM]\s+?([0-9-]+? [0-9-:]+?)\s+?([0-9.-]+?)\s+?([0-9.-]+?)\s+?([0-9.]+?)\s+?([0-9.]+?)\s*?/g;
    var expres;
    var rowclass = "evnrow";
    while (expres = pattern.exec(content)) {
	var lat = expres[4], lon = expres[5];
	var evdatetime = expres[3];
	if (lat >= latmin && lat <= latmax && lon >= lonmin && lon <= lonmax && expres[2] >= mag && expres[6] <= depth) {
	    var region = "";
	    $.ajax({url: "getRegion?lat=" + lat + "&lon=" + lon, async: false, success: function(data) {region = data;}});
	    lat.slice(0,1) == "-" ? lat = lat.substr(1) + " S": lat += " N";
	    lon.slice(0,1) == "-" ? lon = lon.substr(1) + " W" : lon += " E";
	    if (expres[2] >= 6.5) rowclass += " xxlevt";
	    else if (expres[2] >= 5.5) rowclass += " bigevt";
	    newcontent += "<tr class='" + rowclass + "'><td><input type='checkbox' name='onMap' value='" + evdatetime + "' checked><span>" + evdatetime + "</span></td><td class='mag'>M" + expres[2] + "</td><td align='right'>" + lat + "</td><td align='right'>" + lon + "</td><td class='depth'>" + expres[6] + "</td><td>" + region + "</td></tr>";
	    var idx = rowclass.indexOf(" ");
	    if (idx != -1) rowclass = rowclass.substr(0,idx);
	    rowclass == "oddrow" ? rowclass = "evnrow" : rowclass = "oddrow";
	    ++evcount;
	}
    }
    newcontent += "</table>";
    newcontent = "<p>Source: filterEventsFromGFZ. Number of events: " + evcount + "</p>" + newcontent;
    $("#eqinfo").append(newcontent);
    $("#eqinfo input[name=onMap]").bind("change", function() {
	    displayFeature($(this).attr("checked"), $(this).val(), evcount, evstart);
	    $(".eqinfo input[name=eqinfofreeze]").attr("checked", "");
	});
}

function getEventsFromNEIC(start, end, mag, depth, latmin, latmax, lonmin, lonmax) {
    // Output from NEIC seems to be comma-separated.

    var local = restore; // because of asyncronous Ajax call
    var oldcount = evcount;
    evcount = 0;
    var url = "http://neic.usgs.gov/cgi-bin/epic/epic.cgi?SEARCHMETHOD=1&FILEFORMAT=6&SEARCHRANGE=HH";
    var sarr = start.split("-"), earr = end.split("-");
    url += "&SYEAR=" + sarr[0] + "&SMONTH=" + sarr[1] + "&SDAY=" + sarr[2];
    url += "&EYEAR=" + earr[0] + "&EMONTH=" + earr[1] + "&EDAY=" + earr[2];
    url += "&LMAG=" + mag + "&UMAG=9.9&NDEP1=0&NDEP2=" + depth + "&SUBMIT=Submit+Search";
    $("#eqinfo").load("proxy?url=" + url + " pre", function() {
	    filterEventsFromNEIC(latmin, latmax, lonmin, lonmax);
            eventsMap(oldcount, evstart);
            if (stastart != -1) stastart = 0;
            if (evcount > 0) {
                stastart == -1 ? evstart = 0 : evstart = stacount;
		//$(".module.eqinfo").css("display", "");
		//$(".eqinfobuttons").css("display", "");
                //$("#legend").css("display", "");
		//$(".eqinfolegend td:eq(1)").css("display", "");
		//$(".eqinfolegend td:gt(1)").css("display", "none");
                //$(".eqinfolegend").css("display", "");
		//setTimeWindow("useevents");
		//if (local) restoreFreezedEvents();
            } else {
                alert("Got no events for the selected day and options!");
		evcount = oldcount;
		clearModule("eqinfo");
                if ($(".stalistlegend").css("display") == "none") $("#legend").css("display", "none");
            }	    
	    if (!local) {
		saveState();
		$("body").removeClass("wait");
	    }
	});
}

function getEventsFromIRIS(start, end, mag, depth, latmin, latmax, lonmin, lonmax) {
    // Both start and end are 'YYYY-MM-DD' strings.
    // Calls IRIS's fdsnws-event web service.
    // 2013: For now, use their text output, which is CSV with '|' as separator.

    var local = restore; // because of asyncronous Ajax call
    var oldcount = evcount;
    evcount = 0;
    var url = "http://service.iris.edu/fdsnws/event/1/query?";
    url += "output=text";

    url += "&minlat=" + latmin;
    url += "&maxlat=" + latmax;
    url += "&minlon=" + lonmin;
    url += "&maxlon=" + lonmax;
    url += "&starttime=" + start;
    url += "&endtime=" + end;
    url += "&minmagnitude=" + mag;
    url += "&maxdepth=" + depth;
//    url += "&LMAG=" + mag + "&UMAG=9.9&NDEP1=0&NDEP2=" + depth + "&SUBMIT=Submit+Search";
//    $("#eqinfo").load("proxy?url=" + url + " pre", function() {
    $("#eqinfo").load("proxy?url=" + url, function() {
	    filterEventsFromIRIS(latmin, latmax, lonmin, lonmax);
            eventsMap(oldcount, evstart);
            if (stastart != -1) stastart = 0;

            if (evcount > 0) {
                stastart == -1 ? evstart = 0 : evstart = stacount;
		$(".module.eqinfo").css("display", "");
		$(".eqinfobuttons").css("display", "");
                $("#legend").css("display", "");
		$(".eqinfolegend td:eq(1)").css("display", "");
		$(".eqinfolegend td:gt(1)").css("display", "none");
                $(".eqinfolegend").css("display", "");
		setTimeWindow("useevents");
		if (local) restoreFreezedEvents();
            } else {
                alert("IRIS had no events for the selected day and options!:" + url);
		evcount = oldcount;
		clearModule("eqinfo");
                if ($(".stalistlegend").css("display") == "none") $("#legend").css("display", "none");
            }	    
	    if (!local) {
		saveState();
		$("body").removeClass("wait");
	    }
	});
    $("#eqinfo").css("display", "");  // PLE: Force it to be visible!??!
}

function filterEventsFromNEIC(latmin, latmax, lonmin, lonmax) {
    var newcontent = "</table>";  // Gets built up from the bottom
    var content = $("#eqinfo pre").text();
    $("#eqinfo").empty();
    var pattern = /\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+).\d*,\s*([0-9-.]+),\s*([0-9-.]+),\s*([0-9.]+),\s*([0-9.]+)/g;
    var expres;
    var rowclass = "evnrow";

    //  0   1     2   3                  4        5         6         7
    // Year,Month,Day,Time(hhmmss.mm)UTC,Latitude,Longitude,Magnitude,Depth,Catalog
    while (expres = pattern.exec(content)) {
	var lat = expres[5], lon = expres[6];
	var evtime = expres[4].slice(0,2) + ":" + expres[4].slice(2,4) + ":" + expres[4].slice(4,6);
	if (lat >= latmin && lat <= latmax && lon >= lonmin && lon <= lonmax) {
	    var region = "";
	    $.ajax({url: "getRegion?lat=" + lat + "&lon=" + lon, async: false, success: function(data) {region = data;}});
	    lat.slice(0,1) == "-" ? lat = lat.substr(1) + " S": lat += " N";
	    lon.slice(0,1) == "-" ? lon = lon.substr(1) + " W" : lon += " E";
	    if (expres[7] >= 6.5) rowclass += " xxlevt";
	    else if (expres[7] >= 5.5) rowclass += " bigevt";
	    newcontent = "<tr class='" + rowclass + "'><td><input type='checkbox' name='onMap' value='" + expres[1] + "-" + expres[2] + "-" + expres[3] + " " + evtime + "' checked><span>" + expres[1] + "-" + expres[2] + "-" + expres[3] + " " + evtime + "</span></td><td class='mag'>" + expres[7] + "</td><td align='right'>" + lat + "</td><td align='right'>" + lon + "</td><td class='depth'>" + expres[8] + "</td><td>" + region + "</td></tr>" + newcontent;
	    rowclass == "oddrow" ? rowclass = "evnrow" : rowclass = "oddrow";
	    ++evcount;
	}
    }
    newcontent = "<table class='fullwidth'><tr><th>Origin Time<br>UTC</th><th class='mag'>Mag</th><th>Latitude<br>degrees</th><th>Longitude<br>degrees</th><th>Depth<br>km</th><th>Region Name</th></tr>" + newcontent;
    newcontent = "<p>Source: filterEventsFromNEIC. Number of events: " + evcount + "</p>" + newcontent;
    $("#eqinfo").append(newcontent);
    $("#eqinfo input[name=onMap]").bind("change", function() {
	    displayFeature($(this).attr("checked"), $(this).val(), evcount, evstart);
	    $(".eqinfo input[name=eqinfofreeze]").attr("checked", "");
	});
}

function filterEventsFromIRIS(latmin, latmax, lonmin, lonmax) {
    // Current output (April 2013) is "text", which is CSV with
    //  '|' as separator.
    //  '#' as comment introducer
    //
    // Input is from $("#eqinfo").
    // Find events which are in the lat-lon rectangle.
    // This function must set the global variable 'evcount' and
    // append its new material to $("#eqinfo").

    var newcontent = "</table>";
    //var content = $("#eqinfo pre").text();
    var content = $("#eqinfo").text();
    $("#eqinfo").empty();

    // EventID | Time | Latitude | Longitude | Depth/KM | Author | Catalog | Contributor | ContributorID | MagType | Magnitude | MagAuthor | EventLocationName
    // separated by nl!

    // var pattern = /\s*(\d+)\s*(\d+)\|\s*(\d+)\|\s*(\d+).\d*\|\s*([0-9-.]+)\|\s*([0-9-.]+)\|\s*([0-9.]+)\|\s*([0-9.]+)/g;
    //var pattern = /.*/g;
    //var pattern = /.*\|.*$/g;

    // Too hard. Split the whole result into lines, then iterate over
    // lines. This may be expensive!
    var lines = content.split("\n");
    var pattern1 = new RegExp("EventID");

    var words;
    var expres;
    var rowclass = "evnrow";

    var evid, evdatetime, lat, lon, mag, depth;
    //while (expres = pattern.exec(content)) {
    lines.forEach(function(line) {

        //alert(line);
	//words = content.split("|");
	words = line.split("|");
	evid = words[0];
	if (pattern1.test(evid)) {
	    return; // this is a function!
	    evid += "HEADER";
	}
	evdatetime = words[1];
	if (evdatetime) {
	    lat = words[2];
	    lon = words[3];
	    depth = words[4];
	    mag = words[10];
	    var evdate = evdatetime.slice(0,10);    // "YYYY-mm-dd"
	    var evtime = evdatetime.slice(11,19);   // "HH:MM:SS"

	    //alert(evcount + ":" + words.length + "words: evid=" + evid + " evdatetime=" + evdatetime + " lat=" + lat + " lon=" + lon + " mag=" + mag + " depth=" + depth);
	//alert("In the while loop: content.length=" + content.length + " line.length=" + line.length + " evid=" + evid + " evdatetime=" + evdatetime + " lat=" + lat + " lon=" + lon);

	
	//newcontent = "<tr class='" + rowclass + "'><td>" + evid + "</td><td>" + evdate + " " + evtime + "</td></tr>" + newcontent;


	    if (lat >= latmin && lat <= latmax && lon >= lonmin && lon <= lonmax) {

		var region = "";
		$.ajax({url: "getRegion?lat=" + lat + "&lon=" + lon, async: false, success: function(data) {region = data;}});
		lat.slice(0,1) == "-" ? lat = lat.substr(1) + " S": lat += " N";
		lon.slice(0,1) == "-" ? lon = lon.substr(1) + " W" : lon += " E";
		if (mag >= 6.5) rowclass += " xxlevt";
		else if (mag >= 5.5) rowclass += " bigevt";
		newcontent = "<tr class='" + rowclass + "'><td><input type='checkbox' name='onMap' value='" + evdate + " " + evtime + "' checked><span>" + evdate + " " + evtime + "</span></td><td class='mag'>" + mag + "</td><td align='right'>" + lat + "</td><td align='right'>" + lon + "</td><td class='depth'>" + depth + "</td><td>" + region + "</td></tr>" + newcontent;
		rowclass == "oddrow" ? rowclass = "evnrow" : rowclass = "oddrow";
		++evcount;
	    }
	}
    } );
 
    newcontent = "<table class='fullwidth'><tr><th>Origin Time<br>UTC</th><th class='mag'>Mag</th><th>Latitude<br>degrees</th><th>Longitude<br>degrees</th><th>Depth<br>km</th><th>Region Name</th></tr>" + newcontent;
    newcontent = "<p>Source: filterEventsFromIRIS. Number of events: " + evcount + "</p>" + newcontent;
    $("#eqinfo").append(newcontent);
    $("#eqinfo").css("display", ""); // PLE Why did I need to add this?
    $("#eqinfo input[name=onMap]").bind("change", function() {
 	    displayFeature($(this).attr("checked"), $(this).val(), evcount, evstart);
 	    $(".eqinfo input[name=eqinfofreeze]").attr("checked", "");
 	});
}

function loadStationForm(selidx, sync) {
    if (selidx < 2) {
        var args = "start_date=" + $("#date_form input[name=startdate]").val();
        args += "&end_date=" + $("#date_form input[name=enddate]").val();
        args += "&latmin=" + parseFloat($("#station_form input[name=latmin]").val());
        args += "&latmax=" + parseFloat($("#station_form input[name=latmax]").val());
        args += "&lonmin=" + parseFloat($("#station_form input[name=lonmin]").val());
        args += "&lonmax=" + parseFloat($("#station_form input[name=lonmax]").val());
        var type = $("#station_form select[name=typesel]").val();
        if (type) args += "&typesel=" + type;
        if (selidx == 1) {
            var net = $("#station_form select[name=netsel]").val();
            if (net) args += "&netsel=" + net;
        }
        $.ajax({url: "loadStationForm?" + args,
                    async: sync,
                    dataType: "text",
                    success: function(data) {
                    $("#station_form select[name=netsel] option").remove();
                    $("#station_form select[name=statsel] option").remove();
                    var idx = data.indexOf("|");
                    $("#station_form select[name=netsel]").append(data.substr(0, idx));
                    $("#station_form select[name=statsel]").append(data.substr(idx+1));
                    if (!restore) $("body").removeClass("wait");
                }});
    } else {
        var comb = $("#station_form select[name=statsel] :selected").val().split("-").slice(0,3);
        if (comb.length > 1) $("#station_form select[name=netsel]").val(comb.join("-"));
        if (!restore) $("body").removeClass("wait");
    }
}

function setStationList() {
    var oldcount = stacount;
    stacount = $("#statable .sta").length + $("#statable .net").length;
    if (evstart != -1) evstart = 0;
    if (stacount > 0) {
	stationsMap(oldcount, stastart);
	evstart == -1 ? stastart = 0 : stastart = evcount;
	$(".module.stalist").css("display", "");
	$(".stalistbuttons").css("display", "");
	$("#stalist input[name=onMap]").bind("change", function() {
		displayFeature($(this).attr("checked"), $(this).val(), stacount, stastart);
		$(".stalist input[name=stalistfreeze]").attr("checked", "");
	    });
	$("#legend").css("display", "");
	$(".stalistlegend").css("display", "");
	var netclass = "evnrow", staclass, sensclass, strclass;
	$("#statable tr").each(function() {
		if ($(this).hasClass("net")) {
		    $(this).addClass(netclass);
		    netclass == "oddrow" ? netclass = "evnrow" : netclass = "oddrow";
		    staclass = sensclass = strclass = netclass;
		}
		if ($(this).hasClass("sta")) {
		    $(this).addClass(staclass);
		    staclass == "oddrow" ? staclass = "evnrow" : staclass = "oddrow";
		    sensclass = strclass = staclass;
		}
		if ($(this).hasClass("sens")) {
		    $(this).addClass(sensclass);
		    sensclass == "oddrow" ? sensclass = "evnrow" : sensclass = "oddrow";
		    strclass = sensclass;
		}
		if ($(this).hasClass("str")) {
		    $(this).addClass(strclass);
		    strclass == "oddrow" ? strclass = "evnrow" : strclass = "oddrow";
		}
	    });
	$("#modlist").css("display", "");
	stationFeatures();
	$(".stalist input[name=stalistall]").attr("checked", "checked");
    } else {
	alert("Got no stations for the selected day and options!");
	stacount = oldcount;
	clearModule("stalist");
	if ($(".eqinfolegend").css("display") == "none") $("#legend").css("display", "none");
    }
    $("body").removeClass("wait");
}

function getStations() {
    var local = restore; // because of asyncronous Ajax call
    var args = "sesskey=" + $("input[name=sesskey]").val();
    args += "&start_date=" + $("#date_form input[name=startdate]").val();
    args += "&end_date=" + $("#date_form input[name=enddate]").val();
    args += "&nettype=" + $("#station_form select[name=typesel]").val();
    args += "&network=" + $("#station_form select[name=netsel]").val();
    args += "&station=" + $("#station_form select[name=statsel]").val();
    args += "&sensor=" + $("#station_form select[name=sensor]").val();
    if (!$("#station_form input[name=stream]").val()) args += "&stream=*";
    else args += "&" + $("#station_form input[name=stream]").serialize();
    if ($("#station_form input[name=loc]").val())
	args += "&" + $("#station_form input[name=loc]").serialize();
    args += "&latmin=" + parseFloat($("#station_form input[name=latmin]").val());
    args += "&latmax=" + parseFloat($("#station_form input[name=latmax]").val());
    args += "&lonmin=" + parseFloat($("#station_form input[name=lonmin]").val());
    args += "&lonmax=" + parseFloat($("#station_form input[name=lonmax]").val());
    if ($("#eqinfo input[name=onMap]:checked").length) {
	args += "&azmin=" + parseFloat($("#station_form .disaz_form input[name=azmin]").val());
	args += "&azmax=" + parseFloat($("#station_form .disaz_form input[name=azmax]").val());
	args += "&dismin=" + parseFloat($("#station_form .disaz_form input[name=dismin]").val());
	args += "&dismax=" + parseFloat($("#station_form .disaz_form input[name=dismax]").val());
	var events = "";
	$.each($("#eqinfo input[name=onMap]:checked"), function() {
		if (events.length) events += ",";
		var lat = $(this).parent().nextAll().eq(1).text().split(" ");
		var lon = $(this).parent().nextAll().eq(2).text().split(" ");
		lat[1] == "S" ? lat = parseFloat(lat[0]) * -1 : lat = parseFloat(lat[0]);
		lon[1] == "W" ? lon = parseFloat(lon[0]) * -1 : lon = parseFloat(lon[0]);
		events += lat + "_" + lon;
        });
	if (events.length) args += "&evcoord=" + events;
    }
    if (local) args += "&xsl=1";
    $("#stalist").load("loadStationList?" + args, function () {
	    setStationList();
	    if (!local) saveState();
	    else restoreFreezedStations();
       });
}

function selectAll(name, check) {
    $("body").addClass("wait");
    window.setTimeout(function () {
	    $("#" + name + " input[name=onMap]").attr("checked", check);
	    name == "stalist" ? displayAllFeatures(check, stacount, stastart) : displayAllFeatures(check, evcount, evstart);
	    $("body").removeClass("wait");}, 500);
}

function resetRegion(id) {
    $("#" + id + " input[name=latmin]").val("-90");
    $("#" + id + " input[name=latmax]").val("90");
    $("#" + id + " input[name=lonmin]").val("-180");
    $("#" + id + " input[name=lonmax]").val("180");
    if (id == "station_form") {
	$("#" + id + " input[name=azmin]").val("0");
	$("#" + id + " input[name=azmax]").val("360");
	$("#" + id + " input[name=dismin]").val("0");
	$("#" + id + " input[name=dismax]").val("180");
    }
}

function setRegion(id) {
    var arr = eRegion;
    if (id == "station_form") arr = sRegion;
    arr[0] = parseFloat($("#" + id + " input[name=latmin]").val());
    arr[1] = parseFloat($("#" + id + " input[name=latmax]").val());
    arr[2] = parseFloat($("#" + id + " input[name=lonmin]").val());
    arr[3] = parseFloat($("#" + id + " input[name=lonmax]").val());
}

function setTimeWindow(name) {
    $("#tw_form div[class*=use]").css("display", "none");
    $("#tw_form ." + name).css("display", "");
}

function stationFeatures() {
    $(".showcol").bind("click", function() {
	    var check = $(this).attr("checked");
	    var name = $(this).attr("name");
	    $("body").addClass("wait");
	    window.setTimeout(function () {
		    check ? $("#statable ." + name).css("display", "table-cell") : $("#statable ." + name).css("display", "none");
		    $("body").removeClass("wait");}, 500);
	});
}

function freeze(name, bool, visible) {
    if (name == "stalistfreeze") {
        if (bool) {
            if ($("#stalist input[name=onMap]:not(:checked)").length) {
                var args = "";
                $.each($("#stalist input[name=onMap]:not(:checked)"), function() {
                        if (args.length) args += ";";
                        args += $(this).val().replace(" ", "_");
                    });
		if (visible) {
		    clearModule("stalist");
		    $("#stalist").load("freeze?" + $("input[name=sesskey]").serialize() + "&exsta=" + args, function() {
			    setStationList();
                       });
		} else $.get("freeze?" + $("input[name=sesskey]").serialize() + "&exsta=" + args + "&nodata=1");
		if (window.location.hash.indexOf("&stfreeze=1") == -1) window.location.hash += "&stfreeze=1";
            }
        } else {
            if (window.location.hash.indexOf("&stfreeze=1") != -1) {
		clearModule("stalist");
		$("#stalist").load("freeze?" + $("input[name=sesskey]").serialize(), function() {
			setStationList();
                   });
            }
        }
    } else {
	if (bool) {
	    if ($("#eqinfo input[name=onMap]:not(:checked)").length) {
		var args = "";
		$.each($("#eqinfo input[name=onMap]:not(:checked)"), function() {
			if (visible) $(this).parents("tr").css("display", "none");
			if (args.length) args += ",";
			args += $(this).parents("tr").index();		    
		    });
		if (window.location.hash.indexOf("&evfreeze=") != -1) 
		    window.location.hash = window.location.hash.replace(/&evfreeze=\[([0-9,]+)\]/, "");
		window.location.hash += "&evfreeze=[" + args + "]";
	    }
	} else {
	    if (window.location.hash.indexOf("&evfreeze=") != -1) {
		$("#eqinfo tr").css("display", "");
		$("#eqinfo input[name=onMap]:not(:checked)").attr("checked", "checked").trigger("change");
		window.location.hash = window.location.hash.replace(/&evfreeze=\[([0-9,]+)\]/, "");		
	    }
	}	
	$(".eqinfo input[name=eqinfoall]").attr("checked", "checked");
    }
    $("body").removeClass("wait");
}

function completeRequest() {
    if (!$("#stalist input[name=onMap]:checked").length) {
        alert("No stations selected!");
        return;
    }
    if ($("#eqinfo input").length && !$("#eqinfo input[name=onMap]:checked").length) {
        alert("No events selected!");
        return;
    }
    var args = $("input[name=sesskey]").serialize();
    if (!$("#eqinfo input").length)
	args += "&start=" + $("#date_form input[name=startdate]").val() + " " + $("#tw_form input[name=twstart]").val() + 
	    "&end=" + $("#date_form input[name=enddate]").val() + " " + $("#tw_form input[name=twend]").val();
    else {
	var events = "";
	args += "&" + $("#tw_form input[name=before]").serialize() + "&" + $("#tw_form input[name=after]").serialize();
	$.each($("#eqinfo input[name=onMap]:checked"), function() {
		if (events.length) events += ";";
		var lat = $(this).parent().nextAll().eq(1).text().split(" ");
		var lon = $(this).parent().nextAll().eq(2).text().split(" ");
		lat[1] == "S" ? lat = parseFloat(lat[0]) * -1 : lat = parseFloat(lat[0]);
		lon[1] == "W" ? lon = parseFloat(lon[0]) * -1 : lon = parseFloat(lon[0]);
		var depth = parseFloat($(this).parent().nextAll(".depth").text());
		events += $(this).val() + "_" + lat + "_" + lon + "_" + depth;
        });
	if (events.length) args += "&events=" + events;
    }
    freeze("stalistfreeze", true, false);
    freeze("eqinfofreeze", true, false);
    window.location.href = "select?" + args;
}


