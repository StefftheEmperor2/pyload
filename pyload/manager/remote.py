# -*- coding: utf-8 -*-
#@author: mkaay

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import object
from traceback import print_exc

from future import standard_library

standard_library.install_aliases()


class RemoteManager(object):
    available = []

    def __init__(self, core):
        self.pyload = core
        self.backends = []

        if self.pyload.remote:
            self.available.append("WebSocketBackend")

    def start(self):
        host = self.pyload.config.get('remote', 'host')
        port = self.pyload.config.get('remote', 'port')

        for b in self.available:
            klass = getattr(
                __import__("pyload.remote.{}".format(b.lower()),
                           globals(), locals(), [b.lower()], -1), b
            )
            backend = klass(self)
            if not backend.check_deps():
                continue
            try:
                backend.setup(host, port)
                self.pyload.log.info(
                    _("Starting {}: {}:{}").format(b, host, port))
            except Exception as e:
                self.pyload.log.error(
                    _("Failed loading backend {} | {}").format(b, e.message))
                if self.pyload.debug:
                    print_exc()
            else:
                backend.start()
                self.backends.append(backend)

            port += 1
