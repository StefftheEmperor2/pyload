import re

import pycurl
from pyload.core.utils.misc import eval_js

from ..anticaptchas.ReCaptcha import ReCaptcha
from ..base.simple_downloader import SimpleDownloader

class Test(SimpleDownloader):
    __name__ = "Test"
    __type__ = "downloader"
    __version__ = "0.1"
    __status__ = "testing"

    __pyload_version__ = "0.5"

    __pattern__ = r"http(?:s)?://(?:recaptcha.lw-rulez.de/)"
    __config__ = [
        ("enabled", "bool", "Activated", True),
        ("use_premium", "bool", "Use premium account if available", True),
        ("fallback", "bool", "Fallback to free download if premium fails", True),
        ("chk_filesize", "bool", "Check file size", True),
        ("max_wait", "int", "Reconnect if waiting time is greater than minutes", 10),
    ]
    __description__ = """Test downloader plugin"""
    __license__ = "GPLv3"
    __authors__ = [
        ("StefftheEmperor", "StefftheEmperor@lw-rulez.de")
    ]
    __free_url = 'http://recaptcha.lw-rulez.de'

    def handle_free(self, pyfile):
        self.data = self.load(self.__free_url)

        self.solve_captcha()
        m = re.search(r"\"success\": true", self.data)
        if m is None:
            self.fail(self._("captcha not successful"))

    def solve_captcha(self):
        action, inputs = self.parse_html_form("action=\"#\"")

        self.captcha = ReCaptcha(self.pyfile)
        self.captcha.fallback_disabled = True
        captcha_result = self.captcha.challenge()
        cookie_jar = captcha_result['cookie_jar']
        if len(inputs) == 0:
            inputs = {"g-recaptcha-response": captcha_result['result']}

        cookie_jar.set_dot_domain()
        self.data = self.load(self.__free_url, post=inputs, cookies=cookie_jar)
