# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from future import standard_library

from pyload.thread.addon import AddonThread
from pyload.thread.decrypter import DecrypterThread
from pyload.thread.download import DownloadThread
from pyload.thread.info import InfoThread
from pyload.thread.plugin import PluginThread
from pyload.thread.remote import RemoteBackend

standard_library.install_aliases()
