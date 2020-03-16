#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import urllib.parse
from ..base.captcha_service import CaptchaService


class CutCaptcha(CaptchaService):
    __name__ = "CutCaptcha"
    __type__ = "anticaptcha"
    __version__ = "0.01"
    __status__ = "testing"

    __pyload_version__ = "0.5"

    __description__ = "CutCaptcha captcha service plugin"
    __license__ = "GPLv3"
    __authors__ = [
        ("StefftheEmperor", "stefftheemperor[AT]lw-rulez[DOT]de"),
    ]

    KEY_PATTERN = r'var CUTCAPTCHA_MISERY_KEY = "([a-z0-9]*)";'
    SCRIPT_SRC_PATTERN = r'<script src="([0-9a-zA-Z\/\._:]*)"></script>\s*<div id="puzzle-captcha"'
    CUTCAPTCHA_INTERACTIVE_SIG = (
            "7b99386315b3e035285946b842049575fc69a88ccc219e1bc96a9afd0f3c4b7456f09d36bf3dc530"
            + "a08cd50f1b3128716cf727b30f7de4ab1513f15bb82776e84404089a764c6305d9c6033c99f8514e"
            + "249bc3fd5530b475c00059797ce5a45d131adb626a440366af9acc9a50a3a7327b9d3dc28b59f83f"
            + "32129feb89e0cfb74521c306e8ac0b9fff9df31d453eedc54a17d41528c2d866363fc13cb524ad77"
            + "60483b28bf4a347de4a8b2b1480f83f66c4408ad9dbfec78f6f1525b8507b6e52cdd13e13f8e3bfc"
            + "0bb5dd1860e6fc5db99ef0c915fd626c3aaec0bb5ead3a668ebb31dd2a08eacaefffdf51e3a0ba31"
            + "cb636da134c24633f2b2b38f56dfbb92"
    )

    CUTCAPTCHA_INTERACTIVE_JS = """
            while(document.children[0].childElementCount > 0) {
                document.children[0].removeChild(document.children[0].children[0]);
            }
            if (window.lastListenerInfo)
            {
                (function ()
                {
                    var i, event;
                    for (i=0;i<window.lastListenerInfo.length;i++)
                    {
                        event = window.lastListenerInfo[i];
                        if (event['a'] == 'load')
                        {
                            window.removeEventListener('load', event['b']);
                        }
                    }
                })();
                
            }
            document.children[0].innerHTML = '<html><head></head><body style="display:inline-block;">'
                + '<div id="puzzle-captcha" aria-style="mobile"></div></body></html>';
                
            gpyload.data.sitekey = request.params.sitekey;
         
            gpyload.getFrameSize = function() {
                var rectIFrame =  {top: 0, right: 0, bottom: 0, left: 0},
                    rectPopup =  {top: 0, right: 0, bottom: 0, left: 0},
                    rect;
                var iframe = document.body.querySelector("#puzzle-captcha iframe");
                if (iframe !== null && gpyload.isVisible(iframe)) 
                {
                    rect = iframe.getBoundingClientRect();
                    rectIFrame = {top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left};
                }
                
                var left = Math.floor(rectIFrame.left);
                var right = Math.ceil(rectIFrame.right);
                var top = Math.floor(rectIFrame.top);
                var bottom = Math.ceil(rectIFrame.bottom);
                return {top: top, left: left, bottom: bottom, right: right};
            };

            // function that is called when the captcha finished loading and is ready to interact
            window.pyloadCaptchaOnLoadCallback = function() 
            {
                window.CUTCAPTCHA_MISERY_KEY = gpyload.data.sitekey;
                window.capResponseCallback = function(token) { gpyload.submitResponse(token) };
                debugger;
                fetch(request.params.script_src, {
                    method: 'POST',
                    mode: 'cors',
                    redirect: 'follow',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                }).then((data) => {
                    var DOMContentLoaded_event = document.createEvent("Event")
                    DOMContentLoaded_event.initEvent("DOMContentLoaded", true, true)
                    window.document.dispatchEvent(DOMContentLoaded_event)
                    gpyload.activated();
                });
                
            };

            
            window.pyloadCaptchaOnLoadCallback();
            """

    def __init__(self, pyfile):
        super().__init__(pyfile)
        self.key = None
        self.script_src = None

    def detect_key(self, data=None):
        html = data or self.retrieve_data()

        m = re.search(self.KEY_PATTERN, html)
        if m is not None:
            self.key = urllib.parse.unquote(m.group(1).strip())
            self.log_debug(f"Key: {self.key}")
            return self.key
        else:
            self.log_warning(self._("Key pattern not found"))
            return None

    def get_script_src(self, data=None):
        if self.script_src is not None:
            return self.script_src

        html = data or self.retrieve_data()
        m = re.search(self.SCRIPT_SRC_PATTERN, html)
        if m is not None:
            self.script_src = urllib.parse.unquote(m.group(1).strip())
            self.log_debug(f"Script Source: {self.script_src}")
            return self.script_src
        else:
            self.log_warning(self._("Script Source pattern not found"))
            return None

    def challenge(self, key=None, data=None, version=None, secure_token=None):
        key = key or self.retrieve_key(data)
        script_src = self.get_script_src(data)
        user_agent = None;
        if self.pyfile.plugin.req.user_agent is not None:
            user_agent = self.pyfile.plugin.req.user_agent.decode('utf-8')
        params = {
            "url": self.pyfile.url,
            "sitekey": key,
            "method": 'cutcaptcha',
            "cookie_jar": self.pyfile.plugin.req.cookie_jar,
            "user_agent": user_agent,
            "script_src": script_src,
            "cmd": 'pyloadCaptchaInteractive'
        }

        result = self.decrypt_interactive(params, timeout=300)

        return result

    def result(self, server, challenge):
        pass

    def recognize(self, image):
        pass


if __name__ == "__main__":
    # Sign with the command `python -m pyload.plugins.captcha.ReCaptcha
    # pyload.private.pem pem_passphrase`
    import sys
    from ..helpers import sign_string

    if len(sys.argv) > 2:
        with open(sys.argv[1]) as fp:
            pem_private = fp.read()

        print(
            sign_string(
                CutCaptcha.CUTCAPTCHA_INTERACTIVE_JS,
                pem_private,
                pem_passphrase=sys.argv[2],
                sign_algo="SHA384",
            )
        )
