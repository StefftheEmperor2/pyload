# -*- coding: utf-8 -*-
#      ____________
#   _ /       |    \ ___________ _ _______________ _ ___ _______________
#  /  |    ___/    |   _ __ _  _| |   ___  __ _ __| |   \\    ___  ___ _\
# /   \___/  ______/  | '_ \ || | |__/ _ \/ _` / _` |    \\  / _ \/ _ `/ \
# \       |   o|      | .__/\_, |____\___/\__,_\__,_|    // /_//_/\_, /  /
#  \______\    /______|_|___|__/________________________//______ /___/__/
#          \  /
#           \/

import re

import os
import time

from functools import wraps

from ..datatypes.pyfile import PyFile
from ..network.request_factory import get_url
from ..utils.old.packagetools import parse_names
from ..utils import seconds, fs
from ..utils.misc import eval_js, add_crypted2
import json
from enum import IntFlag

from ..datatypes.exceptions import *
from ..datatypes.enums import *
from ..datatypes.data import *
from threading import Lock
# contains function names mapped to their permissions
# unlisted functions are for admins only
perm_map = {}

# decorator only called on init, never initialized, so has no effect on runtime
def permission(bits):
    class Wrapper:
        def __new__(cls, func, *args, **kwargs):
            perm_map[func.__name__] = bits
            return func

    return Wrapper


urlmatcher = re.compile(
    r"((https?|ftps?|xdcc|sftp):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+\-=\\\.&]*)",
    re.IGNORECASE,
)


class MethodNotExistsException(Exception):
    def __init__(self, method):
        self.method = method
        super().__init__()


class Perms(IntFlag):
    ALL = 0  #: requires no permission, but login
    ADD = 1  #: can add packages
    DELETE = 2  #: can delete packages
    STATUS = 4  #: see and change server status
    LIST = 16  #: see queue and collector
    MODIFY = 32  #: moddify some attribute of downloads
    DOWNLOAD = 64  #: can download from webinterface
    SETTINGS = 128  #: can access settings
    ACCOUNTS = 256  #: can access accounts
    LOGS = 512  #: can see server logs


class Role(IntFlag):
    ADMIN = 1  #: admin has all permissions implicit
    USER = 2


def has_permission(userperms, perms):
    # bytewise or perms before if needed
    return perms == (userperms & perms)

# API VERSION
__version__ = 1


