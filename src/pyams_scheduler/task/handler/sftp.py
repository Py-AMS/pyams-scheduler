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

"""PyAMS_scheduler.task.handler.sftp module

This module defines an SFTP directory synchronization handler.
"""

__docformat__ = 'restructuredtext'

import os
from contextlib import contextmanager

from paramiko import AutoAddPolicy, SSHClient

from pyams_scheduler.interfaces.task.sync import IDirectoryHandler, IDirectoryInfo
from pyams_scheduler.task.handler import BaseDirectoryHandler
from pyams_utils.adapter import adapter_config


@adapter_config(name='sftp',
                required=IDirectoryInfo,
                provides=IDirectoryHandler)
class SFTPDirectoryHandler(BaseDirectoryHandler):
    """SFTP directory handler"""

    ssh_client = None
    sftp_client = None

    def connect(self):
        directory_info = IDirectoryInfo(self.context)
        self.ssh_client = SSHClient()
        if directory_info.auto_add_host_key:
            self.ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        self.ssh_client.connect(directory_info.host[1],  # pylint: disable=unsubscriptable-object
                                directory_info.port,
                                directory_info.username,
                                directory_info.password,
                                key_filename=os.path.expanduser(directory_info.private_key)
                                if directory_info.private_key else None)
        self.sftp_client = self.ssh_client.open_sftp()

    def close(self):
        self.ssh_client.close()

    @contextmanager
    def open(self, name, mode='r'):
        file = self.sftp_client.open(self.get_path(name), mode)
        try:
            yield file
        finally:
            file.close()

    def mkdir(self, dirname, mode=0o500):
        self.sftp_client.mkdir(self.get_path(dirname), mode)

    def listdir(self):
        yield from sorted(self.sftp_client.listdir(self.directory))

    def stat(self, name):
        return self.sftp_client.stat(self.get_path(name))

    def set_time(self, name, atime, mtime):
        self.sftp_client.utime(self.get_path(name), times=(atime, mtime))

    def set_mode(self, name, mode=0x400):
        self.sftp_client.chmod(self.get_path(name), mode)

    def unlink(self, name):
        self.sftp_client.unlink(self.get_path(name))
