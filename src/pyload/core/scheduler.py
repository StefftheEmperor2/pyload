# -*- coding: utf-8 -*-
# AUTHOR: mkaay

import time
from heapq import heappop, heappush
from threading import Lock

from _thread import start_new_thread

from .utils.old import lock


class AlreadyCalled(Exception):
    pass


class Deferred:
    def __init__(self):
        self.call = []
        self.result = ()
        self._is_done = False

    def add_callback(self, f, *cargs, **ckwargs):
        self.call.append((f, cargs, ckwargs))

    def callback(self, *args, **kwargs):
        if self.result:
            raise AlreadyCalled
        self.result = (args, kwargs)
        for f, cargs, ckwargs in self.call:
            args += tuple(cargs)
            kwargs.update(ckwargs)
            f(*args, **kwargs)

    def wait(self):
        while not self.is_done:
            time.sleep(0.1)

    def set_is_done(self):
        self._is_done = True

    @property
    def is_done(self):
        return self._is_done


class Scheduler:
    def __init__(self, core):
        self.pyload = core
        self._ = core._
        self.queue = PriorityQueue()

    def add_job(self, t, call, args=[], kwargs={}, threaded=True, deferred=None):
        if deferred is None:
            deferred = Deferred()

        t += time.time()
        j = Job(t, call, args, kwargs, deferred, threaded)
        self.queue.put((t, j))
        return deferred

    def get_deferred(self):
        return Deferred()

    def remove_job(self, d):
        """
        :param d: defered object
        :return: if job was deleted
        """
        index = -1

        for i, j in enumerate(self.queue):
            if j[1].deferred == d:
                index = i

        if index >= 0:
            del self.queue[index]
            return True

        return False

    def run(self):
        while True:
            t, j = self.queue.get()
            if not j:
                break
            else:
                if t <= time.time():
                    j.start()
                else:
                    self.queue.put((t, j))
                    break


class Job:
    def __init__(self, time, call, args=[], kwargs={}, deferred=None, threaded=True):
        self.time = float(time)
        self.call = call
        self.args = args
        self.kwargs = kwargs
        self.deferred = deferred
        self.threaded = threaded

    def run(self):
        ret = self.call(*self.args, **self.kwargs)
        if self.deferred is None:
            return
        else:
            self.deferred.callback(ret)
            self.deferred.set_is_done()

    def start(self):
        if self.threaded:
            start_new_thread(self.run, ())
        else:
            self.run()


class PriorityQueue:
    """
    a non blocking priority queue.
    """

    def __init__(self):
        self.queue = []
        self.lock = Lock()

    def __iter__(self):
        return iter(self.queue)

    def __delitem__(self, key):
        del self.queue[key]

    @lock
    def put(self, element):
        heappush(self.queue, element)

    @lock
    def get(self):
        """
        return element or None.
        """
        try:
            el = heappop(self.queue)
            return el
        except IndexError:
            return None, None
