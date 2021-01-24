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

"""PyAMS_scheduler.task.handler base module

This module defines base directory handler class.
"""

__docformat__ = 'restructuredtext'

import os
from contextlib import contextmanager

from zope.interface import implementer

from pyams_scheduler.interfaces.task.sync import IDirectoryHandler
from pyams_utils.adapter import ContextAdapter


@implementer(IDirectoryHandler)
class BaseDirectoryHandler(ContextAdapter):
    """Base directory handler"""

    directory = None

    def connect(self):
        """Open connection"""

    def close(self):
        """Close handler connection"""

    def get_path(self, name):
        """Get full path for given name"""
        if name.startswith(os.path.sep):
            return name
        return os.path.join(self.directory, name)

    @contextmanager
    def chdir(self, dirname):
        """Change current directory"""
        old_directory = self.directory
        try:
            self.directory = self.get_path(dirname)
            yield
        finally:
            self.directory = old_directory

    @contextmanager
    def open(self, name, mode='r'):
        """Open file"""

    def mkdir(self, dirname, mode=0o500):
        """Create new directory"""

    def listdir(self):
        """List current directory content"""

    def stat(self, name):
        """Get stats about given file name"""

    def set_time(self, name, atime, mtime):
        """Set atime and mtime of given file name"""

    def set_mode(self, name, mode=0x400):
        """Set mode of given file name"""

    def unlink(self, name):
        """Delete given file name"""
