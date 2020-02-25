# -*- coding: utf-8 -*-
# AUTHOR: mkaay, RaNaN

import time
from datetime import timedelta, datetime



class Cookie(object):
    def __init__(self):
        self._domain = None
        self._with_subdomains = None
        self._name = None
        self._value = None
        self._path = None
        self._expire = None
        self._secure = None
        self._max_age = None

    @property
    def domain(self):
        return self._domain

    @domain.setter
    def domain(self, domain):
        self._domain = domain

    @property
    def with_subdomains(self):
        return self._with_subdomains

    @with_subdomains.setter
    def with_subdomains(self, with_subdomains):
        self._with_subdomains =  with_subdomains

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path

    @property
    def expire(self):
        return self._expire

    @expire.setter
    def expire(self, expire):
        self._expire = expire

    @property
    def secure(self):
        return self._secure

    @secure.setter
    def secure(self, secure):
        self._secure = secure

    @property
    def max_age(self):
        return self._max_age

    @max_age.setter
    def max_age(self, max_age):
        self._max_age = max_age

    def set_dot_domain(self):
        domain = self.domain
        if domain is not None:
            if domain[0] != '.':
                self.domain = '.' + domain

    def get_formatted(self):
        domain = self.domain if self.domain is not None else '.'
        if self.with_subdomains is not None:
            if self.with_subdomains:
                with_subdomains = 'TRUE'
            else:
                with_subdomains = 'TRUE'
        else:
            with_subdomains = 'TRUE'

        path = self.path if self.path is not None else '/'
        if self.secure is not None:
            if self.secure:
                secure = 'TRUE'
            else:
                secure = 'FALSE'
        else:
            secure = 'FALSE'

        expire = self.expire if self.expire is not None \
            else int((datetime.fromtimestamp(int(time.time()))
                      + timedelta(hours=744)).timestamp()) #: 31 days retention
        return f"{domain}\t{with_subdomains}\t{path}\t{secure}\t{expire}\t{self.name}\t{self.value}".encode('UTF-8')

    @property
    def json(self):
        name = self.name.decode('utf-8') if isinstance(self.name, bytes) else self.name
        value = self.value.decode('utf-8') if isinstance(self.value, bytes) else self.value
        domain = self.domain.decode('utf-8') if isinstance(self.domain, bytes) else self.domain
        path = self.path.decode('utf-8') if isinstance(self.path, bytes) else self.path
        expire = self.expire.decode('utf-8') if isinstance(self.expire, bytes) else self.expire
        max_age = self.max_age.decode('utf-8') if isinstance(self.max_age, bytes) else self.max_age
        return {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
            "expire": expire,
            "secure": self.secure,
            "with_subdomains": self.with_subdomains,
            "max_age": max_age
        }

class CookieJarIterator:
    def __init__(self, cookie_jar):
        # Cookie_Jar object reference
        self._cookie_jar = cookie_jar
        # member variable to keep track of current index
        self._index = 0

    def __next__(self):
        ''''Returns the next value from team object's lists '''
        if self._index < len(self._cookie_jar):
            cookie = self._cookie_jar.get_cookie_at(self._index)
            self._index += 1
            return cookie
        # End of Iteration
        raise StopIteration


class CookieJar:
    def __init__(self, plugin_name=None, account=None):
        self._cookies = {}
        self.plugin = plugin_name
        self.account = account

    def add_cookies(self, cookie_list):
        for cookie in cookie_list:
            self.add_cookie(cookie)

    @staticmethod
    def factory_by_string(cookie_string):
        cookie_jar = __class__()
        cookie_split = cookie_string.split(';')
        for cookie_split_item in cookie_split:
            cookie_kv_split = cookie_split_item.strip().split('=')
            cookie_item = Cookie()
            cookie_item.name(cookie_kv_split[0])
            cookie_item.value(cookie_kv_split[1])
            cookie_jar.add_cookie(cookie_item)
        return cookie_jar

    @staticmethod
    def factory(cookies):
        cookie_jar = cookies
        if isinstance(cookies, CookieJar):
            cookie_jar = cookies
        elif type(cookies) is list:
            cookie_jar = CookieJar()
            for cookie in cookies:
                if type(cookie) is tuple:
                    cookie_object = Cookie()
                    cookie_object.domain = cookie[0]
                    cookie_object.name = cookie[1]
                    cookie_object.value = cookie[2]
                    cookie_jar.add_cookie(cookie_object)

        return cookie_jar

    def get_cookies(self):
        return list(self.cookies.values())

    def parse_cookie(self, name):
        if name in self.cookies:
            return self.cookies[name]
        else:
            return None

    def set_dot_domain(self):
        for cookie in self.cookies.values():
            cookie.set_dot_domain()

    def get_cookie(self, name):
        return self.parse_cookie(name)

    def add_cookie(self, cookie_item):
        self.cookies[
            cookie_item.name
        ] = cookie_item

    def set_cookie(
        self,
        domain,
        name,
        value,
        path="/",
        expire=time.time() + timedelta(hours=744).seconds,  #: 31 days retention
    ):
        cookie_item = Cookie()
        cookie_item.name = name
        cookie_item.value = value
        cookie_item.domain = domain
        cookie_item.path = path
        cookie_item.expire = expire
        self.add_cookie(cookie_item)

    @property
    def cookies(self):
        return self._cookies

    @cookies.setter
    def cookies(self, cookies):
        self._cookies = cookies

    def clear(self):
        self.cookies = {}

    def __iter__(self):
        return CookieJarIterator(self)

    def __len__(self):
        return len(self.cookies.keys())

    def get_cookie_at(self, index):
        return list(self.cookies.values())[index]

    @property
    def json(self):
        data = {}
        for key, value in self.cookies.items():
            key = key.decode('utf-8') if isinstance(key, bytes) else key
            data[key] = value.json
        return data


