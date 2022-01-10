/*
 * GEOFON WebInterface
 *
 * Begun by:
 *  Marcelo Bianchi, Peter Evans, Javier Quinteros, GFZ Potsdam
 *
 * interface.js module: Control page layout disposition and animations.
 *                      This is not really needed to have the portal running,
 *                      it is implemented based on the template file supplied.
 *
 */
function interface_swap(obj) {
	var parent = $(obj.target).parent().parent();
	var frame = parent.children('.frame');
	if (frame.css('display') === "block") {
		frame.toggle();
	} else {
		$(".canhide").children('.frame').hide();
		frame.toggle();
	}
}

function interface_init() {
	var tabControl = $("#wi-TabControl")

	tabControl.buttonset()
	tabControl.css('display', 'block')

	tabControl.change(function(item) {
		$('#contents').children().children('.tab').css('display', 'none')
		$('#contents').children().children('.' + $(item.target).val()).css('display', 'block')

		if ($(item.target).val() == 'console') {
			wiConsole.scrollToBottom()
			wiConsole.resetLevel()
			$('#wi-ConsoleLabel').removeClass('wi-console-warning-tab')
			$('#wi-ConsoleLabel').removeClass('wi-console-error-tab')
		}
		else if ($(item.target).val() == 'download') {
			$('#wi-DownloadLabel').removeClass('wi-download-alert-tab')
		}
	})

	if (wiConsole.level() <= 2) {
		$('#wi-EventExplorerTab').prop('checked', true)
		$('#wi-EventExplorerTab').change()
	}
	else {
		$('#wi-ConsoleTab').prop('checked', true)
		$('#wi-ConsoleTab').change()
	}

	wiConsole.setCallback(function(level, msgClass) {
		if ((msgClass == 'wi-console-warning' || msgClass == 'wi-console-error') &&
				$('#wi-Console').is(':hidden'))
			$('#wi-ConsoleLabel').addClass(msgClass + '-tab')
		else
			wiConsole.resetLevel()
	})

	wiFDSNWS_Control.setCallback(function() {
		if ($('#wi-FDSNWS-Control').is(':hidden'))
			$('#wi-DownloadLabel').addClass('wi-download-alert-tab')
	})

	/* Bind "canhide" h2/help to open and close the "frame" below */

	/*.help */
	$(".canhide").find(".help").bind("click",interface_swap);
	$(".canhide").find('.help').css("cursor", "pointer");

	/* h2 */
	$(".canhide").find("h2").bind("click",interface_swap);
	$(".canhide").find('h2').css("cursor", "pointer");

	/* Initial setup - close all */
	$(".canhide").children('.frame').toggle();
}

/*
 * Export for main.js
 */
export default function() {
	return new Promise(function(resolve, reject) {
		try {
			interface_init();
			resolve();
		}
		catch (e) {
			if (console.error !== wiConsole.error)
				console.error("interface.js: " + e.message);

			wiConsole.error("interface.js: " + e.message, e);
			reject();
		}
	});
}
