# -*- coding: utf-8 -*-
# AUTHOR: mkaay, RaNaN

import importlib
import os
import re
import sys
import json
import time
import hashlib
from ast import literal_eval
from itertools import chain
from functools import reduce

import semver
import subprocess
import shutil

from pyload import APPID, PKGDIR


class PluginManager:
    ROOT = "pyload.plugins."
    USERROOT = "plugins."
    TYPES = (
        "decrypter",
        "container",
        "downloader",
        "anticaptcha",
        "account",
        "addon",
        "base",
    )

    _PATTERN = re.compile(r'\s*__pattern__\s*=\s*r?(?:"|\')([^"\']+)')
    _VERSION = re.compile(r'\s*__version__\s*=\s*(?:"|\')([\d.]+)')
    _PYLOAD_VERSION = re.compile(r'\s*__pyload_version__\s*=\s*(?:"|\')([\d.]+)')
    _CONFIG = re.compile(r"\s*__config__\s*=\s*(\[[^\]]+\])", re.MULTILINE)
    _DESC = re.compile(r'\s*__description__\s*=\s*(?:"|"""|\')([^"\']+)', re.MULTILINE)

    def __init__(self, core):
        self.pyload = core
        self._ = core._

        self.plugins = {}
        self.create_index()
        # register for import addon
        sys.meta_path.append(self)

        if core.config.get('browser_extension', 'enabled'):
            self.create_browser_extensions()

    def create_browser_extensions(self):
        permissions = []
        matches = []
        captchas = {}

        for crypter_info in self.crypter_plugins.values():
            crypter = self.load_class('decrypter', crypter_info['name'], from_userdir=crypter_info['user'])
            permissions.extend(crypter.get_browser_extension_permissions())
            matches.extend(crypter.get_browser_extension_matches())

        for captcha_info in self.captcha_plugins.values():
            captcha_plugin = self.load_class('anticaptcha', captcha_info['name'], from_userdir=captcha_info['user'])
            interactive_script = captcha_plugin.get_interactive_script()
            permissions.extend(captcha_plugin.get_browser_extension_permissions())
            matches.extend(captcha_plugin.get_browser_extension_matches())
            if interactive_script is not None:
                captchas[captcha_info['name']] = {"version": captcha_plugin.__version__, "script": interactive_script}

        permissions = reduce(lambda l, x: l.append(x) or l if x not in l else l, permissions, [])
        matches = reduce(lambda l, x: l.append(x) or l if x not in l else l, matches, [])

        permissions.sort()
        matches.sort()

        browser_extension_dir = os.path.join(self.pyload.userdir, 'BrowserExtensions', 'mozilla')
        hash_file = os.path.join(browser_extension_dir, 'extension.json')
        do_build_browser_extension = False
        build = 0
        extension_id = None
        if os.path.exists(hash_file):
            extension_data = None
            with open(hash_file) as json_file_handle:
                extension_data = json.load(json_file_handle)
            build = extension_data['build']
            extension_id = extension_data['extension_id']
            extension_hash = str(self.hash_browser_extension(permissions, matches, captchas))
            if extension_hash != extension_data['hash']:
                do_build_browser_extension = True
        else:
            do_build_browser_extension = True

        if do_build_browser_extension:
            self.build_browser_extensions(permissions, matches, captchas, build+1, extension_id)

    def hash_browser_extension(self, permissions, matches, captchas):
        captcha_list = []
        for name, captcha in captchas.items():
            captcha_list.append(name + '::' + captcha['version'])
        captcha_list.sort()
        m = hashlib.md5()
        m.update(("".join(permissions) + "".join(matches) + "".join(captcha_list)).encode('UTF-8'))
        return m.hexdigest()

    def build_browser_extensions(self, permissions, matches, captchas, build, extension_id):
        self.pyload.log.info("Rebuilding browser extensions")
        browser_extension_dir = os.path.join(PKGDIR, 'BrowserExtensions', 'mozilla')
        user_dir = self.pyload.userdir
        browser_extension_output_dir = os.path.join(user_dir, 'BrowserExtensions', 'mozilla')
        build_file_name = os.path.join(user_dir, 'build')
        manifest_template_file = os.path.join(browser_extension_dir, 'manifest-template.json')
        with open(manifest_template_file) as json_file_handle:
            manifest = json.load(json_file_handle)

        manifest['permissions'].extend(permissions)
        manifest['content_scripts'][0]['matches'].extend(matches)
        browser_specific_settings = {
            'gecko': {}
        }
        if extension_id is not None:
            browser_specific_settings['gecko']['id'] = extension_id

        schema = 'https' if self.pyload.config.get('webui', 'use_ssl') else 'http'
        domain = self.pyload.config.get('webui', 'public_domain') \
            if self.pyload.config.get('webui', 'public_domain') \
            else f"{self.pyload.config.get('webui', 'host')}:{self.pyload.config.get('webui', 'port')}"
        browser_extension_base_path = f"{schema}://{domain}/browser_extension"
        browser_specific_settings['gecko']['update_url'] = f"{browser_extension_base_path}/updates.json"
        version = manifest['version'] + '.' + str(build)
        manifest['version'] = version

        browser_extension_versioned_output_dir = os.path.join(browser_extension_output_dir, version)
        os.makedirs(browser_extension_versioned_output_dir, exist_ok=True)
        manifest_output_file = os.path.join(browser_extension_versioned_output_dir, 'manifest.json')
        with open(manifest_output_file, 'w') as json_file:
            json.dump(manifest, json_file)

        captcha_js_template_file = os.path.join(browser_extension_dir, 'captcha-template.js')
        captcha_string = self.file_get_contents(captcha_js_template_file)
        captcha_interactive_scripts = ''
        is_first = True
        for captcha_name, captcha_info in captchas.items():
            if not is_first:
                captcha_interactive_scripts += ",\n"
            captcha_interactive_scripts += "\t\t\"" + captcha_name + "\": function(request, pyload) {\n\t\t\t" \
                                           + captcha_info['script'] \
                                           + "\n}"
            is_first = False

        captcha_js_file = os.path.join(browser_extension_versioned_output_dir, 'captcha.js')
        self.file_put_contents(captcha_js_file,
                               captcha_string.replace('%%%INTERACTIVE_SCRIPTS%%%', captcha_interactive_scripts))

        self.copy_browser_extension_files(
            browser_extension_dir,
            os.path.join(browser_extension_output_dir, version),
            [
                'captcha-template.js',
                'manifest-template.json',
            ]
        )

        path_to_web_ext = self.pyload.config.get('browser_extension', 'web_ext_path')
        if not os.path.exists(path_to_web_ext):
            path_to_web_ext = shutil.which(path_to_web_ext)

        p = subprocess.Popen(
            [
                path_to_web_ext,
                'sign',
                f"--source-dir={browser_extension_versioned_output_dir}",
                '--no-config-discovery',
                '--channel=unlisted',
                '--no-input=true',
                f"--artifacts-dir={browser_extension_output_dir}",
                f"--api-key={self.pyload.config.get('browser_extension', 'amo_jwt_issuer')}",
                f"--api-secret={self.pyload.config.get('browser_extension', 'amo_jwt_secret')}"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=browser_extension_versioned_output_dir
        )
        out, err = p.communicate()

        match = re.search(re.compile(b"Extension ID: (\{[0-9a-f\-]*\})"), out)
        file_match = re.search(re.compile(b"Downloaded:\n(?:\s*)([a-zA-Z0-9\.\-+_/\\: ]*)\n"), out)

        if match and file_match:
            extension_file_path = file_match[1].decode('UTF-8')
            extension_id = match[1].decode('UTF-8')
            browser_extension_hash = self.hash_browser_extension(permissions, matches, captchas)

            with open(os.path.join(browser_extension_output_dir, 'extension.json'), 'w') as json_file:
                json.dump({
                    'hash': browser_extension_hash,
                    'extension_id': extension_id,
                    'version': version,
                    'build': str(build)
                }, json_file)

            updates_file = os.path.join(browser_extension_output_dir, 'updates.json')
            if os.path.exists(updates_file):
                with open(updates_file, 'r') as json_file:
                    updates = json.load(json_file)
            else:
                updates = {
                    'addons': {
                        extension_id: {
                            'updates': []
                        }
                    }
                }

            extension_file_name = os.path.basename(extension_file_path)
            updates['addons'][extension_id]['updates'].append({
                'version': version,
                'update_link': f"{browser_extension_base_path}/{extension_file_name}",
                'update_hash': f"sha512:{self.get_sha512(extension_file_path)}"
            })

            with open(updates_file, 'w') as json_file:
                json.dump(updates, json_file)


        else:
            self.pyload.log.error('Generating browser extension failed')

    @staticmethod
    def get_sha512(file):
        # BUF_SIZE is totally arbitrary, change for your app!
        buf_size = 65536  # lets read stuff in 64kb chunks!

        sha512 = hashlib.sha512()
        with open(file, 'rb') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break

                sha512.update(data)
        return sha512.hexdigest()

    @classmethod
    def copy_browser_extension_files(cls, source, destination, blacklist=[], root=[]):
        dir_list = os.listdir(os.path.join(source, *root))
        for item in dir_list:
            sub_item = os.path.join(*root, item)
            if sub_item not in blacklist:
                source_full_path = os.path.join(source, sub_item)
                destination_full_path = os.path.join(destination, sub_item)
                if os.path.isdir(source_full_path):
                    os.makedirs(destination_full_path, exist_ok=True)
                    new_root = root[:]
                    new_root.append(item)
                    cls.copy_browser_extension_files(source, destination, blacklist, new_root)
                else:
                    shutil.copyfile(source_full_path, destination_full_path)

    @staticmethod
    def file_get_contents(filename):
        if os.path.exists(filename):
            fp = open(filename, "r")
            content = fp.read()
            fp.close()
            return content

    @staticmethod
    def file_put_contents(filename, content):
        fp = open(filename, "w")
        fp.write(content)
        fp.close()

    def create_index(self):
        """
        create information for all plugins available.
        """

        def merge(dst, src, overwrite=False):
            """
            merge dict of dicts.
            """
            for name in src:
                if name in dst:
                    if overwrite:
                        dst[name].update(src[name])
                    else:
                        for k in set(src[name].keys()) - set(dst[name].keys()):
                            dst[name][k] = src[name][k]
                else:
                    dst[name] = src[name]

        self.pyload.log.debug("Indexing plugins...")

        userplugins_dir = os.path.join(self.pyload.userdir, "plugins")
        os.makedirs(userplugins_dir, exist_ok=True)
        sys.path.append(self.pyload.userdir)

        try:
            fp = open(os.path.join(userplugins_dir, "__init__.py"), mode="wb")
            fp.close()
        except Exception:
            pass

        self.crypter_plugins, config = self.parse("decrypters", pattern=True)
        self.plugins["decrypter"] = self.crypter_plugins
        default_config = config

        self.container_plugins, config = self.parse("containers", pattern=True)
        self.plugins["container"] = self.container_plugins
        merge(default_config, config)

        self.hoster_plugins, config = self.parse("downloaders", pattern=True)
        self.plugins["downloader"] = self.hoster_plugins
        merge(default_config, config)

        self.addon_plugins, config = self.parse("addons")
        self.plugins["addon"] = self.addon_plugins
        merge(default_config, config)

        self.captcha_plugins, config = self.parse("anticaptchas")
        self.plugins["anticaptcha"] = self.captcha_plugins
        merge(default_config, config)

        self.account_plugins, config = self.parse("accounts")
        self.plugins["account"] = self.account_plugins
        merge(default_config, config)

        self.internal_plugins, config = self.parse("base")
        self.plugins["base"] = self.internal_plugins
        merge(default_config, config)

        for name, config in default_config.items():
            desc = config.pop("desc", "")
            config = [[k] + list(v) for k, v in config.items()]
            try:
                self.pyload.config.add_plugin_config(name, config, desc)
            except Exception as exc:
                self.pyload.log.error(
                    self._("Invalid config in {}: {}").format(name, config),
                    exc,
                    exc_info=self.pyload.debug > 1,
                    stack_info=self.pyload.debug > 2,
                )

    def parse(self, folder, pattern=False, home={}):
        """
        returns dict with information
        home contains parsed plugins from pyload.

        {
        name : {path, version, config, (pattern, re), (plugin, class)}
        }

        """
        plugins = {}
        if home:
            pfolder = os.path.join(self.pyload.userdir, "plugins", folder)
            os.makedirs(pfolder, exist_ok=True)
            try:
                fp = open(os.path.join(pfolder, "__init__.py"), mode="wb")
                fp.close()
            except Exception:
                pass
        else:
            pfolder = os.path.join(PKGDIR, "plugins", folder)

        configs = {}
        for entry in os.listdir(pfolder):
            if (
                    os.path.isfile(os.path.join(pfolder, entry)) and entry.endswith(".py")
            ) and not entry.startswith("_"):

                with open(os.path.join(pfolder, entry)) as data:
                    content = data.read()

                name = entry[:-3]
                if name[-1] == ".":
                    name = name[:-4]

                m_pyver = self._PYLOAD_VERSION.search(content)
                if m_pyver is None:
                    self.pyload.log.debug(
                        f"__pyload_version__ not found in plugin {name}"
                    )
                else:
                    pyload_version = m_pyver.group(1)

                    requires_version = f"{pyload_version}.0"
                    requires_version_info = semver.parse_version_info(requires_version)

                    if self.pyload.version_info.major:
                        core_version = self.pyload.version_info.major
                        plugin_version = requires_version_info.major
                    else:
                        core_version = self.pyload.version_info.minor
                        plugin_version = requires_version_info.minor

                    if core_version > plugin_version:
                        self.pyload.log.warning(
                            self._(
                                "Plugin {} not compatible with current pyLoad version"
                            ).format(name)
                        )
                        continue

                m_ver = self._VERSION.search(content)
                if m_ver is None:
                    self.pyload.log.debug(f"__version__ not found in plugin {name}")
                    version = 0
                else:
                    version = float(m_ver.group(1))

                # home contains plugins from pyload root
                if isinstance(home, dict) and name in home:
                    if home[name]["v"] >= version:
                        continue

                plugins[name] = {}
                plugins[name]["v"] = version

                module = entry.replace(".pyc", "").replace(".py", "")

                # the plugin is loaded from user directory
                plugins[name]["user"] = True if home else False
                plugins[name]["name"] = module
                plugins[name]["folder"] = folder

                if pattern:
                    m_pat = self._PATTERN.search(content)
                    pattern = r"^unmachtable$" if m_pat is None else m_pat.group(1)

                    plugins[name]["pattern"] = pattern

                    try:
                        plugins[name]["re"] = re.compile(pattern)
                    except Exception:
                        self.pyload.log.error(
                            self._("{} has a invalid pattern").format(name)
                        )

                # internals have no config
                if folder == "base":
                    self.pyload.config.delete_config(name)
                    continue

                m_desc = self._DESC.search(content)
                desc = "" if m_desc is None else m_desc.group(1)

                config = self._CONFIG.findall(content)
                if not config:
                    new_config = {"enabled": ["bool", "Activated", False], "desc": desc}
                    configs[name] = new_config
                    continue

                config = literal_eval(
                    config[0].strip().replace("\n", "").replace("\r", "")
                )

                if isinstance(config, list) and all(
                        isinstance(c, tuple) for c in config
                ):
                    config = {x[0]: x[1:] for x in config}
                else:
                    self.pyload.log.error(
                        self._("Invalid config in {}: {}").format(name, config)
                    )
                    continue

                if folder == "addons" and "enabled" not in config:
                    config["enabled"] = ["bool", "Activated", False]

                config["desc"] = desc
                configs[name] = config

        if not home:
            temp_plugins, temp_configs = self.parse(folder, pattern, plugins or True)
            plugins.update(temp_plugins)
            configs.update(temp_configs)

        return plugins, configs

    def parse_urls(self, urls):
        """
        parse plugins for given list of urls.
        """
        last = None
        res = []  #: tupels of (url, plugin)

        for url in urls:
            if type(url) not in (
                    str,
                    bytes,
                    memoryview,
            ):  #: check memoryview (as py2 byffer)
                continue
            found = False

            # NOTE: E1136: Value 'last' is unsubscriptable (unsubscriptable-object)
            if last and last[1]["re"].match(url):
                res.append((url, last[0]))
                continue

            for name, value in chain(
                    self.crypter_plugins.items(),
                    self.hoster_plugins.items(),
                    self.container_plugins.items(),
            ):
                if value["re"].match(url):
                    res.append((url, name))
                    last = (name, value)
                    found = True
                    break

            if not found:
                res.append((url, "DefaultPlugin"))

        return res

    def find_plugin(self, name, pluginlist=("decrypter", "downloader", "container")):
        for ptype in pluginlist:
            if name in self.plugins[ptype]:
                return self.plugins[ptype][name], ptype
        return None, None

    def get_plugin(self, name, original=False):
        """
        return plugin module from downloader|decrypter|container.
        """
        plugin, type = self.find_plugin(name)

        if not plugin:
            self.pyload.log.warning(self._("Plugin {} not found").format(name))
            plugin = self.hoster_plugins["DefaultPlugin"]

        if "new_module" in plugin and not original:
            return plugin["new_module"]

        return self.load_module(type, name, from_userdir=plugin['user'])

    def get_plugin_name(self, name):
        """
        used to obtain new name if other plugin was injected.
        """
        plugin, type = self.find_plugin(name)

        if "new_name" in plugin:
            return plugin["new_name"]

        return name

    def load_module(self, module_type, name):
        """
        Returns loaded module for plugin.

        :param type: plugin type, subfolder of module.plugins
        :param name:
        """
        plugins = self.plugins[module_type]
        if name in plugins:
            if APPID in plugins[name]:
                return plugins[name][APPID]
            try:
                module_name = plugins[name]["name"]
                module_folder = plugins[name]["folder"]
                module = __import__(
                    self.ROOT + f"{module_folder}.{module_name}",
                    globals(),
                    locals(),
                    plugins[name]["name"],
                )
                plugins[name][APPID] = module  #: cache import, maybe unneeded
                return module
            except Exception as exc:
                self.pyload.log.error(
                    self._("Error importing {name}: {msg}").format(name=name, msg=exc),
                    exc_info=self.pyload.debug > 1,
                    stack_info=self.pyload.debug > 2,
                )
        else:
            self.pyload.log.debug(f"Plugin {name} not found")
            self.pyload.log.debug(f"Available plugins : {plugins}")

    def load_class(self, module_type, name, from_userdir=False):
        """
        Returns the class of a plugin with the same name.
        """
        module = self.load_module(module_type, name, from_userdir=from_userdir)
        if module:
            return getattr(module, name)

    def get_account_plugins(self):
        """
        return list of account plugin names.
        """
        return list(self.account_plugins.keys())

    def find_module(self, fullname, path=None):
        # redirecting imports if necesarry
        if fullname.startswith(self.ROOT) or fullname.startswith(
                self.USERROOT
        ):  #: os.seperate pyload plugins
            if fullname.startswith(self.USERROOT):
                user = 1
            else:
                user = 0  #: used as bool and int

            split = fullname.split(".")
            if len(split) != 4 - user:
                return
            type, name = split[2 - user: 4 - user]

            if type in self.plugins and name in self.plugins[type]:
                # userplugin is a newer version
                if not user and self.plugins[type][name]["user"]:
                    return self
                # imported from userdir, but pyloads is newer
                if user and not self.plugins[type][name]["user"]:
                    return self

    def load_module(self, module_type, name, replace=True, from_userdir=False):
        if replace:
            if self.ROOT in name:
                newname = name.replace(self.ROOT, '')
            elif self.USERROOT in name:
                newname = name.replace(self.USERROOT, '')

            if module_type == 'addon':
                module_type = 'addons'
            elif module_type == 'account':
                module_type = 'accounts'
            elif module_type == 'decrypter':
                module_type = 'decrypters'
            elif module_type == 'downloader':
                module_type = 'downloaders'
            elif module_type == 'anticaptcha':
                module_type = 'anticaptchas'

            newname = (self.USERROOT if from_userdir else self.ROOT) + module_type + '.' + name
        else:
            newname = name

        if '.' in newname:
            base, plugin = newname.rsplit(".", 1)

        self.pyload.log.debug(f"Redirected import {name} -> {newname}")

        if newname not in sys.modules:  #: could be already in modules
            module = __import__(newname, globals(), locals(), [plugin])
            # inject under new an old name
            sys.modules[name] = module
            sys.modules[newname] = module
        else:
            module = sys.modules[newname]

        return module

    def reload_plugins(self, type_plugins):
        """
        reloads and reindexes plugins.
        """

        def merge(dst, src, overwrite=False):
            """
            merge dict of dicts.
            """
            for name in src:
                if name in dst:
                    if overwrite:
                        dst[name].update(src[name])
                    else:
                        for k in set(src[name].keys()) - set(dst[name].keys()):
                            dst[name][k] = src[name][k]
                else:
                    dst[name] = src[name]

        if not type_plugins:
            return False

        self.pyload.log.debug(f"Request reload of plugins: {type_plugins}")

        as_dict = {}
        for t, n in type_plugins:
            if t in as_dict:
                as_dict[t].append(n)
            else:
                as_dict[t] = [n]

        # we do not reload addons or internals, would cause to much side effects
        if "addon" in as_dict or "base" in as_dict:
            return False

        for type in as_dict.keys():
            for plugin in as_dict[type]:
                if plugin in self.plugins[type]:
                    if APPID in self.plugins[type][plugin]:
                        self.pyload.log.debug(f"Reloading {plugin}")
                        importlib.reload(self.plugins[type][plugin][APPID])

        # index creation
        self.crypter_plugins, config = self.parse("decrypters", pattern=True)
        self.plugins["decrypter"] = self.crypter_plugins
        default_config = config

        self.container_plugins, config = self.parse("containers", pattern=True)
        self.plugins["container"] = self.container_plugins
        merge(default_config, config)

        self.hoster_plugins, config = self.parse("downloaders", pattern=True)
        self.plugins["downloader"] = self.hoster_plugins
        merge(default_config, config)

        self.captcha_plugins, config = self.parse("anticaptchas")
        self.plugins["anticaptcha"] = self.captcha_plugins
        merge(default_config, config)

        self.account_plugins, config = self.parse("accounts")
        self.plugins["account"] = self.account_plugins
        merge(default_config, config)

        for name, config in default_config.items():
            desc = config.pop("desc", "")
            config = [[k] + list(v) for k, v in config.items()]
            try:
                self.pyload.config.add_plugin_config(name, config, desc)
            except Exception:
                self.pyload.log.error(
                    self._("Invalid config in {}: {}").format(name, config),
                    exc_info=self.pyload.debug > 1,
                    stack_info=self.pyload.debug > 2,
                )

        if "account" in as_dict:  #: accounts needs to be reloaded
            self.pyload.account_manager.init_plugins()
            self.pyload.scheduler.add_job(
                0, self.pyload.account_manager.get_account_infos
            )

        return True
