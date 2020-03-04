# -*- coding: utf-8 -*-

from logging import getLogger

from pyload import APPID

from .http.http_download import HTTPDownload
from .http.http_request import HTTPRequest, BigHTTPRequest
from .cookie_jar import CookieJar

class Browser:
    def __init__(self, bucket=None):
        self.log = getLogger(APPID)

        self.bucket = bucket

        self._cookie_jar = None  #: needs to be setted later
        self._size = 0

        self.dl = None
        self._user_agent = None
        self._last_url = None
        self._is_big = False
        self._limit = None

    def set_is_big(self):
        self._is_big = True

    def set_is_small(self):
        self._is_big = False

    def set_limit(self, limit):
        self._limit = limit

    @property
    def http(self):

        if self._is_big:
            req = BigHTTPRequest(cookies=self.cookie_jar, limit=self._limit)
        else:
            req = HTTPRequest(cookies=self.cookie_jar)

        req.user_agent = self.user_agent

        return req

    def get_request(self):
        return self.http

    @property
    def user_agent(self):
        return self._user_agent

    @user_agent.setter
    def user_agent(self, user_agent):
        self._user_agent = user_agent

    def set_user_agent(self, user_agent):
        self.user_agent = user_agent

    def set_last_url(self, val):
        self._last_url = val

    # tunnel some attributes from HTTP Request to Browser
    #last_effective_url = property(lambda self: self.http.last_effective_url)
    #last_url = property(lambda self: self.http.last_url, set_last_url)
    #code = property(lambda self: self.http.code)

    @property
    def cookie_jar(self):
        return self._cookie_jar

    @cookie_jar.setter
    def cookie_jar(self, cookie_jar):
        self._cookie_jar = cookie_jar

    @property
    def speed(self):
        if self.dl:
            return self.dl.speed
        return 0

    @property
    def size(self):
        if self._size:
            return self._size
        if self.dl:
            return self.dl.size
        return 0

    @property
    def arrived(self):
        if self.dl:
            return self.dl.arrived
        return 0

    @property
    def percent(self):
        if not self.size:
            return 0
        return (self.arrived * 100) // self.size

    def clear_cookies(self):
        if self.cookie_jar:
            self.cookie_jar.clear()

    def clear_referer(self):
        self._last_url = None

    def abort_downloads(self):
        if self.dl:
            self._size = self.dl.size
            self.dl.abort = True

    def http_download(
        self,
        url,
        filename,
        get={},
        post={},
        referer=True,
        cookies=True,
        chunks=1,
        resume=False,
        progress_notify=None,
        disposition=False,
        options=None,
        cookie_jar=None
    ):
        """
        this can also download ftp.
        """
        my_cookie_jar = CookieJar()
        my_cookie_jar.add_cookies(self.cookie_jar)
        my_cookie_jar.add_cookies(cookie_jar)
        self._size = 0
        if type(referer) is bool:
            referer = None
        self.dl = HTTPDownload(
            url,
            filename,
            get,
            post,
            referer,
            my_cookie_jar if cookies else None,
            self.bucket,
            options,
            progress_notify,
            disposition,
        )

        name = self.dl.download(chunks, resume)
        self._size = self.dl.size

        self.dl = None

        return name

    def load(self, *args, **kwargs):
        """
        retrieves page.
        """
        request = self.get_request()
        data = request.load(*args, **kwargs)
        self.cookie_jar = data.cookie_jar
        request.close()
        return data

    def close(self):
        """
        cleanup.
        """
        if hasattr(self, "dl"):
            del self.dl
        if hasattr(self, "cookie_jar"):
            del self.cookie_jar
