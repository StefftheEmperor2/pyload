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
%%%INTERACTIVE_SCRIPTS%%%
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

				if (typeof request.params.captcha_plugin != 'undefined' && typeof methods[request.params.captcha_plugin] != 'undefined')
				{
					methods[request.params.captcha_plugin].call(window, request, pyload);
				}
				else
				{
					console.error("pyLoad: Script not found: " + request.params.captcha_plugin);
					return;
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