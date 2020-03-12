// ==UserScript==
// @name         pyLoad Script for Interactive Captcha
// @namespace    https://pyload.net/
// @version      0.19
// @author       Michi-F, GammaC0de
// @description  pyLoad Script for Interactive Captcha
// @homepage     https://github.com/pyload/pyload
// @icon         https://raw.githubusercontent.com/pyload/pyload/stable/module/web/media/img/favicon.ico
// @updateURL    https://raw.githubusercontent.com/pyload/pyload/stable/module/web/media/js/captcha-interactive.user.js
// @downloadURL  https://raw.githubusercontent.com/pyload/pyload/stable/module/web/media/js/captcha-interactive.user.js
// @supportURL   https://github.com/pyload/pyload/issues
// @grant        none
// @run-at       document-start
// @require      https://kjur.github.io/jsrsasign/jsrsasign-all-min.js
//
// @match        *://*/*
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

(function() {
    if (window.location.host == 'filecrypt.cc')
    {
        EventTarget.prototype.realAddEventListener = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function(a,b,c)
        {
            this.realAddEventListener(a,b,c);

            if(!this.lastListenerInfo){this.lastListenerInfo = new Array()};
            this.lastListenerInfo.push({a : a, b : b , c : c});
        };
    }
    // this function listens to messages from the pyload main page
    window.addEventListener('message', function(e) {
        try {
            var request = JSON.parse(e.data);
        } catch(e) {
            return
        }
        if(request.constructor === {}.constructor && request.actionCode === "pyloadActivateInteractive")
        {
            if (request.params.script) {
                var sig = new KJUR.crypto.Signature({"alg": "SHA384withRSA", "prov": 'cryptojs/jsrsa'});
                sig.init("-----BEGIN PUBLIC KEY-----\n" +
                    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuEHE4uAeTeEQjIwB//YH\n" +
                    "Gl5e058aJRCRyOvApv1iC1ZQgXGHopgEd528+AtkAZKdCRkoNCWda7L/hROpZNjq\n" +
                    "xgO5NjjlBnotntQiZ6xr7A4Kfdctmw1DPcv/dkp6SXRpAAw8BE9CctZ3H7cE/4UT\n" +
                    "FIJOYQQXF2dcBTWLnUAjesNoHBz0uHTdvBIwJdfdUIrNMI4IYXL4mq9bpKNvrwrb\n" +
                    "iNhSqN0yV8sanofZmDX4JUmVGpWIkpX0u+LA4bJlaylwPxjuWyIn5OBED0cdqpbO\n" +
                    "7t7Qtl5Yu639DF1eZDR054d9OB3iKZX1a6DTg4C5DWMIcU9TsLDm/JJKGLWRxcJJ\n" +
                    "fwIDAQAB\n" +
                    "-----END PUBLIC KEY----- ");
                sig.updateString(request.params.script.code);

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

                    window.cgpyload = function(param_data)
                    {

                        var cookie_jar = request.params.cookie_jar;

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
                            if (gpyload.data.rectDoc.left !== rect.left || gpyload.data.rectDoc.right !== rect.right || gpyload.data.rectDoc.top !== rect.top || gpyload.data.rectDoc.bottom !== rect.bottom) {
                                gpyload.data.rectDoc = rect;
                                var responseMessage = {actionCode: "pyloadIframeSize", params: {rect: rect}};
                                parent.postMessage(JSON.stringify(responseMessage), "*");
                            }
                        };

                        this.data = param_data;
                    };

                    window.gpyload = new cgpyload(
                        {
                            debounceInterval: 1500,
                            rectDoc: {top: 0, right: 0, bottom: 0, left: 0}
                        });
                    try {
                        debugger;
                        eval(request.params.script.code);
                    } catch(err) {
                        console.error("pyLoad: Script aborted: " + err.name + ": " + err.message + " (" + err.stack +")");
                        return;
                    }
                    if (typeof gpyload.getFrameSize === "function") {
                        var checkDocSize = gpyload.debounce(function() {
                            window.scrollTo(0,0);
                            var rect = gpyload.getFrameSize();
                            gpyload.setSize(rect);
                        }, gpyload.data.debounceInterval);
                        gpyload.observer = new MutationObserver(function(mutationsList) {
                            checkDocSize();
                        });
                        var js_script = document.createElement("script");
                        js_script.type = "text/javascript";
                        js_script.innerHTML = "gpyload.observer.observe(document.querySelector('body'), {attributes:true, attributeOldValue:false, characterData:true, characterDataOldValue:false, childList:true, subtree:true});";
                        document.getElementsByTagName('body')[0].appendChild(js_script);
                    }

            }
        }
    });
})();