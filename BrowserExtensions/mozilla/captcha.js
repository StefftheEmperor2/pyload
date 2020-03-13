// ==UserScript==
// @name		 pyLoad Script for Interactive Captcha
// @namespace	https://pyload.net/
// @version	  0.19
// @author	   Michi-F, GammaC0de
// @description  pyLoad Script for Interactive Captcha
// @homepage	 https://github.com/pyload/pyload
// @icon		 https://raw.githubusercontent.com/pyload/pyload/stable/module/web/media/img/favicon.ico
// @updateURL	https://raw.githubusercontent.com/pyload/pyload/stable/module/web/media/js/captcha-interactive.user.js
// @downloadURL  https://raw.githubusercontent.com/pyload/pyload/stable/module/web/media/js/captcha-interactive.user.js
// @supportURL   https://github.com/pyload/pyload/issues
// @grant		none
// @run-at	   document-start
// @require	  https://kjur.github.io/jsrsasign/jsrsasign-all-min.js
//
// @match		*://*/*
//
// ==/UserScript==

/*
	Copyright (C) 2018, Michi-F

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU Affero General Public License as
	published by the Free Software Foundation, either version 3 of the
	License, or (at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU Affero General Public License for more details.

	You should have received a copy of the GNU Affero General Public License
	along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

(function(localWindow) {
	localWindow.foo="bar";
	let methods = {
		"recaptcha": function(request, gpyload)
		{
			while(document.children[0].childElementCount > 0)
			{
				document.children[0].removeChild(document.children[0].children[0]);
			}
			document.children[0].innerHTML = '<html><head></head><body style="display:inline-block;"><div id="captchadiv" style="display: inline-block;"></div></body></html>';

			gpyload.data.sitekey = request.params.sitekey;

			gpyload.getFrameSize = function()
			{
				var rectAnchor =  {top: 0, right: 0, bottom: 0, left: 0},
					rectPopup =  {top: 0, right: 0, bottom: 0, left: 0},
					rect;
				var anchor = document.body.querySelector("iframe[src*='/anchor']");
				if (anchor !== null && gpyload.isVisible(anchor)) {
					rect = anchor.getBoundingClientRect();
					rectAnchor = {top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left};
				}
				var popup = document.body.querySelector("iframe[src*='/bframe']");
				if (popup !== null && gpyload.isVisible(popup)) {
					rect = popup.getBoundingClientRect();
					rectPopup = {top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left};
				}
				var left = Math.round(Math.min(rectAnchor.left, rectAnchor.right, rectPopup.left, rectPopup.right));
				var right = Math.round(Math.max(rectAnchor.left, rectAnchor.right, rectPopup.left, rectPopup.right));
				var top = Math.round(Math.min(rectAnchor.top, rectAnchor.bottom, rectPopup.top, rectPopup.bottom));
				var bottom = Math.round(Math.max(rectAnchor.top, rectAnchor.bottom, rectPopup.top, rectPopup.bottom));
				return {top: top, left: left, bottom: bottom, right: right};
			};

			// function that is called when the captcha finished loading and is ready to interact
			let callbackString = `window.pyloadCaptchaOnLoadCallback = function()
			{
				console.log('captcha loaded');
				grecaptcha.render(
					"captchadiv",
					{size: "compact",
					 'sitekey': gpyload.data.sitekey,
					 'callback': function() {
						var recaptchaResponse = grecaptcha.getResponse(); // get captcha response
						gpyload.submitResponse(recaptchaResponse);
					 }}
				);
				debugger;
				gpyload.activated();
			};`;

			console.log('registered', 'pyloadCaptchaOnLoadCallback');
			let onDocumentLoaded = function(event)
			{
				if(typeof grecaptcha !== 'undefined' && grecaptcha) {
					window.pyloadCaptchaOnLoadCallback();
				} else {
					debugger;

					var js_script = document.createElement('script');
					js_script.type = "text/javascript";
					js_script.textContent = callbackString;
					document.getElementsByTagName('head')[0].appendChild(js_script);
					js_script.remove();

					var js_script = document.createElement('script');
					js_script.type = "text/javascript";
					js_script.src = "//www.google.com/recaptcha/api.js?onload=pyloadCaptchaOnLoadCallback&render=explicit";
					js_script.async = true;
					document.getElementsByTagName('head')[0].appendChild(js_script);
				}
			};

			if (document.readyState === 'loading')
			{
				console.log('deferring recaptcha loading');
				document.addEventListener('DOMContentLoaded', (event) => {
					onDocumentLoaded(event);
				});
			}
			else
			{
				onDocumentLoaded();
			}

		}
	};
	// this function listens to messages from the pyload main page
	console.log('added message handler for pyload interactive captcha');
	window.addEventListener('message', function(e) {
		try {
			var request = JSON.parse(e.data);
		} catch(e) {
			return
		}

		if(request.constructor === {}.constructor && request.actionCode === "pyloadActivateInteractive")
		{
			console.log('pyloadActivateInteractive');
			if (request.params.cmd == 'pyloadCaptchaInteractive') {
				if (typeof request.params.cookie_jar != 'undefined')
				{
					for (let key in request.params.cookie_jar)
					{
						var cookie_obj = request.params.cookie_jar[key],
							cookie_str = cookie_obj.name+'='+cookie_obj.value
						if (cookie_obj.expire !== null)
						{
							cookie_str += ';expires='+cookie_obj.expire
						}
						if (cookie_obj.path !== null)
						{
							cookie_str += ';path='+cookie_obj.expire
						}
						// document.cookie = cookie_str;
					}
				}

				let cgpyload = function(paramData)
				{
					let gpyload = this;
					let cookieJar = null;
					let frameSize = null;

					this.isVisible = function(element) {
						var style = window.getComputedStyle(element);
						return !(style.width === 0 ||
							style.height === 0 ||
							style.opacity === 0 ||
							style.display ==='none' ||
							style.visibility === 'hidden'
						);
					};

					this.debounce = function (fn, delay) {
						var timer = null;
						return function () {
							var context = this, args = arguments;
							clearTimeout(timer);
							timer = setTimeout(function () {
								fn.apply(context, args);
							}, delay);
						};
					};

					this.submitResponse = function(response) {
						if (typeof gpyload.observer !== 'undefined') {
							gpyload.observer.disconnect();
						}
						var response_cookies = cookie_jar,
							cookie_lines = document.cookie.split(';'),
							cookie_kv, cookie_key, cookie_value;

						for (let i in cookie_lines)
						{
							cookie_kv = cookie_lines[i].split('=')
							cookie_key = cookie_kv[0].trim();
							cookie_value = cookie_kv[1].trim();
							if (typeof response_cookies[cookie_key] != 'undefined')
							{
								response_cookies[cookie_key].value = cookie_value;
							}
							else
							{
								response_cookies[cookie_key] = {"name": cookie_key, "value": cookie_value, "domain": request.params.domain};
							}
						}
						var responseMessage = {actionCode: "pyloadSubmitResponse", params: {"cookie": response_cookies, "response": response, "domain": window.location.hostname}};
						parent.postMessage(JSON.stringify(responseMessage),"*");
					};

					this.activated = function() {
						var responseMessage = {actionCode: "pyloadActivatedInteractive"};
						parent.postMessage(JSON.stringify(responseMessage),"*");
					};

					this.setSize = function(rect) {
						debugger;
						if (gpyload.data.rectDoc.left !== rect.left || gpyload.data.rectDoc.right !== rect.right || gpyload.data.rectDoc.top !== rect.top || gpyload.data.rectDoc.bottom !== rect.bottom) {
							gpyload.data.rectDoc = rect;
							var responseMessage = {actionCode: "pyloadIframeSize", params: {rect: rect}};
							parent.postMessage(JSON.stringify(responseMessage), "*");
						}
					};

					this.setFrameSize = function(paramFrameSize)
					{
						frameSize = paramFrameSize;
					};

					this.getFrameSize = function()
					{
						return frameSize;
					};

					this.setCookieJar = function(paramCookieJar)
					{
						cookieJar = paramCookieJar;
					};

					this.getCookieJar = function()
					{
						return cookieJar
					}

					this.data = paramData;
				};

				let gpyload = new cgpyload(
					{
						debounceInterval: 1500,
						rectDoc: {top: 0, right: 0, bottom: 0, left: 0}
					});

				window['test'] = 'bla';

				if (typeof request.params.method != 'undefined')
				{
					methods[request.params.method].call(window, request, gpyload);
				}
				else
				{
					try {
						eval(request.params.script.code);
					} catch(err) {
						console.error("pyLoad: Script aborted: " + err.name + ": " + err.message + " (" + err.stack +")");
					return;
					}
				}


				if (typeof gpyload.getFrameSize === "function")
				{
					var checkDocSize = gpyload.debounce(function()
					{
						window.scrollTo(0,0);
						var rect = gpyload.getFrameSize();
						gpyload.setSize(rect);
					}, gpyload.data.debounceInterval);
					gpyload.observer = new MutationObserver(function(mutationsList) {
						checkDocSize();
					});

					/*
					var js_script = document.createElement("script");
					js_script.type = "text/javascript";
					js_script.innerHTML = "gpyload.observer.observe(document.querySelector('body'), {attributes:true, attributeOldValue:false, characterData:true, characterDataOldValue:false, childList:true, subtree:true});";
					document.getElementsByTagName('body')[0].appendChild(js_script);
					*/
				}

			}
		}
	});
})(this);