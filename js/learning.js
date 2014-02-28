//
// Test script used by test/testpost.html
//
var colour = "purple";

function whatColor() {
	console.log("In whatColor");
	var content = "RED, NO, GREEN";
	content = colour;
	$( "#learnbox" ).empty().append( content );
};

// whatColor();

function myPost(url, params) {
	$( "#learnbox-url").empty().append("URL: " + url);
	$( "#learnbox-params").empty().append("Parameters: " + "<br />");
	for (var k in params) {
		$( "#learnbox-params" ).append(k + ": " + params[k] + "<br />");
	};
	$.post( url, params,
		function (data, textStatus, jqXHR) {
			console.log("Done POST " + url);
			// DUMP RAW OUTPUT INTO THE BOX!
			var report;
			if (typeof data === "undefined") {
				report = "[undefined]";
			} else {
				report = "<pre>" + data + "</pre>";
			};
			$( "#learnbox-result" ).empty().append( report );
		});
}

// This is server-specific:
//var baseurl="/webinterface/wsgi";
var baseurl="/testwi/webdc3/wsgi";  // For sec24c106.
var url;
var params;

if ( false ) {
    url =  "/webinterface/wsgi/metadata/streams";
    params = {network: "all", station: "all",
	      start: "2000", end: "2015",
	      networktype: "all"};
};

test_export = false;
test_import = true;
test_streams = false;

if ( test_export ) {
	url = baseurl + "/metadata/export";
	params = {streams: '[["GE", "APE", "BHZ", ""], ["AK", "BBB", "BHZ", "10"]]'};
	expected = "Formatted CSV table of 'N S L C' lines.";
} else if ( test_import ) {
	url = baseurl + "/metadata/import";
        params = {file: 'GE APE -- BHZ\nGE KBU 10 BHZ\nGE APE -- BHE\nGE APE -- BHN\n'}
        // Simple - 1 station:
	// params = {file: 'GE APE -- BHZ\nGE APE -- BHE\n'}
	expected = "Pack object for addStations";

} else if ( test_streams) {
	url = baseurl + "/metadata/streams";
	params = {network: "GE-1993-None", station: "all",
		start: "2010",
		end: "2015",
		networktype: "all"};
	expected = Array("BH", "LH", "VH", "...", "BN");
} else {
	url = baseurl + "/metadata/networktypes";
	params = {};
	expected = "List: all, virt, permr, permo, etc.";
};

myPost(url, params);
$('#learnbox-expect').empty().append("<p>" + expected + "</p>");

