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

"""PyAMS_scheduler.task.sync module

This module provides main directory synchronization task components.
"""

import fnmatch
import io
import socket
import stat
import sys
import traceback
from contextlib import contextmanager

from persistent import Persistent
from zope.component import queryAdapter
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.interfaces.task import TASK_STATUS_EMPTY, TASK_STATUS_ERROR, \
    TASK_STATUS_FAIL, TASK_STATUS_OK
from pyams_scheduler.interfaces.task.sync import DirectorySyncError, IDirectoryHandler, \
    IDirectoryInfo, IDirectorySyncTask
from pyams_scheduler.task import Task
from pyams_security.interfaces.names import UNCHANGED_PASSWORD
from pyams_utils.factory import factory_config
from pyams_utils.size import get_human_size


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@factory_config(IDirectoryInfo)
class DirectoryInfo(Persistent):
    """Directory info"""

    host = FieldProperty(IDirectoryInfo['host'])
    port = FieldProperty(IDirectoryInfo['port'])
    auto_add_host_key = FieldProperty(IDirectoryInfo['auto_add_host_key'])
    username = FieldProperty(IDirectoryInfo['username'])
    private_key = FieldProperty(IDirectoryInfo['private_key'])
    _password = FieldProperty(IDirectoryInfo['password'])
    directory = FieldProperty(IDirectoryInfo['directory'])

    def __init__(self, data=None):  # pylint: disable=unused-argument
        super().__init__()

    def __repr__(self):
        protocol, hostname = self.host or (None, None)
        if hostname:
            return f'{protocol}://{self.username}@{hostname}:{self.port}{self.directory}'
        return f'{protocol}://{socket.gethostname()}{self.directory}'

    @property
    def password(self):
        """Password getter"""
        return self._password

    @password.setter
    def password(self, value):
        """Password setter"""
        if value == UNCHANGED_PASSWORD:
            return
        self._password = value

    @contextmanager
    def get_handler(self):
        """Get protocol handler"""
        protocol, _hostname = self.host or (None, None)
        if not protocol:
            return None
        handler = queryAdapter(self, IDirectoryHandler, name=protocol)
        if handler is not None:
            try:
                handler.directory = self.directory
                handler.connect()
                yield handler
            finally:
                if handler is not None:
                    handler.close()
        return None


