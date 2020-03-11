
function wrapWindow(text, after) {
	 return `(function () {
	    window.document['addMockedEventListener'] = function()
	    {
	        document.addEventListener.apply(document, arguments);
	    }
		let origWindow = window;
		let windowMockData = {
		    "addMockedEventListener": function()
		    {
		        origWindow.addEventListener.apply(origWindow, arguments);
		    },
		    "removeMockedEventListener": function()
		    {
		        origWindow.removeEventListener.apply(origWindow, arguments);
		    }
		};
		(function () {
		    let findTop = function(childWindow)
		    {
		        if (typeof childWindow == 'undefined')
		        {
		            childWindow = origWindow;
		        }
		        if (childWindow.parent === childWindow)
		        {
		            topWindow = childWindow;
		        }
		        else
		        {
		            topWindow = findTop(childWindow.parent);
		        }

		        return topWindow;
		    }
		    let revocableWindowProxy = Proxy.revocable(windowMockData, {
		        get: function(target, name) {
		            let returnValue = undefined;
		            if (name in windowMockData)
		            {
		                returnValue = windowMockData[name];
		            }
		            else if (name in origWindow)
		            {
		                returnValue = origWindow[name];
		            }

		            return returnValue;
		        },
		        set: function(target, prop, value) {
		            origWindow[prop] = value;
		            return true;
		        },
		        has: function(target, key) {
		            let hasValue = false;
		            if (key in windowMockData)
		            {
		                hasValue = true;
		            }
		            else if (name in origWindow)
		            {
		                hasValue = true;
		            }

		            return hasValue;
		        },
		        getPrototypeOf: function(target)
		        {
		            return Object.getPrototypeOf(origWindow);
		        }
		    });
			let window = revocableWindowProxy.proxy;
			let top = undefined;

            windowMockData['top'] = findTop();
            top = window.top;

			(function() {`+text+after+`}).apply(window);
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
		if (details.url.match(/\.js(?:\?(?:.*))?$/))
		{

		    after = '';
		    if (details.url.match(/prototype\.js/))
			{
                after = 'origWindow.Prototype = Prototype; origWindow.Class = Class;'
			    after += 'origWindow.Enumerable = Enumerable; origWindow[\'$H\'] = $H; origWindow[\'$w\'] = $w;';
			    after += 'origWindow[\'Ajax\'] = Ajax;';
			    after += 'origWindow[\'Field\'] = Field;';
                after += 'origWindow[\'Form\'] = Form;';
			}
			if (details.url.match(/effects\.js/))
			{
			    after += 'origWindow[\'Effect\'] = Effect;';
			}
			replacedStr = wrapWindow(str, after);

			if (details.url.match(/prototype\.js/))
			{
			    replacedStr = replacedStr.replace('Event.observe(window, \'load\', fireContentLoadedEvent);', 'Event.observe(origWindow, \'load\', fireContentLoadedEvent);');
			}

			if (details.url.match(/container\.js/))
			{
			    replacedStr = replacedStr.replace(/u0bb.R0=(?:.*)\n/g, 'u0bb.R0=function() {}; WaynePop3 = function() {}; WaynePop3.Logger=function(){}; WaynePop3.Logger.log=function() { console.log.apply(console.log, arguments); };');
			}

            if (details.url.match(/jquery\.js/))
			{
                replacedStr = replacedStr.replace('a.addEventListener(', "origWindow.addEventListener(");
                replacedStr = replacedStr.replace('a.getComputedStyle', "origWindow.getComputedStyle");
			}
			replacedStr = replacedStr.replace('window.addEventListener(', 'origWindow.addEventListener(');
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
		chunkData.push(event.data);
	};

	filter.onstop = event => {
		let str = decodeChunks(chunkData, decoder);

		// Just change any instance of Example in the HTTP response
		// to WebExtension Example.
		if (details.url.match(/\.js(?:\?(?:.*))?$/) && ! (details.url.match(/jquery\.js/)))
		{
		    str = str.replace('\\x61\\x64\\x64\\x45\\x76\\x65\\x6e\\x74\\x4c\\x69\\x73\\x74\\x65\\x6e\\x65\\x72', 'addMockedEventListener');
		    str = str.replace('\\x72\\x65\\x6d\\x6f\\x76\\x65\\x45\\x76\\x65\\x6e\\x74\\x4c\\x69\\x73\\x74\\x65\\x6e\\x65\\x72', 'removeMockedEventListener');
			replacedStr = wrapWindow(str);

			filter.write(encoder.encode(replacedStr));
		}
		else if (details.url.match(/\.html(?:\?(?:.*))?$/))
		{
		    str = str.replace('window.addEventListener(', 'origWindow.addEventListener(');
		    str = str.replace('\\x61\\x64\\x64\\x45\\x76\\x65\\x6e\\x74\\x4c\\x69\\x73\\x74\\x65\\x6e\\x65\\x72', 'addMockedEventListener')
		    str = str.replace('\\x72\\x65\\x6d\\x6f\\x76\\x65\\x45\\x76\\x65\\x6e\\x74\\x4c\\x69\\x73\\x74\\x65\\x6e\\x65\\x72', 'removeMockedEventListener');
		    var re = /(?:<script>([\s\S]*?)<\/script>)/g, lastEnd=0, script, after;
            replacedStr = '';
            while ((match = re.exec(str)) != null)
            {
                script = match[1];
                after = '';
                if (script.match(/var MetrikaLog = function MetrikaLog/))
                {
                    after = 'origWindow[\'MetrikaLog\'] = MetrikaLog';
                }
                replacedStr += str.substring(lastEnd, match.index)+'<script>'+wrapWindow(match[1], after)+'</script>';
                lastEnd=match.index+match[0].length;
            }
            replacedStr+=str.substring(lastEnd);
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
	{urls: ["*://filecrypt.cc/*", "*://filecrypt.co/*", "*://www.filecrypt.cc/*",  "*://www.filecrypt.co/*"], types: ["main_frame", "script", "sub_frame"]},
	["blocking"]
);

browser.webRequest.onBeforeRequest.addListener(
	cutcaptchaListener,
	{urls: ["*://cutcaptcha.com/*"], types: ["main_frame", "script", "sub_frame"]},
	["blocking"]
);