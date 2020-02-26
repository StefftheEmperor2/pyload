# -*- coding: utf-8 -*-
# AUTHOR: RaNaN

import codecs
import io
from itertools import chain
from logging import getLogger
from urllib.parse import quote, urlencode, unquote_plus

import pycurl
from pyload import APPID

from ..exceptions import Abort
from .exceptions import BadHeader
from ..cookie_jar import Cookie, CookieJar


def myquote(url):
    try:
        url = url.encode()
    except AttributeError:
        pass
    return quote(url, safe="%/:=&?~#+!$,;'@()*[]")


def myurlencode(data):
    data = dict(data)
    return urlencode(
        {
            x.encode()
            if hasattr(x, "encode")
            else x: y.encode()
            if hasattr(y, "encode")
            else y
            for x, y in data.items()
        }
    )


BAD_STATUS_CODES = tuple(
    chain((400,), (401,), range(403, 406), range(408, 418), range(500, 506))
)


class HTTPRequest:
    def __init__(self, cookies=None, options=None):
        self.c = pycurl.Curl()
        self.rep = None

        self.cookie_jar = cookies  #: cookiejar
        self._user_agent = None
        self.last_url = None
        self.last_effective_url = None
        self.abort = False
        self.code = 0  #: last http code

        self.header = bytes()

        self.headers = []  #: temporary request header

        self.init_handle()
        if options is not None:
            self.set_interface(options)

        self.c.setopt(pycurl.WRITEFUNCTION, self.write)
        self.c.setopt(pycurl.HEADERFUNCTION, self.write_header)
        self.log = getLogger(APPID)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def init_handle(self):
        """
        sets common options to curl handle.
        """
        self.c.setopt(pycurl.COOKIEJAR, '')
        self.c.setopt(pycurl.COOKIEFILE, '')
        self.c.setopt(pycurl.FOLLOWLOCATION, 1)
        self.c.setopt(pycurl.MAXREDIRS, 10)
        self.c.setopt(pycurl.CONNECTTIMEOUT, 30)
        self.c.setopt(pycurl.NOSIGNAL, 1)
        self.c.setopt(pycurl.NOPROGRESS, 1)
        if hasattr(pycurl, "AUTOREFERER"):
            self.c.setopt(pycurl.AUTOREFERER, 1)
        self.c.setopt(pycurl.SSL_VERIFYPEER, 0)
        self.c.setopt(pycurl.LOW_SPEED_TIME, 60)
        self.c.setopt(pycurl.LOW_SPEED_LIMIT, 5)
        if hasattr(pycurl, "USE_SSL"):
            self.c.setopt(pycurl.USE_SSL, pycurl.USESSL_TRY)

        # self.c.setopt(pycurl.VERBOSE, 1)

        self.c.setopt(pycurl.USERAGENT, self.user_agent)
        if pycurl.version_info()[7]:
            self.c.setopt(pycurl.ENCODING, b"gzip, deflate")
        self.c.setopt(
            pycurl.HTTPHEADER,
            [
                b"Accept: */*",
                b"Accept-Language: en-US,en",
                b"Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                b"Connection: keep-alive",
                b"Keep-Alive: 300",
                b"Expect:",
            ],
        )

    def set_interface(self, options):
        options = {
            k: (v.encode() if hasattr(v, "encode") else v) for k, v in options.items()
        }

        interface, proxy, ipv6 = (
            options["interface"],
            options["proxies"],
            options["ipv6"],
        )

        if interface and interface.lower() != "none":
            self.c.setopt(pycurl.INTERFACE, interface)

        if proxy:
            if proxy["type"] == "socks4":
                self.c.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS4)
            elif proxy["type"] == "socks5":
                self.c.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
            else:
                self.c.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)

            self.c.setopt(pycurl.PROXY, proxy["host"])
            self.c.setopt(pycurl.PROXYPORT, int(proxy["port"]))

            if proxy["username"]:
                user = proxy["username"]
                pw = proxy["password"]
                self.c.setopt(pycurl.PROXYUSERPWD, f"{user}:{pw}".encode())

        if ipv6:
            self.c.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_WHATEVER)
        else:
            self.c.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V4)

        if "auth" in options:
            self.c.setopt(pycurl.USERPWD, options["auth"])

        if "timeout" in options:
            self.c.setopt(pycurl.LOW_SPEED_TIME, int(options["timeout"]))

    def add_cookies(self, cookies):
        """
        put cookies from curl handle to cookie_jar.
        """
        if self.cookie_jar is None:
            self.cookie_jar = CookieJar()

        if isinstance(self.cookie_jar, CookieJar):
            try:
                iter(cookies)
            except TypeError:
                raise
            self.cookie_jar.add_cookies(cookies)

    def clear_cookies(self):
        self.c.setopt(pycurl.COOKIELIST, "")

    def set_request_context(self, url, get, post, referer, cookies, multipart=False, content_type=None):
        """
        sets everything needed for the request.
        """
        self.rep = io.BytesIO()

        url = myquote(url)

        if get:
            get = urlencode(get)
            url = f"{url}?{get}"

        self.c.setopt(pycurl.URL, url)
        self.c.last_url = url

        if post:
            self.c.setopt(pycurl.POST, 1)
            if not multipart:
                if isinstance(post, str):
                    post = post.encode()
                else:  # TODO: check if mapping
                    post = myurlencode(post)

                self.c.setopt(pycurl.POSTFIELDS, post)
            else:
                post = [
                    (x, y.encode() if hasattr(y, "encode") else y)
                    for x, y in post.items()
                ]
                self.c.setopt(pycurl.HTTPPOST, post)
        else:
            self.c.setopt(pycurl.POST, 0)

        if referer and self.last_url:
            self.c.setopt(pycurl.REFERER, self.last_url)

        if cookies:
            if isinstance(cookies, CookieJar):
                curl_cookies = cookies.get_cookie_list()

                curl_list = curl_cookies.decode('utf-8')
                self.c.setopt(pycurl.COOKIELIST, curl_list)
        if content_type is not None:
            self.headers.append('Content-Type: '+content_type)

    def load(
        self,
        url,
        get={},
        post={},
        referer=True,
        cookies=True,
        just_header=False,
        multipart=False,
        decode=False,
        follow_location=True,
        save_cookies=True,
        content_type=None
    ):
        """
        load and returns a given page.
        """
        self.set_request_context(url, get, post, referer, cookies, multipart, content_type=content_type)

        self.header = bytes()

        self.c.setopt(pycurl.HTTPHEADER, self.headers)

        if not follow_location:
            self.c.setopt(pycurl.FOLLOWLOCATION, 0)

        if just_header:
            self.c.setopt(pycurl.NOBODY, 1)

        self.c.perform()
        rep = self.header if just_header else self.get_response()

        if just_header:
            self.c.setopt(pycurl.NOBODY, 0)

        self.last_effective_url = self.c.getinfo(pycurl.EFFECTIVE_URL)

        response_cookies = self.decode_cookies()
        if save_cookies:
            try:
                self.add_cookies(response_cookies)
            except TypeError:
                pass
            finally:
                pass

        try:
            self.code = self.verify_header()

        finally:
            self.rep.close()
            self.rep = None

        if decode:
            rep = self.decode_response(rep)

        return rep

    def verify_header(self):
        """
        raise an exceptions on bad headers.
        """
        code = int(self.c.getinfo(pycurl.RESPONSE_CODE))
        if code in BAD_STATUS_CODES:
            # 404 will NOT raise an exception
            raise BadHeader(code, self.header, self.get_response())
        return code

    def check_header(self):
        """
        check if header indicates failure.
        """
        return int(self.c.getinfo(pycurl.RESPONSE_CODE)) not in BAD_STATUS_CODES

    def get_response(self):
        """
        retrieve response from bytes io.
        """
        if self.rep is None:
            return ""
        else:
            value = self.rep.getvalue()
            self.rep.close()
            self.rep = io.BytesIO()
            return value

    def decode_cookies(self):
        header = self.header.splitlines()
        cookie_jar = CookieJar()
        for line in header:
            if not line.lower().startswith(b'set-cookie:'):
                continue
            cookie_line = line[11:]
            cookie_values = cookie_line.split(b';')

            is_first = True
            cookie_domain = None
            cookie_name= None
            cookie_value = None
            cookie_expires = None
            cookie_path = None
            cookie_max_age = None

            for cookie_value_line in cookie_values:
                cookie_key_value_pair = [item.strip() for item in cookie_value_line.split(b'=')]
                if is_first:
                    cookie_name = unquote_plus(cookie_key_value_pair[0].decode('utf-8'))
                    cookie_value = unquote_plus(cookie_key_value_pair[1].decode('utf-8'))
                if cookie_key_value_pair[0] == b'expires':
                    cookie_expires = cookie_key_value_pair[1]
                if cookie_key_value_pair[0] == b'path':
                    cookie_path = cookie_key_value_pair[1]
                if cookie_key_value_pair[0] == b'domain':
                    cookie_domain = cookie_key_value_pair[1]
                if cookie_key_value_pair[0] == b'Max-Age':
                    cookie_max_age = cookie_key_value_pair[1]
                is_first = False

            cookie_item = Cookie()
            cookie_item.name = cookie_name
            cookie_item.value = cookie_value
            cookie_item.domain = cookie_domain
            cookie_item.expire = cookie_expires
            cookie_item.path = cookie_path
            cookie_item.max_age = cookie_max_age

            cookie_jar.add_cookie(cookie_item)

        return cookie_jar

    def decode_response(self, rep):
        """
        decode with correct encoding, relies on header.
        """
        header = self.header.splitlines()
        encoding = "utf-8"  #: default encoding

        for line in header:
            line = line.lower().replace(b' ', b'')
            if not line.startswith(b'content-type:') or (
                b'text' not in line and b'application' not in line
            ):
                continue

            none, delemiter, charset = line.rpartition(b'charset=')
            if delemiter:
                charset = charset.split(b';')
                if charset:
                    encoding = charset[0].decode('utf-8')

        try:
            # self.log.debug(f"Decoded {encoding}")
            if codecs.lookup(encoding).name == "utf-8" and rep.startswith(
                codecs.BOM_UTF8
            ):
                encoding = "utf-8-sig"

            decoder = codecs.getincrementaldecoder(encoding)("replace")
            rep = decoder.decode(rep, True)

            # TODO: html_unescape as default

        except LookupError:
            self.log.debug(f"No Decoder foung for {encoding}")

        except Exception:
            self.log.debug(f"Error when decoding string from {encoding}", exc_info=True)

        return rep

    def write(self, buf):
        """
        writes response.
        """
        if self.rep.tell() > 1_000_000 or self.abort:
            rep = self.get_response()
            if self.abort:
                raise Abort
            with open("response.dump", mode="wb") as fp:
                fp.write(rep)
            raise Exception("Loaded Url exceeded limit")

        self.rep.write(buf)

    def write_header(self, buf):
        """
        writes header.
        """
        self.header += buf

    def put_header(self, name, value):
        self.headers.append(f"{name}: {value}")

    def clear_headers(self):
        self.headers = []

    @property
    def user_agent(self):
        if self._user_agent is None:
            user_agent = b"Mozilla/5.0 (X11; Linux x86_64; rv:75.0) Gecko/20100101 Firefox/75.0"
        else:
            user_agent = self._user_agent
        return user_agent

    @user_agent.setter
    def user_agent(self, user_agent):
        self._user_agent = user_agent

    def close(self):
        """
        cleanup, unusable after this.
        """
        if self.rep:
            self.rep.close()
            del self.rep

        if hasattr(self, "cookie_jar"):
            del self.cookie_jar

        if hasattr(self, "c"):
            self.c.close()
            del self.c