class Api:
    """
    **pyLoads API**

    This is accessible either internal via core.api or via thrift backend.

    see Thrift specification file remote/thriftbackend/pyload.thrift\
    for information about data structures and what methods are usuable with rpc.

    Most methods requires specific permissions, please look at the source code if you need to know.\
    These can be configured via webinterface.
    Admin user have all permissions, and are the only ones who can access the methods with no specific permission.
    """

    def __init__(self, core):
        self.pyload = core
        self._ = core._
        self.thread_lock = Lock()

    def _convert_py_file(self, p):
        f = FileData(
            p["id"],
            p["url"],
            p["name"],
            p["plugin"],
            p["size"],
            p["format_size"],
            p["status"],
            p["statusmsg"],
            p["package"],
            p["error"],
            p["order"],
        )
        return f

    def _convert_config_format(self, c):
        sections = {}
        for section_name, sub in c.items():
            section = ConfigSection(section_name, sub["desc"])
            items = []
            for key, data in sub.items():
                if key in ("desc", "outline"):
                    continue
                item = ConfigItem()
                item.name = key
                item.description = data["desc"]
                item.value = str(data["value"])
                item.type = data["type"]
                items.append(item)
            section.items = items
            sections[section_name] = section
            if "outline" in sub:
                section.outline = sub["outline"]
        return sections

    @permission(Perms.SETTINGS)
    def get_config_value(self, category, option, section="core"):
        """
        Retrieve config value.

        :param category: name of category, or plugin
        :param option: config option
        :param section: 'plugin' or 'core'
        :return: config value as string
        """
        if section == "core":
            value = self.pyload.config[category][option]
        else:
            value = self.pyload.config.get_plugin(category, option)
        return value

    @permission(Perms.SETTINGS)
    def set_config_value(self, category, option, value, section="core"):
        """
        Set new config value.

        :param category:
        :param option:
        :param value: new config value
        :param section: 'plugin' or 'core
        """
        self.pyload.addon_manager.dispatch_event(
            "config_changed", category, option, value, section
        )

        if section == "core":
            self.pyload.config[category][option] = value

            if option in (
                "limit_speed",
                "max_speed",
            ):  #: not so nice to update the limit
                self.pyload.request_factory.update_bucket()

        elif section == "plugin":
            self.pyload.config.set_plugin(category, option, value)

    @permission(Perms.SETTINGS)
    def get_config(self):
        """
        Retrieves complete config of core.

        :return: list of `ConfigSection`
        """
        return self._convert_config_format(self.pyload.config.config)

    def get_config_dict(self):
        """
        Retrieves complete config in dict format, not for RPC.

        :return: dict
        """
        return self.pyload.config.config

    @permission(Perms.SETTINGS)
    def get_plugin_config(self):
        """
        Retrieves complete config for all plugins.

        :return: list of `ConfigSection`
        """
        return self._convert_config_format(self.pyload.config.plugin)

    def get_plugin_config_dict(self):
        """
        Plugin config as dict, not for RPC.

        :return: dict
        """
        return self.pyload.config.plugin

    @permission(Perms.STATUS)
    def pause_server(self):
        """
        Pause server: Tt wont start any new downloads, but nothing gets aborted.
        """
        self.pyload.thread_manager.pause = True

    @permission(Perms.STATUS)
    def unpause_server(self):
        """
        Unpause server: New Downloads will be started.
        """
        self.pyload.thread_manager.pause = False
        self.pyload.notify_change()

    @permission(Perms.STATUS)
    def toggle_pause(self):
        """
        Toggle pause state.

        :return: new pause state
        """
        self.pyload.thread_manager.pause ^= True
        paused = self.pyload.thread_manager.pause
        self.pyload.notify_change()
        return paused

    @permission(Perms.STATUS)
    def toggle_reconnect(self):
        """
        Toggle reconnect activation.

        :return: new reconnect state
        """
        self.pyload.config.toggle("reconnect", "enabled")
        reconnect_enabled = self.pyload.config.get("reconnect", "enabled")
        self.pyload.notify_change()
        return reconnect_enabled

    @permission(Perms.LIST)
    def status_server(self):
        """
        Some general information about the current status of pyLoad.

        :return: `ServerStatus`
        """
        server_status = ServerStatus(
            self.pyload.thread_manager.pause,
            len(self.pyload.thread_manager.processing_ids()),
            self.pyload.files.get_queue_count(),
            self.pyload.files.get_file_count(),
            0,
            not self.pyload.thread_manager.pause and self.is_time_download(),
            self.pyload.config.get("reconnect", "enabled") and self.is_time_reconnect(),
            self.is_captcha_waiting(),
        )

        for pyfile in [
            x.active
            for x in self.pyload.thread_manager.threads
            if x.active and isinstance(x.active, PyFile)
        ]:
            server_status.speed += pyfile.get_speed()  #: bytes/s

        return server_status

    @permission(Perms.STATUS)
    def free_space(self):
        """
        Available free space at download directory in bytes.
        """
        return fs.free_space(self.pyload.config.get("general", "storage_folder"))

    @permission(Perms.ALL)
    def get_server_version(self):
        """
        pyLoad Core version.
        """
        return self.pyload.version

    def kill(self):
        """
        Clean way to quit pyLoad.
        """
        self.pyload._do_exit = True

    def restart(self):
        """
        Restart pyload core.
        """
        self.pyload._do_restart = True

    @permission(Perms.LOGS)
    def get_log(self, offset=0):
        """
        Returns most recent log entries.

        :param offset: line offset
        :return: List of log entries
        """
        filename = os.path.join(
            self.pyload.config.get("log", "filelog_folder"), "log.txt"
        )
        try:
            with open(filename) as fh:
                lines = fh.readlines()
            if offset >= len(lines):
                return []
            return lines[offset:]
        except Exception:
            return ["No log available"]

    @permission(Perms.STATUS)
    def is_time_download(self):
        """
        Checks if pyload will start new downloads according to time in config.

        :return: bool
        """
        start = self.pyload.config.get("download", "start_time").split(":")
        end = self.pyload.config.get("download", "end_time").split(":")
        return seconds.compare(start, end)

    @permission(Perms.STATUS)
    def is_time_reconnect(self):
        """
        Checks if pyload will try to make a reconnect.

        :return: bool
        """
        start = self.pyload.config.get("reconnect", "start_time").split(":")
        end = self.pyload.config.get("reconnect", "end_time").split(":")
        return seconds.compare(start, end) and self.pyload.config.get(
            "reconnect", "enabled"
        )

    @permission(Perms.LIST)
    def status_downloads(self):
        """
        Status off all currently running downloads.

        :return: list of `DownloadStatus`
        """
        data = []
        for pyfile in self.pyload.thread_manager.get_active_files():
            if not isinstance(pyfile, PyFile):
                continue

            data.append(
                DownloadInfo(
                    pyfile.id,
                    pyfile.name,
                    pyfile.get_speed(),
                    pyfile.get_eta(),
                    pyfile.format_eta(),
                    pyfile.get_bytes_left(),
                    pyfile.get_size(),
                    pyfile.format_size(),
                    pyfile.get_percent(),
                    pyfile.status,
                    pyfile.get_status_name(),
                    pyfile.format_wait(),
                    pyfile.wait_until,
                    pyfile.packageid,
                    pyfile.package().name,
                    pyfile.pluginname,
                )
            )

        return data

    @permission(Perms.ADD)
    def add_package(self, name, links, dest=Destination.QUEUE.value):
        """
        Adds a package, with links to desired destination.

        :param name: name of the new package
        :param links: list of urls
        :param dest: `Destination`
        :return: package id of the new package
        """
        if self.pyload.config.get("general", "folder_per_package"):
            folder = name
        else:
            folder = ""

        folder = (
            folder.replace("http://", "")
            .replace(":", "")
            .replace("/", "_")
            .replace("\\", "_")
        )

        destination = Destination(int(dest))
        pid = self.pyload.files.add_package(name, folder, destination)

        if isinstance(links, str):
            links = [links]
        self.pyload.files.add_links(links, pid)

        self.pyload.log.info(
            self._("Added package {name} containing {count:d} links").format(
                name=name, count=len(links)
            )
        )

        self.pyload.files.save()
        return pid

    @permission(Perms.ADD)
    def parse_urls(self, html=None, url=None):
        """
        Parses html content or any arbitaty text for links and returns result of
        `check_urls`

        :param html: html source
        :return:
        """
        urls = []

        if html:
            urls += [x[0] for x in urlmatcher.findall(html)]

        if url:
            page = None
            try:
                page = get_url(url)
            except Exception as e:
                self.pyload.log.error(e)
            if page is not None:
                urls += [x[0] for x in urlmatcher.findall(page)]

        # remove duplicates
        return self.check_urls(set(urls))

    @permission(Perms.ADD)
    def check_urls(self, urls):
        """
        Gets urls and returns pluginname mapped to list of matches urls.

        :param urls:
        :return: {plugin: urls}
        """
        data = self.pyload.plugin_manager.parse_urls(urls)
        plugins = {}

        for url, plugin in data:
            if plugin in plugins:
                plugins[plugin].append(url)
            else:
                plugins[plugin] = [url]

        return plugins

    @permission(Perms.ADD)
    def check_online_status(self, urls):
        """
        initiates online status check.

        :param urls:
        :return: initial set of data as `OnlineCheck` instance containing the result id
        """
        data = self.pyload.plugin_manager.parse_urls(urls)

        rid = self.pyload.thread_manager.create_result_thread(data, False)

        tmp = [
            (url, (url, OnlineStatus(url, pluginname, "unknown", 3, 0)))
            for url, pluginname in data
        ]
        data = parse_names(tmp)
        result = {}

        for k, v in data.items():
            for url, status in v:
                status.packagename = k
                result[url] = status

        return OnlineCheck(rid, result)

    @permission(Perms.ADD)
    def check_online_status_container(self, urls, container, data):
        """
        checks online status of urls and a submited container file.

        :param urls: list of urls
        :param container: container file name
        :param data: file content
        :return: online check
        """
        with open(
            os.path.join(
                self.pyload.config.get("general", "storage_folder"), "tmp_" + container
            ),
            "wb",
        ) as th:
            th.write(data)

        return self.check_online_status(urls + [th.name])

    @permission(Perms.ADD)
    def poll_results(self, rid):
        """
        Polls the result available for ResultID.

        :param rid: `ResultID`
        :return: `OnlineCheck`, if rid is -1 then no more data available
        """
        result = self.pyload.thread_manager.get_info_result(rid)

        if "ALL_INFO_FETCHED" in result:
            del result["ALL_INFO_FETCHED"]
            return OnlineCheck(-1, result)
        else:
            return OnlineCheck(rid, result)

    @permission(Perms.ADD)
    def generate_packages(self, links):
        """
        Parses links, generates packages names from urls.

        :param links: list of urls
        :return: package names mapped to urls
        """
        result = parse_names((x, x) for x in links)
        return result

    @permission(Perms.ADD)
    def generate_and_add_packages(self, links, dest=Destination.QUEUE.value):
        """
        Generates and add packages.

        :param links: list of urls
        :param dest: `Destination`
        :return: list of package ids
        """
        return [
            self.add_package(name, urls, dest)
            for name, urls in self.generate_packages(links).items()
        ]

    @permission(Perms.ADD)
    def check_and_add_packages(self, links, dest=Destination.QUEUE.value):
        """
        Checks online status, retrieves names, and will add packages.
        Because of this packages are not added immediatly, only for internal use.

        :param links: list of urls
        :param dest: `Destination`
        :return: None
        """
        data = self.pyload.plugin_manager.parse_urls(links)
        self.pyload.thread_manager.create_result_thread(data, True)

    @permission(Perms.LIST)
    def get_package_data(self, pid):
        """
        Returns complete information about package, and included files.

        :param pid: package id
        :return: `PackageData` with .links attribute
        """
        data = self.pyload.files.get_package_data(int(pid))

        if not data:
            raise PackageDoesNotExists(pid)

        pdata = PackageData(
            data["id"],
            data["name"],
            data["folder"],
            data["site"],
            data["password"],
            data["queue"],
            data["order"],
            links=[self._convert_py_file(x) for x in data["links"].values()],
        )

        return pdata

    @permission(Perms.LIST)
    def get_package_info(self, pid):
        """
        Returns information about package, without detailed information about containing
        files.

        :param pid: package id
        :return: `PackageData` with .fid attribute
        """
        data = self.pyload.files.get_package_data(int(pid))

        if not data:
            raise PackageDoesNotExists(pid)

        pdata = PackageData(
            data["id"],
            data["name"],
            data["folder"],
            data["site"],
            data["password"],
            data["queue"],
            data["order"],
            fids=[int(x) for x in data["links"]],
        )

        return pdata

    @permission(Perms.LIST)
    def get_file_data(self, fid):
        """
        Get complete information about a specific file.

        :param fid: file id
        :return: `FileData`
        """
        info = self.pyload.files.get_file_data(int(fid))
        if not info:
            raise FileDoesNotExists(fid)

        fileinfo = list(info.values())[0]
        fdata = self._convert_py_file(fileinfo)
        return fdata

    @permission(Perms.DELETE)
    def delete_files(self, *args, fids):
        """
        Deletes several file entries from pyload.

        :param fids: list of file ids
        """
        for id in fids.values():
            self.pyload.files.delete_link(int(id))

        self.pyload.files.save()

    @permission(Perms.DELETE)
    def delete_packages(self, **kwargs):
        pids = kwargs['ids'].values()
        """
        Deletes packages and containing links.

        :param pids: list of package ids
        """
        for id in pids:
            self.pyload.files.delete_package(int(id))

        self.pyload.files.save()

    @permission(Perms.LIST)
    def get_queue(self):
        """
        Returns info about queue and packages, **not** about files, see `get_queue_data` \
        or `get_package_data` instead.

        :return: list of `PackageInfo`
        """
        return [
            PackageData(
                pack["id"],
                pack["name"],
                pack["folder"],
                pack["site"],
                pack["password"],
                pack["queue"],
                pack["order"],
                pack["linksdone"],
                pack["sizedone"],
                pack["sizetotal"],
                pack["linkstotal"],
            )
            for pack in self.pyload.files.get_info_data(Destination.QUEUE).values()
        ]

    @permission(Perms.LIST)
    def get_queue_data(self):
        """
        Return complete data about everything in queue, this is very expensive use it
        sparely.
        See `get_queue` for alternative.

        :return: list of `PackageData`
        """
        return [
            PackageData(
                pack["id"],
                pack["name"],
                pack["folder"],
                pack["site"],
                pack["password"],
                pack["queue"],
                pack["order"],
                pack["linksdone"],
                pack["sizedone"],
                pack["sizetotal"],
                links=[self._convert_py_file(x) for x in pack["links"].values()],
            )
            for pack in self.pyload.files.get_complete_data(Destination.QUEUE).values()
        ]

    @permission(Perms.LIST)
    def get_collector(self):
        """
        same as `get_queue` for collector.

        :return: list of `PackageInfo`
        """
        return [
            PackageData(
                pack["id"],
                pack["name"],
                pack["folder"],
                pack["site"],
                pack["password"],
                pack["queue"],
                pack["order"],
                pack["linksdone"],
                pack["sizedone"],
                pack["sizetotal"],
                pack["linkstotal"],
            )
            for pack in self.pyload.files.get_info_data(Destination.COLLECTOR).values()
        ]

    @permission(Perms.LIST)
    def get_collector_data(self):
        """
        same as `get_queue_data` for collector.

        :return: list of `PackageInfo`
        """
        return [
            PackageData(
                pack["id"],
                pack["name"],
                pack["folder"],
                pack["site"],
                pack["password"],
                pack["queue"],
                pack["order"],
                pack["linksdone"],
                pack["sizedone"],
                pack["sizetotal"],
                links=[self._convert_py_file(x) for x in pack["links"].values()],
            )
            for pack in self.pyload.files.get_complete_data(
                Destination.COLLECTOR.value
            ).values()
        ]

    @permission(Perms.ADD)
    def add_files(self, pid, links):
        """
        Adds files to specific package.

        :param pid: package id
        :param links: list of urls
        """
        self.pyload.files.add_links(links, int(pid))

        self.pyload.log.info(
            self._("Added {count:d} links to package #{package:d} ").format(
                count=len(links), package=pid
            )
        )
        self.pyload.files.save()

    @permission(Perms.MODIFY)
    def push_to_queue(self, pid):
        """
        Moves package from Collector to Queue.

        :param pid: package id
        """
        self.pyload.files.set_package_location(pid, Destination.QUEUE)

    @permission(Perms.MODIFY)
    def pull_from_queue(self, pid):
        """
        Moves package from Queue to Collector.

        :param pid: package id
        """
        self.pyload.files.set_package_location(pid, Destination.COLLECTOR)

    @permission(Perms.MODIFY)
    def restart_package(self, **kwargs):
        pid = kwargs['id']
        """
        Restarts a package, resets every containing files.

        :param pid: package id
        """
        self.pyload.files.restart_package(int(pid))

    @permission(Perms.MODIFY)
    def restart_file(self, *args, lid):
        """
        Resets file status, so it will be downloaded again.

        :param lid:  file id
        """
        self.pyload.files.restart_file(int(lid))

    @permission(Perms.MODIFY)
    def recheck_package(self, pid):
        """
        Proofes online status of all files in a package, also a default action when
        package is added.

        :param pid:
        :return:
        """
        self.pyload.files.re_check_package(int(pid))

    @permission(Perms.MODIFY)
    def stop_all_downloads(self):
        """
        Aborts all running downloads.
        """
        pyfiles = list(self.pyload.files.cache.values())
        for pyfile in pyfiles:
            pyfile.abort_download()
            pyfile.notify_change()
        self.pyload.notify_change()

        return True

    @permission(Perms.MODIFY)
    def stop_downloads(self, fids):
        """
        Aborts specific downloads.

        :param fids: list of file ids
        :return:
        """
        pyfiles = self.pyload.files.cache.values()
        for pyfile in pyfiles:
            if pyfile.id in fids:
                pyfile.abort_download()

    @permission(Perms.MODIFY)
    def set_package_name(self, pid, name):
        """
        Renames a package.

        :param pid: package id
        :param name: new package name
        """
        pack = self.pyload.files.get_package(pid)
        pack.name = name
        pack.sync()

    @permission(Perms.MODIFY)
    def move_package(self, destination, pid):
        """
        Set a new package location.

        :param destination: `Destination`
        :param pid: package id
        """
        try:
            dest = Destination(destination)
        except ValueError:
            pass
        else:
            self.pyload.files.set_package_location(pid, dest)

    @permission(Perms.MODIFY)
    def move_files(self, fids, pid):
        """
        Move multiple files to another package.

        :param fids: list of file ids
        :param pid: destination package
        :return:
        """
        # TODO: implement
        pass

    @permission(Perms.ADD)
    def upload_container(self, filename, data):
        """
        Uploads and adds a container file to pyLoad.

        :param filename: filename, extension is important so it can correctly decrypted
        :param data: file content
        """
        with open(
            os.path.join(
                self.pyload.config.get("general", "storage_folder"), "tmp_" + filename
            ),
            "wb",
        ) as th:
            th.write(data)

        self.add_package(th.name, [th.name], Destination.QUEUE.value)

    @permission(Perms.MODIFY)
    def order_package(self, pid, position):
        """
        Gives a package a new position.

        :param pid: package id
        :param position:
        """
        self.pyload.files.reorder_package(pid, position)

    @permission(Perms.MODIFY)
    def order_file(self, fid, position):
        """
        Gives a new position to a file within its package.

        :param fid: file id
        :param position:
        """
        self.pyload.files.reorder_file(fid, position)

    @permission(Perms.MODIFY)
    def set_package_data(self, pid, data):
        """
        Allows to modify several package attributes.

        :param pid: package id
        :param data: dict that maps attribute to desired value
        """
        p = self.pyload.files.get_package(pid)
        if not p:
            raise PackageDoesNotExists(pid)

        for key, value in data.items():
            if key == "id":
                continue
            setattr(p, key, value)

        p.sync()
        self.pyload.files.save()

    @permission(Perms.DELETE)
    def delete_finished(self):
        """
        Deletes all finished files and completly finished packages.

        :return: list of deleted package ids
        """
        return self.pyload.files.delete_finished_links()

    @permission(Perms.MODIFY)
    def restart_failed(self):
        """
        Restarts all failed failes.
        """
        self.pyload.files.restart_failed()

    @permission(Perms.LIST)
    def get_package_order(self, destination):
        """
        Returns information about package order.

        :param destination: `Destination`
        :return: dict mapping order to package id
        """
        packs = self.pyload.files.get_info_data(Destination(destination))
        order = {}

        for pid in packs:
            pack = self.pyload.files.get_package_data(int(pid))
            while pack["order"] in order.keys():  #: just in case
                pack["order"] += 1
            order[pack["order"]] = pack["id"]
        return order

    @permission(Perms.LIST)
    def get_file_order(self, pid):
        """
        Information about file order within package.

        :param pid:
        :return: dict mapping order to file id
        """
        raw_data = self.pyload.files.get_package_data(int(pid))
        order = {}
        for id, pyfile in raw_data["links"].items():
            while pyfile["order"] in order.keys():  #: just in case
                pyfile["order"] += 1
            order[pyfile["order"]] = pyfile["id"]
        return order

    @permission(Perms.STATUS)
    def is_captcha_waiting(self):
        """
        Indicates wether a captcha task is available.

        :return: bool
        """
        self.pyload.last_client_connected = time.time()
        task = self.pyload.captcha_manager.get_task()
        return task is not None

    @permission(Perms.STATUS)
    def get_captcha_task(self, exclusive=False):
        """
        Returns a captcha task.

        :param exclusive: unused
        :return: `CaptchaTask`
        """
        self.pyload.last_client_connected = time.time()
        task = self.pyload.captcha_manager.get_task()
        if task:
            task.set_wating_for_user(exclusive=exclusive)
            data = task.captcha_params_data
            type = task.captcha_format
            result = task.captcha_result_type

            t = CaptchaTask(int(task.id), json.dumps(data), type, result)
            return t
        else:
            return CaptchaTask(-1)

    @permission(Perms.STATUS)
    def get_captcha_task_status(self, tid):
        """
        Get information about captcha task.

        :param tid: task id
        :return: string
        """
        self.pyload.last_client_connected = time.time()
        t = self.pyload.captcha_manager.get_task_by_id(tid)
        return t.get_status() if t else ""

    @permission(Perms.STATUS)
    def set_captcha_result(self, tid, result, cookie_jar=None):
        """
        Set result for a captcha task.

        :param tid: task id
        :param result: captcha result
        :param cookie_jar cookie_jar
        """
        self.pyload.last_client_connected = time.time()
        task = self.pyload.captcha_manager.get_task_by_id(tid)
        if task:
            task.set_result(result, cookie_jar)
            self.pyload.captcha_manager.remove_task(task)

    @permission(Perms.STATUS)
    def get_events(self, uuid):
        """
        Lists occured events, may be affected to changes in future.

        :param uuid:
        :return: list of `Events`
        """
        events = self.pyload.event_manager.get_events(uuid)
        new_events = []

        def conv_dest(d):
            return (Destination.QUEUE if d == "queue" else Destination.COLLECTOR).value

        for e in events:
            event = EventInfo()
            event.eventname = e[0]
            if e[0] in ("update", "remove", "insert"):
                event.id = e[3]
                event.type = (
                    ElementType.PACKAGE if e[2] == "pack" else ElementType.FILE
                ).value
                event.destination = conv_dest(e[1])
            elif e[0] == "order":
                if e[1]:
                    event.id = e[1]
                    event.type = (
                        ElementType.PACKAGE if e[2] == "pack" else ElementType.FILE
                    )
                    event.destination = conv_dest(e[3])
            elif e[0] == "reload":
                event.destination = conv_dest(e[1])
            new_events.append(event)
        return new_events

    @permission(Perms.ACCOUNTS)
    def get_accounts(self, refresh):
        """
        Get information about all entered accounts.

        :param refresh: reload account info
        :return: list of `AccountInfo`
        """
        accs = self.pyload.account_manager.get_account_infos(False, refresh)
        accounts = []
        for group in accs.values():
            accounts.extend(
                [
                    AccountInfo(
                        acc["validuntil"],
                        acc["login"],
                        acc["options"],
                        acc["valid"],
                        acc["trafficleft"],
                        acc["maxtraffic"],
                        acc["premium"],
                        acc["type"],
                    )
                    for acc in group
                ]
            )
        return accounts

    @permission(Perms.ALL)
    def get_account_types(self):
        """
        All available account types.

        :return: list
        """
        return list(self.pyload.account_manager.accounts.keys())

    @permission(Perms.ACCOUNTS)
    def update_account(self, plugin, account, password=None, options={}):
        """
        Changes pw/options for specific account.
        """
        self.pyload.account_manager.update_account(plugin, account, password, options)

    @permission(Perms.ACCOUNTS)
    def remove_account(self, plugin, account):
        """
        Remove account from pyload.

        :param plugin: pluginname
        :param account: accountname
        """
        self.pyload.account_manager.remove_account(plugin, account)

    @permission(Perms.ALL)
    def login(self, username, password):
        """
        Login into pyLoad, this **must** be called when using rpc before any methods can
        be used.

        :param username:
        :param password:
        :param remoteip: Omit this argument, its only used internal
        :return: bool indicating login was successful
        """
        return True if self.check_auth(username, password) else False

    def check_auth(self, username, password):
        """
        Check authentication and returns details.

        :param username:
        :param password:
        :param remoteip:
        :return: dict with info, empty when login is incorrect
        """
        return self.pyload.db.check_auth(username, password)

    def is_authorized(self, func, userdata):
        """
        checks if the user is authorized for specific method.

        :param func: function name
        :param userdata: dictionary of user data
        :return: boolean
        """
        if userdata["role"] == Role.ADMIN:
            return True
        elif func in perm_map and has_permission(
            userdata["permission"], perm_map[func]
        ):
            return True
        else:
            return False

    # TODO: add security permission check
    # remove?
    def get_userdir(self):
        return os.path.realpath(self.pyload.userdir)

    # TODO: add security permission check
    # remove?
    def get_cachedir(self):
        return os.path.realpath(self.pyload.cachedir)

    #: Old API
    @permission(Perms.ALL)
    def getUserData(self, username, password):
        """
        similar to `check_auth` but returns UserData thrift type.
        """
        user = self.check_auth(username, password)
        if user:
            return OldUserData(
                user["name"],
                user["email"],
                user["role"],
                user["permission"],
                user["template"],
            )
        else:
            return OldUserData()

    @permission(Perms.ALL)
    def get_userdata(self, username, password):
        """
        similar to `check_auth` but returns UserData thrift type.
        """
        user = self.check_auth(username, password)
        if user:
            return UserData(
                user["id"],
                user["name"],
                user["email"],
                user["role"],
                user["permission"],
                user["template"],
            )
        else:
            return UserData()

    #: Old API
    def getAllUserData(self):
        """
        returns all known user and info.
        """
        res = {}
        for id, data in self.pyload.db.get_all_user_data().items():
            res[data["name"]] = OldUserData(
                data["name"],
                data["email"],
                data["role"],
                data["permission"],
                data["template"],
            )

        return res

    def get_all_userdata(self):
        """
        returns all known user and info.
        """
        res = {}
        for id, data in self.pyload.db.get_all_user_data().items():
            res[id] = UserData(
                id,
                data["name"],
                data["email"],
                data["role"],
                data["permission"],
                data["template"],
            )
        return res

    @permission(Perms.STATUS)
    def get_services(self):
        """
        A dict of available services, these can be defined by addon plugins.

        :return: dict with this style: {"plugin": {"method": "description"}}
        """
        data = {}
        for plugin, funcs in self.pyload.addon_manager.methods.items():
            data[plugin] = funcs

        return data

    @permission(Perms.STATUS)
    def has_service(self, plugin, func):
        """
        Checks wether a service is available.

        :param plugin:
        :param func:
        :return: bool
        """
        cont = self.pyload.addon_manager.methods
        return plugin in cont and func in cont[plugin]

    @permission(Perms.STATUS)
    def call(self, info):
        """
        Calls a service (a method in addon plugin).

        :param info: `ServiceCall`
        :return: result
        :raises: ServiceDoesNotExists, when its not available
        :raises: ServiceException, when a exception was raised
        """
        plugin = info.plugin
        func = info.func
        args = info.arguments
        parse = info.parse_arguments

        if not self.has_service(plugin, func):
            raise ServiceDoesNotExists(plugin, func)

        try:
            ret = self.pyload.addon_manager.call_rpc(plugin, func, args, parse)
            return str(ret)
        except Exception as exc:
            raise ServiceException(exc)

    @permission(Perms.STATUS)
    def get_all_info(self):
        """
        Returns all information stored by addon plugins. Values are always strings.

        :return: {"plugin": {"name": value } }
        """
        return self.pyload.addon_manager.get_all_info()

    @permission(Perms.STATUS)
    def get_info_by_plugin(self, plugin):
        """
        Returns information stored by a specific plugin.

        :param plugin: pluginname
        :return: dict of attr names mapped to value {"name": value}
        """
        return self.pyload.addon_manager.get_info(plugin)

    def change_password(self, user, oldpw, newpw):
        """
        changes password for specific user.
        """
        return self.pyload.db.change_password(user, oldpw, newpw)

    def set_user_permission(self, user, permission, role):
        self.pyload.db.set_permission(user, permission)
        self.pyload.db.set_role(user, role)

    def addcrypted2(self, *args, api, javascript_key, encrypted, package):
        evaluated_key = self.pyload.eval_js(f"(function () {{ {javascript_key}; return f(); }})()")
        add_crypted2(evaluated_key, api=api, encrypted=encrypted, package=package)

        return 'Success'
