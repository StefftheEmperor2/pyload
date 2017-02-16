# -*- coding: utf-8 -*-
#@author: RaNaN

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import int
from time import time

from future import standard_library

from pyload.api import InteractionTask as BaseInteractionTask
from pyload.api import InputType

standard_library.install_aliases()


# noinspection PyUnresolvedReferences
class InteractionTask(BaseInteractionTask):
    """
    General Interaction Task extends ITask defined by api with additional fields and methods.
    """

    #: Plugins can put needed data here
    storage = None
    #: Timestamp when task expires
    wait_until = 0
    #: The received result
    result = None
    #: List of registered handles
    handler = None
    #: Error Message
    error = None
    #: Timeout locked
    locked = False
    #: A task that was retrieved counts as seen
    seen = False
    #: A task that is relevant to every user
    shared = False
    #: primary uid of the owner
    owner = None

    def __init__(self, *args, **kwargs):
        if 'owner' in kwargs:
            self.owner = kwargs['owner']
            del kwargs['owner']
        if 'shared' in kwargs:
            self.shared = kwargs['shared']
            del kwargs['shared']

        BaseInteractionTask.__init__(self, *args, **kwargs)

        # additional internal attributes
        self.storage = {}
        self.handler = []
        self.wait_until = 0

    def convert_result(self, value):
        if self.input.type == InputType.Click:
            parts = value.split(',')
            return int(parts[0]), int(parts[1])

        # TODO: convert based on input/output
        return value

    def get_result(self):
        return self.result

    def set_shared(self):
        """
        Enable shared mode, should not be reversed.
        """
        self.shared = True

    def set_result(self, value):
        self.result = self.convert_result(value)

    def set_waiting(self, sec, lock=False):
        """
        Sets waiting in seconds from now, < 0 can be used as infinitive.
        """
        if not self.locked:
            if sec < 0:
                self.wait_until = -1
            else:
                self.wait_until = max(time() + sec, self.wait_until)

            if lock:
                self.locked = True

    def is_waiting(self):
        if self.result or self.error or self.timed_out():
            return False

        return True

    def timed_out(self):
        return time() > self.wait_until > -1

    def correct(self):
        [x.task_correct(self) for x in self.handler]

    def invalid(self):
        [x.task_invalid(self) for x in self.handler]
