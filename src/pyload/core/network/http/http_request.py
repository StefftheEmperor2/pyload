# -*- coding: utf-8 -*-
# AUTHOR: RaNaN

import codecs
import io
from itertools import chain
from logging import getLogger
from urllib.parse import quote, urlencode, unquote_plus, urlparse

import pycurl
from pyload import APPID
from ..exceptions import Abort
from .exceptions import BadHeader
from ..cookie_jar import Cookie, CookieJar
from datetime import datetime
from dateutil import tz
import re
import math

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


class HTTPRequestOption:
    def __init__(self, name=None, value=None):
        self._name = name
        self._value = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

class HTTPRequestOptionStoreIterator:

    def __init__(self, option_store):
        # Cookie_Jar object reference
        self._option_store = option_store
        # member variable to keep track of current index
        self._index = 0

    def __next__(self):
        ''''Returns the next value from team object's lists '''
        if self._index < len(self._option_store):
            option = self._option_store.get_option_at(self._index)
            self._index += 1
            return option
        # End of Iteration
        raise StopIteration


class HTTPRequestOptionStore:
    def __init__(self):
        self._store = {}

    def __setitem__(self, name, value):
        option = HTTPRequestOption()
        option.set_name(name)
        option.set_value(value)
        self._store[name] = option

    def __getitem__(self, name):
        return self._store[name]

    def __iter__(self):
        return HTTPRequestOptionStoreIterator(self)

    def __len__(self):
        return len(self._store.keys())

    def items(self):
        options = []
        for option in self:
            options.append((option.get_name(), option.get_value()))
        return options

    def set(self, key, value):
        self[key] = value

    def get_option_at(self, index):
        return list(self._store.values())[index]

    def add(self, other):
        if isinstance(other, self.__class__):
            for option in other:
                self[option.get_name()] = option.get_value()
        if type(other) is dict:
            for k, v in other:
                self[k] = v


class HTTPRequestHeaderStoreIterator:

    def __init__(self, header_store):
        # Cookie_Jar object reference
        self._header_store = header_store
        # member variable to keep track of current index
        self._index = 0

    def __next__(self):
        ''''Returns the next value from team object's lists '''
        if self._index < len(self._header_store):
            option = self._header_store.get_header_at(self._index)
            self._index += 1
            return option
        # End of Iteration
        raise StopIteration

class HTTPRequestHeader:
    def __init__(self, name=None, value=None):
        self._name = name
        self._value = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value


class HTTPHeaderStore:
    def __init__(self):
        self._store = {}

    def __setitem__(self, name, value):
        header = HTTPRequestHeader()
        header.set_name(name)
        header.set_value(value)
        self._store[name] = header

    def __getitem__(self, name):
        return self._store[name]

    def __iter__(self):
        return HTTPRequestHeaderStoreIterator(self)

    def __len__(self):
        return len(self._store.keys())

    def get_header_at(self, index):
        return list(self._store.values())[index]

    def has_key(self, key):
        return key in self._store

    def get_list(self):
        list = []
        for header in self:
            value = header.get_value()
            if value:
                list.append(header.get_name()+': '+header.get_value())
            else:
                list.append(header.get_name() + ':')
        return list

    def __add__(self, other):
        self.add(other)

    def add(self, other):
        if isinstance(other, HTTPRequestHeaderStore):
            for header in other:
                self[header.get_name()] = header.get_value()
        elif type(other) is list:
            for header in other:
                if type(header) is dict:
                    for k, v in header.items():
                        self[k] = v

    def set(self, key, value):
        self[key] = value

    @classmethod
    def factory_by_raw_header(cls, header):
        instance = cls()
        header_lines = header.splitlines()
        for header_line in header_lines:
            match = re.match(r"^\s*([a-zA-Z0-9\-_]*?)\s*:\s*([a-zA-Z0-9\-\._,\s:=/;:\"]*?)\s*$", header_line.decode('UTF-8'))
            if match:
                name = match[1].lower()
                value = match[2]
                if name is 'set-cookie':
                    continue
                instance.set(name, value)
        return instance


