# -*- coding: utf-8 -*-

import re

import pycurl
from pyload.core.utils.misc import eval_js

from ..anticaptchas.ReCaptcha import ReCaptcha
from ..base.simple_downloader import SimpleDownloader


class TurbobitNet(SimpleDownloader):
    __name__ = "TurbobitNet"
    __type__ = "downloader"
    __version__ = "0.33"
    __status__ = "testing"

    __pyload_version__ = "0.5"

    __pattern__ = r"http(?:s)?://(?:www\.)?(?:turbobit\.net|turbo.to)/(?:download/free/)?(?P<ID>\w+)"
    __config__ = [
        ("enabled", "bool", "Activated", True),
        ("use_premium", "bool", "Use premium account if available", True),
        ("fallback", "bool", "Fallback to free download if premium fails", True),
        ("chk_filesize", "bool", "Check file size", True),
        ("max_wait", "int", "Reconnect if waiting time is greater than minutes", 10),
    ]

    __description__ = """Turbobit.net downloader plugin"""
    __license__ = "GPLv3"
    __authors__ = [
        ("zoidberg", "zoidberg@mujmail.cz"),
        ("prOq", None),
        ("GammaC0de", "nitzo2001[AT]yahoo[DOT]com"),
    ]

    URL_REPLACEMENTS = [(__pattern__ + ".*", r"https://turbobit.net/\g<ID>.html")]

    COOKIES = []

    INFO_PATTERN = (
        r"<title>\s*Download file (?P<N>.+?) \((?P<S>[\d.,]+) (?P<U>[\w^_]+)\)"
    )
    OFFLINE_PATTERN = r"<h2>File Not Found</h2>|html\(\'File (?:was )?not found"
    TEMP_OFFLINE_PATTERN = r""

    LINK_FREE_PATTERN = r'(/download/redirect/[^"\']+)'
    LINK_PREMIUM_PATTERN = r'<a href=[\'"](.+?/download/redirect/[^"\']+)'

    LIMIT_WAIT_PATTERN = r"<div id=\'timeout\'>(\d+)<"

    @property
    def free_url(self):
        return "https://turbobit.net/download/free/{}".format(
            self.info["pattern"]["ID"]
        )

    def handle_free(self, pyfile):
        self.data = self.load(self.free_url, cookies=self.cookie_jar)
        self.referer = self.free_url
        m = re.search(self.LIMIT_WAIT_PATTERN, self.data)
        if m is not None:
            self.retry(wait=int(m.group(1)))

        self.solve_captcha()

        err = re.search(r"Incorrect, try again!", self.data)
        if err is not None:
            self.retry_captcha(msg=_('captcha incorrect'))
        else:
            m = re.search(r"minLimit : (.+?),", self.data)
            if m is None:
                limit_match = re.search(self.LIMIT_WAIT_PATTERN, self.data)
                if limit_match is not None:
                    self.retry(wait=int(limit_match.group(1)))
                self.fail(self._("minLimit pattern not found"))

            wait_time = self.pyload.eval_js(m.group(1))
            self.wait(wait_time)

            self.data = self.load(
                "https://turbobit.net/download/getLinkTimeout/{}".format(
                    self.info["pattern"]["ID"]
                ),
                referer=self.free_url,
                cookies=self.cookie_jar,
                headers=[{'X-Requested-With': 'XMLHttpRequest'}]
            )

            if "/download/started/" in self.data:
                self.data = self.load(
                    "https://turbobit.net/download/started/{}".format(
                        self.info["pattern"]["ID"]
                    ),
                    cookies=self.cookie_jar
                )

                m = re.search(self.LINK_FREE_PATTERN, self.data)
                if m is not None:
                    self.referer = self.free_url
                    self.link = "https://turbobit.net{}".format(m.group(1))

    def solve_captcha(self):
        action, inputs = self.parse_html_form("action='#'")
        if not inputs:
            self.fail(self._("Captcha form not found"))

        cookie_jar = None
        if inputs["captcha_type"] == "recaptcha2":
            self.captcha = ReCaptcha(self.pyfile)
            self.captcha.fallback_disabled = True
            captcha_result = self.captcha.challenge()
            inputs["g-recaptcha-response"] = captcha_result['result']
            cookie_jar = captcha_result['cookie_jar']
        else:
            self.fail(self._("Unknown captcha type"))

        self.data = self.load(self.free_url, post=inputs, cookies=self.cookie_jar)

    def handle_premium(self, pyfile):
        m = re.search(self.LINK_PREMIUM_PATTERN, self.data)
        if m is not None:
            self.link = m.group(1)