@factory_config(IDirectorySyncTask)
class DirectorySyncTask(Task):
    """Directory synchronization task"""

    label = _("Directory synchronization")
    icon_class = 'fas fa-sync-alt'

    source = FieldProperty(IDirectorySyncTask['source'])
    filter = FieldProperty(IDirectorySyncTask['filter'])
    recursive = FieldProperty(IDirectorySyncTask['recursive'])
    follow_symlinks = FieldProperty(IDirectorySyncTask['follow_symlinks'])
    ignore_read_errors = FieldProperty(IDirectorySyncTask['ignore_read_errors'])
    use_datetime = FieldProperty(IDirectorySyncTask['use_datetime'])
    delete_source = FieldProperty(IDirectorySyncTask['delete_source'])
    ignore_delete_errors = FieldProperty(IDirectorySyncTask['ignore_delete_errors'])
    target = FieldProperty(IDirectorySyncTask['target'])
    ignore_write_errors = FieldProperty(IDirectorySyncTask['ignore_write_errors'])

    def run(self, report, **kwargs):  # pylint: disable=unused-argument,too-many-statements

        copied = {
            'files': [],  # list of copied files
            'size': 0
        }

        def copy_file(src, dst, name, src_stat):
            """Copy a single file from source to destination"""
            size = 0
            try:
                with src.open(name, 'rb') as src_file:
                    try:
                        with dst.open(name, 'wb') as dst_file:
                            data = src_file.read(io.DEFAULT_BUFFER_SIZE)
                            while data:
                                size += len(data)
                                dst_file.write(data)
                                data = src_file.read(io.DEFAULT_BUFFER_SIZE)
                        if self.use_datetime:
                            dst.set_time(name, src_stat.st_atime, src_stat.st_mtime)
                        dst.set_mode(name, src_stat.st_mode)
                        report.writeln(f'     * {src.directory}: {name} ({get_human_size(size)})')
                        copied['files'].append((src.directory, name))
                        copied['size'] += size
                    except PermissionError:
                        if not self.ignore_write_errors:
                            raise
                        report.writeln(f'   + {src.directory}: **{name}** (WRITE ERROR)')
            except PermissionError:
                if not self.ignore_read_errors:
                    raise
                report.writeln(f'   + {src.directory}: **{name}** (READ ERROR)')

        def synchronize_files(src, dst):  # pylint: disable=too-many-branches,too-many-statements
            """Synchronize source directory and destination"""
            for name in src.listdir():
                try:
                    src_stat = src.stat(name)
                except (DirectorySyncError, PermissionError, FileNotFoundError):
                    report.writeln(f'   + {src.directory}: **{name}** (SRC STAT ERROR)')
                    if not self.ignore_read_errors:
                        raise
                    continue
                dst_stat = None
                # check for symbolic link
                is_src_link = stat.S_ISLNK(src_stat.st_mode)
                if is_src_link and not self.follow_symlinks:
                    continue
                # check for directory
                is_src_dir = stat.S_ISDIR(src_stat.st_mode)
                try:
                    dst_stat = dst.stat(name)
                except (DirectorySyncError, PermissionError):
                    report.writeln(f'   + {src.directory}: **{name}** (DST STAT ERROR)')
                    if not self.ignore_write_errors:
                        raise
                    continue
                except FileNotFoundError:
                    if is_src_dir and self.recursive:
                        try:
                            dst.mkdir(name, src_stat.st_mode)
                        except (DirectorySyncError, PermissionError):
                            report.writeln(f'   + {src.directory}: **{name}** (CREATE ERROR)')
                            if not self.ignore_write_errors:
                                raise
                            continue

                if is_src_dir:
                    # recursive directory synchronization
                    if self.recursive:
                        try:
                            with src.chdir(name):
                                try:
                                    with dst.chdir(name):
                                        synchronize_files(src, dst)
                                except (DirectorySyncError, PermissionError):
                                    report.writeln(f'   + {src.directory}: **{name}** (SYNC ERROR)')
                                    if not self.ignore_write_errors:
                                        raise
                                    continue
                        except (DirectorySyncError, PermissionError):
                            report.writeln(f'   + {src.directory}: **{name}** (READ ERROR)')
                            if not self.ignore_read_errors:
                                raise
                            continue
                else:
                    # check filter
                    if self.filter and not fnmatch.fnmatch(name, self.filter):
                        continue
                    # regular file copy
                    if (dst_stat is None) or \
                            (not self.use_datetime) or \
                            (src_stat.st_mtime > dst_stat.st_mtime) or \
                            (src_stat.st_size != dst_stat.st_size):
                        try:
                            copy_file(src, dst, name, src_stat)
                        except (DirectorySyncError, PermissionError):
                            report.writeln(f'   + {src.directory}: **{name}** (WRITE ERROR)')
                            if not self.ignore_write_errors:
                                raise
                            continue
                    else:
                        report.writeln(f'   + {src.directory}: {name} (unchanged)')
                    if self.delete_source:
                        try:
                            src.unlink(name)
                        except (DirectorySyncError, PermissionError):
                            report.writeln(f'   + {src.directory}: **{name}** (DELETE ERROR)')
                            if not self.ignore_delete_errors:
                                raise
                            continue

        try:
            report.writeln(f'Directories synchronization output', prefix='### ')
            report.writeln(f' - source: {self.source!r}')
            report.writeln(f' - target: {self.target!r}')
            report.writeln(f' - copied files:')
            with self.source.get_handler() as source:
                with self.target.get_handler() as target:
                    synchronize_files(source, target)
            if copied['files']:
                report.writeln(f"   >> {len(copied['files'])} files ({get_human_size(copied['size'])}) copied")
            else:
                report.writeln('   >> no copied file')
            return (TASK_STATUS_OK, copied) if copied['files'] else (TASK_STATUS_EMPTY, None)

        except:  # pylint: disable=bare-except
            report.writeln('**An SQL error occurred**', suffix='\n')
            report.write_exception(*sys.exc_info())
            return TASK_STATUS_FAIL, None
