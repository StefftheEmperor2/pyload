# -*- coding: utf-8 -*-

import pycurl
from pyload.core.network.browser import Browser
from pyload.core.network.http.http_request import HTTPRequest

from ..base.addon import BaseAddon


class UserAgentSwitcher(BaseAddon):
    __name__ = "UserAgentSwitcher"
    __type__ = "addon"
    __version__ = "0.16"
    __status__ = "testing"

    __pyload_version__ = "0.5"

    __config__ = [
        ("enabled", "bool", "Activated", True),
        ("connecttimeout", "int", "Max timeout for link connection in seconds", 60),
        ("maxredirs", "int", "Maximum number of redirects to follow", 10),
        (
            "useragent",
            "str",
            "Custom user-agent string",
            "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0",
        ),
    ]

    __description__ = """Custom user-agent"""
    __license__ = "GPLv3"
    __authors__ = [("Walter Purcaro", "vuolter@gmail.com")]