class HTTPRequestHeaderStore(HTTPHeaderStore):
    pass


class HTTPResponseHeaderStore(HTTPHeaderStore):
    pass


class HTTPResponse:
    def __init__(self):
        self._body = None
        self._code = None
        self._effective_url = None
        self._header = None
        self._header_store = None
        self.cookie_jar = None

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, body):
        self._body = body

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, code):
        self._code = code

    @property
    def effective_url(self):
        return self._effective_url

    @effective_url.setter
    def effective_url(self, effective_url):
        self._effective_url = effective_url

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, header):
        self._header = header
        self._header_store = HTTPResponseHeaderStore.factory_by_raw_header(header)

    @property
    def header_store(self):
        return self._header_store

class HTTPRequest:
    def __init__(self, cookies=None, options=None):
        self.c = pycurl.Curl()
        self.rep = None

        self.cookie_jar = cookies  #: cookiejar
        self._user_agent = None
        self.last_url = None
        self.abort = False
        self.code = 0  #: last http code

        self.header = bytes()
        self.headers = HTTPRequestHeaderStore()

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

        if pycurl.version_info()[7]:
            self.c.setopt(pycurl.ENCODING, b"gzip, deflate")


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

    def set_request_context(self, url, get, post, referer, cookies, multipart=False, content_type=None, options=None, headers=None, cookie_jar=None):
        """
        sets everything needed for the request.
        """
        self.rep = io.BytesIO()

        url = myquote(url)

        if isinstance(options, HTTPRequestOptionStore):
            for option in options:
                self.c.setopt(option.get_name(), option.get_value())
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

        if cookies is True or cookies is None:
            if isinstance(cookie_jar, CookieJar):
                for cookie in cookie_jar:
                    if not cookie.is_expired():
                        cookie_formatted = cookie.get_formatted()
                        self.c.setopt(pycurl.COOKIELIST, cookie_formatted.decode('utf-8'))

        if content_type is not None:
            self.headers.set('Content-Type', content_type)

        if headers is not None:
            self.headers.add(headers)

        if self.user_agent is not None:
            self.c.setopt(pycurl.USERAGENT, self.user_agent)

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
        content_type=None,
        options=None,
        headers=None,
        cookie_jar=None
    ):
        """
        load and returns a given page.
        """
        self.set_request_context(url,
                                 get,
                                 post,
                                 referer,
                                 cookies=cookies,
                                 cookie_jar=cookie_jar,
                                 multipart=multipart,
                                 content_type=content_type,
                                 options=options,
                                 headers=headers)

        self.header = bytes()

        default_headers = HTTPRequestHeaderStore()
        default_headers["Accept"] = "*/*"
        default_headers["Accept-Language"] = "en-US,en"
        default_headers["Accept-Charset"] = "ISO-8859-1,utf-8;q=0.7,*;q=0.7"
        default_headers["Connection"] = "keep-alive"
        default_headers["Keep-Alive"] = "300"
        default_headers["Expect"] = ""
        default_headers.add(self.headers)

        self.c.setopt(pycurl.HTTPHEADER, default_headers.get_list())

        """Temporary - remove later !!! """
        self.c.setopt(pycurl.SSL_VERIFYPEER, 0)
        self.c.setopt(pycurl.SSL_VERIFYHOST, 0)

        if not follow_location:
            self.c.setopt(pycurl.FOLLOWLOCATION, 0)

        if just_header:
            self.c.setopt(pycurl.NOBODY, 1)

        self.c.perform()
        rep = self.header if just_header else self.get_response()

        if just_header:
            self.c.setopt(pycurl.NOBODY, 0)

        effective_url = self.c.getinfo(pycurl.EFFECTIVE_URL)
        parsed_url = urlparse(url)
        response_cookies = self.decode_cookies(parsed_url.hostname.encode('UTF-8'))
        if save_cookies:
            try:
                self.add_cookies(response_cookies)
            except TypeError:
                pass
            finally:
                pass

        code = None
        try:
            code = self.verify_header()

        finally:
            self.rep.close()
            self.rep = None

        if decode:
            rep = self.decode_response(rep)

        response = HTTPResponse()
        response.body = rep
        response.code = code
        response.effective_url = effective_url
        response.header = self.header
        response.cookie_jar = response_cookies
        return response

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

    def decode_cookies(self, default_domain=None):
        header = self.header.splitlines()
        cookie_jar = CookieJar()
        for line in header:
            if not line.lower().startswith(b'set-cookie:'):
                continue
            cookie_line = line[11:]
            cookie_values = cookie_line.split(b';')

            is_first = True
            cookie_domain = None
            cookie_name = None
            cookie_value = None
            cookie_expires = None
            cookie_path = None
            cookie_max_age = None
            is_expired = False
            for cookie_value_line in cookie_values:
                cookie_key_value_pair = [item.strip() for item in cookie_value_line.split(b'=')]
                if is_first:
                    cookie_name = unquote_plus(cookie_key_value_pair[0].decode('utf-8'))
                    cookie_value = unquote_plus(cookie_key_value_pair[1].decode('utf-8'))
                if cookie_key_value_pair[0] == b'expires':
                    expires = cookie_key_value_pair[1].decode('UTF-8')
                    found = False
                    matches = re.match(r'^[0-9]*$', expires)
                    if matches:
                        found = True
                        expires = datetime.fromtimestamp(float(expires))
                    if not found:
                        matches = re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), ([0-9]{2})\-'
                                           + r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\-((?:[0-9]{4}|[0-9]{2})) '
                                           + r'([0-9]{2}):([0-9]{2}):([0-9]{2}) ([A-Z]*)$', expires)
                        if matches:
                            found = True
                            weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                            month_int = months.index(matches[3]) + 1
                            if len(matches[4]) == 2:
                                current_year = datetime.now().year
                                current_century = math.floor(current_year / 100)
                                if ((current_century * 100) + int(matches[4])) < current_year:
                                    year = ((current_century+1) * 100) + int(matches[4])
                                else:
                                    year = (current_century * 100) + int(matches[4])
                            else:
                                year = int(matches[4])

                            expires = datetime(year, month_int, int(matches[2]), int(matches[5]), int(matches[6]), int(matches[7]), 0, tz.gettz(matches[8]))
                        if found:
                            if expires < datetime.now(tz.tzlocal()):
                                is_expired = True
                            cookie_expires = expires

                if cookie_key_value_pair[0] == b'path':
                    cookie_path = cookie_key_value_pair[1]
                if cookie_key_value_pair[0] == b'domain':
                    cookie_domain = cookie_key_value_pair[1]
                if cookie_key_value_pair[0] == b'Max-Age':
                    cookie_max_age = cookie_key_value_pair[1]
                is_first = False

            if cookie_domain is None and default_domain is not None:
                if default_domain[0] == '.':
                    cookie_domain = default_domain
                else:
                    cookie_domain = b'.'+default_domain

            if not is_expired:
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
        self.headers[name] = value

    def clear_headers(self):
        self.headers.clear()

    @property
    def user_agent(self):
        if self._user_agent is None:
            user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:75.0) Gecko/20100101 Firefox/75.0"
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


class BigHTTPRequest(HTTPRequest):
    """
    Overcome HTTPRequest's load() size limit to allow loading very big web pages by
    overrding HTTPRequest's write() function.
    """

    # TODO: Add 'limit' parameter to HTTPRequest in v0.6.x
    def __init__(self, cookies=None, options=None, limit=1_000_000):
        self.limit = limit
        super().__init__(cookies=cookies, options=options)

    def write(self, buf):
        """
        writes response.
        """
        if self.limit and self.rep.tell() > self.limit or self.abort:
            rep = self.getResponse()
            if self.abort:
                raise Abort
            with open("response.dump", mode="wb") as fp:
                fp.write(rep)
            raise Exception("Loaded Url exceeded limit")

        self.rep.write(buf)

