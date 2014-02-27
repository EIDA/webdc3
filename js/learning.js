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
	$( "#learnbox-params").empty();
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

var baseurl="/webinterface/wsgi";
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

if ( test_export ) {
	url = baseurl + "/metadata/export";
	params = {streams: '[["GE", "APE", "BHZ", ""], ["AK", "BBB", "BHZ", "10"]]'};
} else if ( test_import ) {
	url = baseurl + "/metadata/import";
        params = {file: 'GE APE -- BHZ\nGE KBU 10 BHZ\nGE APE -- BHE\nGE APE -- BHN\n'}
        // Simple - 1 station:
	// params = {file: 'GE APE -- BHZ\nGE APE -- BHE\n'}
};

myPost(url, params);
