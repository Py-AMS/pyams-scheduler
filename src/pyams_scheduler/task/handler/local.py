#
# Copyright (c) 2015-2021 Thierry Florac <tflorac AT ulthar.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

"""PyAMS_scheduler.task.handler.local module

"""

__docformat__ = 'restructuredtext'

import os
from contextlib import contextmanager

from pyams_scheduler.interfaces.task.sync import IDirectoryHandler, IDirectoryInfo
from pyams_scheduler.task.handler import BaseDirectoryHandler
from pyams_utils.adapter import adapter_config


@adapter_config(name='local',
                required=IDirectoryInfo,
                provides=IDirectoryHandler)
class LocalDirectoryHandler(BaseDirectoryHandler):
    """Local directory handler"""

    @contextmanager
    def open(self, name, mode='r'):
        file = open(self.get_path(name), mode)
        try:
            yield file
        finally:
            file.close()

    def mkdir(self, dirname, mode=0o500):
        os.mkdir(self.get_path(dirname), mode)

    def listdir(self):
        yield from sorted(os.listdir(self.directory))

    def stat(self, name):
        return os.stat(self.get_path(name))

    def set_time(self, name, atime, mtime):
        os.utime(self.get_path(name), times=(atime, mtime))

    def set_mode(self, name, mode=0x400):
        os.chmod(self.get_path(name), mode)

    def unlink(self, name):
        os.unlink(self.get_path(name))
