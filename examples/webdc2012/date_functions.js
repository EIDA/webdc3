$(document).ready(function() {
	var date = new Date();
	var datestr = date.getFullYear() + "-";
	date.getMonth() < 9 ? datestr += "0" + (date.getMonth() + 1) + "-" : datestr += (date.getMonth() + 1) + "-";
	date.getDate() < 10 ? datestr += "0" + date.getDate() : datestr += date.getDate();
	$("#date_form input[name=startdate]").val(datestr);
	$("#date_form input[name=enddate]").val(datestr);
	$("#date_form input[name=startdate]+sub img").DatePicker({date: $("#date_form input[name=startdate]").val(), 
		    position: 'right',
		    onBeforeShow: function() {
		    $("#date_form input[name=startdate]+sub img").DatePickerSetDate($("#date_form input[name=startdate]").val(), true);},
		    onChange: function(formated, date) {
		    $("#date_form input[name=startdate]").val(formated);
		    $("#date_form input[name=startdate]+sub img").DatePickerHide();
		    clearModule("eqinfo"); clearModule("stalist");
		    checkDate("start");}
	    });
	$("#date_form input[name=enddate]+sub img").DatePicker({date: $("#date_form input[name=enddate]").val(), 
		    position: 'right',
		    onBeforeShow: function() {
		    $("#date_form input[name=enddate]+sub img").DatePickerSetDate($("#date_form input[name=enddate]").val(), true);},
		    onChange: function(formated, date) {
		    $("#date_form input[name=enddate]").val(formated);
		    $("#date_form input[name=enddate]+sub img").DatePickerHide();
		    clearModule("eqinfo"); clearModule("stalist");
		    checkDate("end");}
	    });
	$("#date_form input[name$=date]").bind("change", function() {
		clearModule("eqinfo"); clearModule("stalist");
		checkDate($(this).attr("name").slice(0,-4));
	    });
	$("#tw_form input[name=twstart]").val("00:00:00");
	$("#tw_form input[name=twend]").val("23:59:59"); 
    });

function saveDate() {
    var start = $("#date_form input[name=startdate]").val() + " " + $("#tw_form input[name=twstart]").val();
    var end = $("#date_form input[name=enddate]").val() + " " + $("#tw_form input[name=twend]").val();
    return "start=" + start + "&end=" + end;
}

function restoreDate() {
    var hash = window.location.hash.substr(1);
    var start = "", end = "";
    var spattern = /start=([0-9-: ]+)/;
    var epattern = /end=([0-9-: ]+)/;
    var result = "";
    if (result = spattern.exec(hash)) start = result[1];    
    if (result = epattern.exec(hash)) end = result[1];
    if (start.length || end.length) {
        if (!start.length) start = end;
        if (!end.length) end = start;
	var tmp = start.split(" ");
	$("#date_form input[name=startdate]").val(tmp[0]);
	$("#tw_form input[name=twstart]").val(tmp[1]);
	tmp = end.split(" ");
	$("#date_form input[name=enddate]").val(tmp[0]);
	$("#tw_form input[name=twend]").val(tmp[1]);
    }
}

function checkDate(type) {
    if ($("#date_form input[name=startdate]").val() > $("#date_form input[name=enddate]").val())
	type == "start" ? $("#date_form input[name=enddate]").val($("#date_form input[name=startdate]").val()) :
	    $("#date_form input[name=startdate]").val($("#date_form input[name=enddate]").val());
    $("select[name=typesel]").triggerHandler("change");
}

function diffDate(date1, date2) {
    var diff1 = new Date();
    var diff2 = new Date();
    var pattern = new RegExp("([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})");
    var matched = pattern.exec(date1);
    if (matched) {
	diff1.setFullYear(matched[1]);
        diff1.setMonth(matched[2] - 1);
        diff1.setDate(matched[3]);
        diff1.setHours(matched[4]);
        diff1.setMinutes(matched[5]);
        diff1.setSeconds(matched[6]);
    }
    matched = pattern.exec(date2);
    if (matched) {
	diff2.setFullYear(matched[1]);
        diff2.setMonth(matched[2] - 1);
        diff2.setDate(matched[3]);
        diff2.setHours(matched[4]);
        diff2.setMinutes(matched[5]);
        diff2.setSeconds(matched[6]);
    }
    return (Math.ceil(diff1.getTime()-diff2.getTime()));
}
