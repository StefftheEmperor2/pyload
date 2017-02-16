# -*- coding: utf-8 -*-
#@author: RaNaN

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from future import standard_library

from mod_pywebsocket import util
from mod_pywebsocket.dispatch import Dispatcher as BaseDispatcher

standard_library.install_aliases()


class Dispatcher(BaseDispatcher):

    def __init__(self):
        self._logger = util.get_class_logger(self)

        self._handler_suite_map = {}
        self._source_warnings = []

    def add_handler(self, path, handler):
        self._handler_suite_map[path] = handler
