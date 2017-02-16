# -*- coding: utf-8 -*-
#@author: RaNaN

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import REQUEST, object
from contextlib import closing

from future import standard_library

from pyload.network.bucket import Bucket
from pyload.plugin.network.defaultrequest import (DefaultDownload,
                                                  DefaultRequest)

standard_library.install_aliases()


class RequestFactory(object):

    def __init__(self, core):
        self.pyload = core
        self.bucket = Bucket()
        self.update_bucket()

        self.pyload.evm.listen_to("config:changed", self.update_config)

    def get_url(self, *args, **kwargs):
        """
        See HTTPRequest for argument list.
        """
        with closing(DefaultRequest(self.get_config())) as h:
            rep = h.load(*args, **kwargs)
        return rep

        # old api methods above

    def get_request(self, context=None, klass=DefaultRequest):
        """
        Creates a request with new or given context.
        """

        # also accepts the context class directly
        if isinstance(context, klass.CONTEXT_CLASS):
            return klass(self.get_config(), context)
        elif context:
            return klass(*context)
        else:
            return klass(self.get_config())

    def get_download_request(self, request=None, klass=DefaultDownload):
        """
        Instantiates a instance for downloading.
        """

        # TODO: load with plugin manager
        return klass(self.bucket, request)

    def get_interface(self):
        return self.pyload.config.get('connection', 'interface')

    def get_proxies(self):
        """
        Returns a proxy list for the request classes.
        """
        if not self.pyload.config.get('proxy', 'activated'):
            return {}
        else:
            type = "http"
            setting = self.pyload.config.get('proxy', 'type').lower()
            if setting == "socks4":
                type = "socks4"
            elif setting == "socks5":
                type = "socks5"

            username = None
            if self.pyload.config.get('proxy', 'username') and self.pyload.config.get(
                    'proxy', 'username').lower() != "none":
                username = self.pyload.config.get('proxy', 'username')

            pw = None
            if self.pyload.config.get('proxy', 'password') and self.pyload.config.get(
                    'proxy', 'password').lower() != "none":
                pw = self.pyload.config.get('proxy', 'password')

            return {
                "type": type,
                "address": self.pyload.config.get('proxy', 'host'),
                "port": self.pyload.config.get('proxy', 'port'),
                "username": username,
                "password": pw,
            }

    def update_config(self, section, option, value):
        """
        Updates the bucket when a config value changed.
        """
        if option in ("limit_speed", "max_speed"):
            self.update_bucket()

    def get_config(self):
        """
        Returns options needed for pycurl.
        """
        return {"interface": self.get_interface(),
                "proxies": self.get_proxies(),
                "ipv6": self.pyload.config.get('connection', 'ipv6')}

    def update_bucket(self):
        """
        Set values in the bucket according to settings.
        """
        max_speed = self.pyload.config.get('connection', 'max_speed')
        if max_speed > 0:
            self.bucket.set_rate(max_speed * 1024)
        else:
            self.bucket.set_rate(-1)

# needs REQUEST in global namespace


def get_url(*args, **kwargs):
    return REQUEST.get_url(*args, **kwargs)


def get_request(*args, **kwargs):
    return REQUEST.get_request(*args, **kwargs)
