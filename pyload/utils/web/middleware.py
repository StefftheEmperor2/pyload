# -*- coding: utf-8 -*-
#@author: vuolter

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import object

from future import standard_library

standard_library.install_aliases()


# from wsgigzip import GzipMiddleware


class PrefixMiddleware(object):

    def __init__(self, app, prefix=None):
        self.app = app
        self.prefix = prefix or "/pyload"

    def __call__(self, e, h):
        path = e['PATH_INFO']
        if path.startswith(self.prefix):
            e['PATH_INFO'] = path.replace(self.prefix, "", 1)
        return self.app(e, h)


class StripPathMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return self.app(e, h)
