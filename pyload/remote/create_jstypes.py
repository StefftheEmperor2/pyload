#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import io
import os
from builtins import dict

from future import standard_library

from pyload.remote import apitypes
from pyload.remote.apitypes_debug import enums

standard_library.install_aliases()


path = os.path.dirname(os.path.abspath(__file__))
module = os.path.join(path, "..")


# generate js enums


def main():

    print("generating apitypes.js")

    with io.open(os.path.join(module, 'webui', 'app', 'scripts', 'utils', 'apitypes.js'), 'wb') as f:
        f.write("""// Autogenerated, do not edit!
/*jslint -W070: false*/
define([], function() {
\t'use strict';
\treturn {
""")

    for name in enums:
        enum = getattr(apitypes, name)
        values = dict((attr, getattr(enum, attr))
                      for attr in dir(enum) if not attr.startswith("_"))

        f.write("\t\t{}: {},\n".format(name, values))

    f.write("\t};\n});")
    f.close()


if __name__ == "__main__":
    main()
