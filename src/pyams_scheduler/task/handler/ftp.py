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

"""PyAMS_scheduler.task.handler.ftp module

This module a directory synchronization handler  using FTP protocol.
"""

import os
import stat
import time
from contextlib import contextmanager
from ftplib import Error, FTP
from tempfile import SpooledTemporaryFile
from time import mktime

from pyams_scheduler.interfaces.task.sync import DirectoryReadError, DirectoryWriteError, \
    IDirectoryHandler, \
    IDirectoryInfo
from pyams_scheduler.task.handler import BaseDirectoryHandler
from pyams_utils.adapter import adapter_config


__docformat__ = 'restructuredtext'


class FTPHelper:
    """Base FTP helper class"""

    def __init__(self, ftp, name, mode):
        self.ftp = ftp
        self.name = name
        self.mode = mode
        self.file = SpooledTemporaryFile(64 * 1024)

    def close(self):
        """Close temporary file"""
        self.file.close()


class FTPReader(FTPHelper):
    """FTP reader helper class"""

    def __init__(self, ftp, name, mode):
        super().__init__(ftp, name, mode)
        try:
            self.ftp.ftp_client.retrbinary('RETR {}'.format(self.ftp.get_path(self.name)),
                                           self.file.write)
        except Error as exc:
            raise DirectoryReadError from exc
        self.file.seek(0)

    def read(self, bufsize):
        """Read data from source"""
        return self.file.read(bufsize)


class FTPWriter(FTPHelper):
    """FTP writer helper class"""

    def write(self, data):
        """Write data to target"""
        self.file.write(data)

    def close(self):
        self.file.seek(0)
        try:
            self.ftp.ftp_client.storbinary('STOR {}'.format(self.ftp.get_path(self.name)),
                                           self.file)
        except Error as exc:
            raise DirectoryWriteError from exc
        self.file.close()


@adapter_config(name='ftp',
                required=IDirectoryInfo,
                provides=IDirectoryHandler)
class FTPDirectoryHandler(BaseDirectoryHandler):
    """FTP directory handler"""

    ftp_client = None

    def connect(self):
        directory_info = IDirectoryInfo(self.context)
        self.ftp_client = FTP()
        self.ftp_client.connect(directory_info.host[1],  # pylint: disable=unsubscriptable-object
                                directory_info.port)
        if directory_info.username:
            self.ftp_client.login(directory_info.username, directory_info.password)

    def close(self):
        self.ftp_client.quit()

    @contextmanager
    def open(self, name, mode='r'):
        if mode.startswith('r'):
            helper = FTPReader(self, self.get_path(name), mode)
        else:
            helper = FTPWriter(self, self.get_path(name), name)
        try:
            yield helper
        finally:
            helper.close()

    def mkdir(self, dirname, mode=0o500):
        self.ftp_client.mkd(self.get_path(dirname))

    def listdir(self):
        yield from sorted(filter(lambda name: name not in ('.', '..'),
                                 self.ftp_client.nlst(self.directory)))

    @staticmethod
    def get_mode(value):
        """File mode converter"""
        mode = 0
        flags = (stat.S_IFDIR,
                 stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR,
                 stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP,
                 stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH)
        for idx, flag in enumerate(value):
            if flag != '-':
                mode |= flags[idx]
        return mode

    def stat(self, name):  # pylint: disable=too-many-locals
        # get mode
        mode = 0
        entries = []
        try:
            self.ftp_client.retrlines('LIST {}'.format(self.get_path(name)),
                                      entries.append)
        except Error as ex:
            raise FileNotFoundError(name) from ex
        if len(entries) == 1:
            mode, ignore, user, group, size, month, day, year, name = entries[0].split()  # pylint: disable=unused-variable
            mode = self.get_mode(mode)
        else:
            for entry in entries:
                mode, ignore, user, group, size, month, day, year, name = entry.split()  # pylint: disable=unused-variable
                if name == '.':
                    mode = self.get_mode(mode)
                    break
        # get size
        try:
            size = self.ftp_client.size(self.get_path(name))
        except:  # pylint: disable=bare-except
            size = 0
        # get time
        try:
            _ret, mdtm = self.ftp_client.voidcmd('MDTM {}'.format(self.get_path(name))).split()
            mtime = round(mktime(time.strptime(mdtm, '%Y%m%d%H%M%S')))
        except:  # pylint: disable=bare-except
            mtime = 0
        return os.stat_result((
            mode,   # st_mode
            0,      # st_ino
            0,      # st_dev
            0,      # st_nlink
            0,      # st_uid
            0,      # st_gid
            size,   # st_size
            mtime,  # st_atime
            mtime,  # st_mtime
            mtime   # st_ctime
        ))

    def set_time(self, name, atime, mtime):
        pass

    def set_mode(self, name, mode=0x400):
        pass

    def unlink(self, name):
        self.ftp_client.delete(self.get_path(name))
