
function wrapWindow(text) {
	return `if (typeof pyloadWindow == 'undefined')
	{
		var pyloadWindow = null;	
	}
	if (typeof pyloadWindowKeys == 'undefined')
	{
		pyloadWindowKeys = [];
	}
	
	 (function () {
		let origWindow = window;
		(function () {
			let Sizzle = undefined;
			let window = {
				set Sizzle(sizzle) {
					Sizzle = sizzle;
					this._sizzle = sizzle;
				},
				get Sizzle() {
					return this._sizzle;
				}
			};
			let top = undefined;
			let location = undefined;
			if (pyloadWindow === null)
			{
				let keys = [];
				for (var key of Object.keys(origWindow)) {
					if (['top', 'localStorage', 'indexedDB', 'sessionStorage'].indexOf(key) === -1)
					{
						window[key] = origWindow[key];
					}
					pyloadWindowKeys.push(key);
				}
				window.top = window;
				top = window.top;
				location = window.location;
				pyloadWindow = window;
			}
			else
			{
				window = pyloadWindow;
			}
			debugger;
			(function() {`+text+`}).apply(window);
			for (var key of Object.keys(origWindow)) {
				if (pyloadWindowKeys.indexOf(key) === -1)
				{
					origWindow[key] = window.key;
					pyloadWindowKeys.push(key);
				}
			}
		})();
	})();`;
}

function decodeChunks(chunkData, decoder)
{
	let str = '';
	if (chunkData.length === 1)
	{
		str = decoder.decode(chunkData[0], {stream: true});
	}
	else {
		for (let i = 0; i < chunkData.length; i++) {
			let stream = (i == chunkData.length - 1) ? false : true;
			str += decoder.decode(chunkData[i], {stream});
		}
	}
	return str;
}
function filecryptListener(details) {
	let filter = browser.webRequest.filterResponseData(details.requestId);
	let decoder = new TextDecoder("utf-8");
	let encoder = new TextEncoder();
	let chunkData = [];

	filter.ondata = event => {
		chunkData.push(event.data);
	};

	filter.onstop = event => {
		let str = decodeChunks(chunkData, decoder);
		let replacedStr = '';

		// Just change any instance of Example in the HTTP response
		// to WebExtension Example.
		if (details.url.match(/\.js(?:\?(?:.*))$/))
		{
			replacedStr = wrapWindow(str);
			filter.write(encoder.encode(replacedStr));
		}
		else
		{
			filter.write(encoder.encode(str));
		}

		filter.close();
	};

	return {};
}

function cutcaptchaListener(details) {
	let filter = browser.webRequest.filterResponseData(details.requestId);
	let decoder = new TextDecoder("utf-8");
	let encoder = new TextEncoder();
	let chunkData = [];
	let replacedStr = '';

	filter.ondata = event => {
		data.push(event.data);
	};

	filter.onstop = event => {
		let str = decodeChunks(chunkData, decoder);

		// Just change any instance of Example in the HTTP response
		// to WebExtension Example.
		if (details.url.match(/\.js(?:\?(?:.*))$/))
		{
			replacedStr = wrapWindow(str);
			filter.write(encoder.encode(replacedStr));
		}
		else
		{
			filter.write(encoder.encode(str));
		}

		filter.disconnect();
	};

	return {};
}

browser.webRequest.onBeforeRequest.addListener(
	filecryptListener,
	{urls: ["*://filecrypt.cc/*", "*://www.filecrypt.cc/*"], types: ["main_frame", "script", "sub_frame"]},
	["blocking"]
);

browser.webRequest.onBeforeRequest.addListener(
	cutcaptchaListener,
	{urls: ["*://cutcaptcha.com/*"], types: ["main_frame", "script", "sub_frame"]},
	["blocking"]
);