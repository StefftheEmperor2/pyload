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
	let methods = {
		"recaptcha": function(request, pyload)
		{
			while(document.children[0].childElementCount > 0)
			{
				document.children[0].removeChild(document.children[0].children[0]);
			}
			document.children[0].innerHTML = '<html><head></head><body style="display:inline-block;"><div id="captchadiv" style="display: inline-block;"></div></body></html>';
            pyload.load_js(browser.runtime.getURL('page-scripts/mutationObserver.js'));
			pyload.data.sitekey = request.params.sitekey;

			pyload.getFrameSize = function()
			{
				var rectAnchor =  {top: 0, right: 0, bottom: 0, left: 0},
					rectPopup =  {top: 0, right: 0, bottom: 0, left: 0},
					rect;
				var anchor = document.body.querySelector("iframe[src*='/anchor']");
				if (anchor !== null && pyload.isVisible(anchor)) {
					rect = anchor.getBoundingClientRect();
					rectAnchor = {top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left};
				}
				var popup = document.body.querySelector("iframe[src*='/bframe']");
				if (popup !== null && pyload.isVisible(popup)) {
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

			console.log('registered', 'pyloadCaptchaOnLoadCallback');
			let onDocumentLoaded = function(event)
			{
				if(typeof grecaptcha !== 'undefined' && grecaptcha) {
					window.pyloadCaptchaOnLoadCallback();
				} else {
					var page_script = document.createElement('script');
					page_script.type = "text/javascript";
					page_script.onload = function()
					{
					    window.addEventListener('pyload.siteKeySet', function(event) {
					        var js_script = document.createElement('script');
                            js_script.type = "text/javascript";
                            js_script.src = "//www.google.com/recaptcha/api.js?onload=pyloadCaptchaOnLoadCallback&render=explicit";
                            js_script.async = true;
                            document.getElementsByTagName('head')[0].appendChild(js_script);
					    });
					    let event = new CustomEvent('pyload.setSiteKey', {"detail": pyload.data.sitekey});
					    window.dispatchEvent(event);

					};
					page_script.src = browser.runtime.getURL('page-scripts/recaptcha/pyloadCaptchaOnLoadCallback.js');
					document.getElementsByTagName('head')[0].appendChild(page_script);
					page_script.remove();

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

		},
		"cutcaptcha": function(request, pyload)
		{
            pyload.data.sitekey = request.params.sitekey;

            window.dispatchEvent(new Event("beforeunload", {
              bubbles: true,
              cancelable: true
            }));

            window.dispatchEvent(new Event("unload", {
              bubbles: true,
              cancelable: true
            }));

            pyload.load_js(browser.runtime.getURL('page-scripts/deleteEventListeners.js'), function() {
                pyload.load_js(browser.runtime.getURL('page-scripts/cleanupHtml.js'), function() {
                pyload.eval_js('window.document.body.innerHTML = \'<div id="puzzle-captcha" aria-style="mobile"></div>\';');
                    window.addEventListener('pyload.mutationObserverRegistered', function() {

                        pyload.eval_js(`var CUTCAPTCHA_MISERY_KEY = "`+pyload.data.sitekey+`";
                            window.capResponseCallback = function(token) {
                                let event = new CustomEvent("pyload.submitResponse", { "detail": token });
                                window.dispatchEvent(event);
                            };`);

                        document.addEventListener('DOMContentLoaded', function()
                        {
                            pyload.activated();
                        });

                        pyload.load_js(request.params.script_src, function() {

                        window.addEventListener('load', function() {
                            window.document.dispatchEvent(new Event("DOMContentLoaded", {
                              bubbles: true,
                              cancelable: true
                            }));
                        });


                            window.dispatchEvent(new Event("load", {
                              bubbles: true,
                              cancelable: true
                            }));
                        });

                    });

                    pyload.load_js(browser.runtime.getURL('page-scripts/mutationObserver.js'), function () {
                        window.dispatchEvent(new CustomEvent("pyload.mutationObserverRegistered"));
                    });

                    pyload.getFrameSize = function()
                    {
                        let rectIFrame =  {top: 0, right: 0, bottom: 0, left: 0},
                            rectPopup =  {top: 0, right: 0, bottom: 0, left: 0},
                            rect,
                            iframe = document.body.querySelector("#puzzle-captcha iframe");

                        if (iframe !== null && pyload.isVisible(iframe))
                        {
                            rect = iframe.getBoundingClientRect();
                            rectIFrame = {top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left};
                        }

                        var left = Math.floor(rectIFrame.left);
                        var right = Math.ceil(rectIFrame.right);
                        var top = Math.floor(rectIFrame.top);
                        var bottom = Math.max(Math.ceil(rectIFrame.bottom));
                        return {top: top, left: left, bottom: bottom, right: right};
                    };
                });
            });

        }
	};

	var page_script = document.createElement('script');
    page_script.type = "text/javascript";
    page_script.src = browser.runtime.getURL('page-scripts/replaceEventHandler.js');
    document.getElementsByTagName('head')[0].appendChild(page_script);
    page_script.remove();

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
							cookie_str += ';path='+cookie_obj.path
						}
						// document.cookie = cookie_str;
					}
				}

				let cPyload = function(paramData)
				{
					let pyload = this;
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

					this.submitResponse = function(response) {
						if (typeof pyload.observer !== 'undefined') {
							pyload.observer.disconnect();
						}

						console.log("Submitting response");
						var responseMessage = {actionCode: "pyloadSubmitResponse", params: {"response": response, "domain": window.location.hostname}};
						parent.postMessage(JSON.stringify(responseMessage),"*");
					};

					this.activated = function()
					{
					    console.log('captcha activated');
						let responseMessage = {actionCode: "pyloadActivatedInteractive"};
						parent.postMessage(JSON.stringify(responseMessage),"*");
                        pyload.checkDocSize();
					};

					this.setSize = function(rect)
					{
						if (pyload.data.rectDoc.left !== rect.left || pyload.data.rectDoc.right !== rect.right || pyload.data.rectDoc.top !== rect.top || pyload.data.rectDoc.bottom !== rect.bottom) {
							pyload.data.rectDoc = rect;
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
					};

					this.load_js = function(src, callback)
					{
                        var page_script = document.createElement('script');
                        page_script.type = "text/javascript";
                        if (typeof callback !== 'undefined')
                        {
                            page_script.onload = callback;
                        }
                        page_script.src = src;
                        window.document.getElementsByTagName('head')[0].appendChild(page_script);
                        page_script.remove();
					}

					this.eval_js = function(code)
					{
                        var page_script = document.createElement('script');
                        page_script.type = "text/javascript";
                        page_script.text = code;
                        document.getElementsByTagName('head')[0].appendChild(page_script);
                        page_script.remove();
					}

                    this.checkDocSize = function()
                    {
                        window.scrollTo(0,0);
                        var rect = pyload.getFrameSize();
                        if (rect !== null)
                        {
                            pyload.setSize(rect);
                        }
                    };

                    window.addEventListener('pyload.activated', function() {
                        pyload.activated();
                    });

                    window.addEventListener('pyload.submitResponse', function(event) {
                        pyload.submitResponse(event.detail);
                    });

                    window.addEventListener('pyload.mutationObserved', function() {
                        pyload.checkDocSize();
                    });

                    window.addEventListener('message', function(e) {
                            try {
                                var request = JSON.parse(e.data);
                            } catch(e) {
                                return
                            }

                            if (typeof request.cmd != 'undefined' && request.cmd == 'pyloadCheckDocSize')
                            {
                                pyload.checkDocSize();
                            }
                    });
					this.data = paramData;
				};

				let pyload = new cPyload(
                {
                    rectDoc: {top: 0, right: 0, bottom: 0, left: 0}
                });

				if (typeof request.params.method != 'undefined')
				{
					methods[request.params.method].call(window, request, pyload);
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

                if (window.document.readyState == 'complete')
                {
                    pyload.checkDocSize();
                }
                else
                {
                    window.document.addEventListener('DOMContentLoaded', function() {
                        pyload.checkDocSize();
                    });
                }

			}
		}
	});
})(this);