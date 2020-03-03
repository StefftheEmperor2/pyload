# -*- coding: utf-8 -*-
# AUTHOR: RaNaN, mkaay


from ..managers.event_manager import UpdateEvent, CoreEvent
from ..utils.old import safepath


class PyPackage:
    """
    Represents a package object at runtime.
    """

    def __init__(self, manager, id, name, folder, site, password, queue, order):
        self.m = self.manager = manager
        self.m.package_cache[int(id)] = self

        self.id = int(id)
        self.name = name
        self._folder = folder
        self.site = site
        self.password = password
        self.queue = queue
        self.order = order
        self.set_finished = False

    @property
    def folder(self):
        return safepath(self._folder)

    def to_dict(self):
        """
        Returns a dictionary representation of the data.

        :return: dict: {id: { attr: value }}
        """
        return {
            self.id: {
                "id": self.id,
                "name": self.name,
                "folder": self.folder,
                "site": self.site,
                "password": self.password,
                "queue": self.queue,
                "order": self.order,
                "links": {},
            }
        }

    def get_children(self):
        """
        get information about contained links.
        """
        return self.m.get_package_data(self.id)["links"]

    def sync(self):
        """
        sync with db.
        """
        self.m.update_package(self)

    def release(self):
        """
        sync and delete from cache.
        """
        self.sync()
        self.m.release_package(self.id)

    def delete(self):
        self.m.delete_package(self.id)

    def notify_change(self):
        e = UpdateEvent("pack", self.id, "collector" if not self.queue else "queue")
        self.m.pyload.event_manager.add_event(e)

        self.m.pyload.notify_change()

    def __setattr__(self, key, value):
        if key == "folder":
            self._folder = value
        else:
            super(PyPackage, self).__setattr__(key, value)

    def get_progress(self):
        total = 0
        progress = 0
        for file_id in self.get_children():
            file = self.manager.get_file(file_id)
            total += file.maxprogress
            if file.is_finished():
                file_progress = file.maxprogress
            else:
                file_progress = file.progress
            progress += file_progress
        return (progress / total) * 100

    def get_downloaded_files(self):
        downloaded_files = 0
        for file_id in self.get_children():
            file = self.manager.get_file(file_id)
            if file.is_finished():
                downloaded_files += 1
        return downloaded_files

    def get_total_size(self):
        total_size = 0
        for file_id in self.get_children():
            file = self.manager.get_file(file_id)
            total_size += file.get_size()
        return total_size

    def get_downloaded_size(self):
        downloaded_size = 0
        for file_id in self.get_children():
            file = self.manager.get_file(file_id)
            downloaded_size += file.get_downloaded_size()
        return downloaded_size

    def get_json(self):
        return {
            "id": self.id,
            "progress": self.get_progress(),
            "total_files": len(self.get_children()),
            "finished_files": self.get_downloaded_files(),
            "total_size": self.get_total_size(),
            "downloaded_size": self.get_downloaded_size()
        }
