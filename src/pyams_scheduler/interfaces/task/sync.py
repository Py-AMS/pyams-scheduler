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

"""PyAMS_scheduler.interfaces.task.handler module

This module defines interfaces used by file handlers.
"""

__docformat__ = 'restructuredtext'

from zope.interface import Attribute, Interface, Invalid, implementer, invariant
from zope.schema import Bool, Int, Object, Password, TextLine, Tuple
from zope.schema.interfaces import ITuple
from pyams_scheduler.interfaces import ITask

from pyams_scheduler import _


class IDirectoryHandlerHostField(ITuple):
    """Handler host field marker interface"""


@implementer(IDirectoryHandlerHostField)
class DirectoryHandlerHostField(Tuple):
    """Directory handler host field

    This schema field is made of two elements which are the protocol
    (file, ftp, sftp...) and the host (which can be None for local files
    handlers).
    """

    def __init__(self, **kwargs):
        super().__init__(value_type=TextLine(),
                         min_length=2,
                         max_length=2,
                         **kwargs)


class IDirectoryHandler(Interface):
    """Directory handler interface

    This interface tries to mimic the *os* package files interfaces
    required to handle directory synchronization.
    """

    directory = Attribute("Current directory")

    def connect(self):
        """Open connection if required"""

    def close(self):
        """Close handler connection"""

    def open(self, name, mode='r'):
        """Open file

        This method may be a context manager so that connection will
        be closed automatically on exit.
        """

    def chdir(self, dirname):
        """Change current directory

        This method may be a context manager, so that previous directory
        is automatically restored on exit.
        """

    def mkdir(self, dirname):
        """Create new directory"""

    def listdir(self):
        """List current directory content"""

    def stat(self, name):
        """Get stats about given file name"""

    def set_time(self, name, atime, mtime):
        """Set atime and mtime of given file name"""

    def set_mode(self, name, mode=0x777):
        """Set mode of given file name"""

    def unlink(self, name):
        """Delete given file name"""


class IDirectoryInfo(Interface):
    """Synchronization task connection information"""

    host = DirectoryHandlerHostField(title=_("Host"),
                                     description=_("Protocol and host name"),
                                     required=True)

    port = Int(title=_("Port number"),
               description=_("Port number is required for remote protocols like SFTP or FTP"),
               default=22,
               required=False)

    auto_add_host_key = Bool(title=_("Automatically add host key?"),
                             description=_("If 'yes', an SSH connection will be accepted "
                                           "even if server key is unknown"),
                             required=False,
                             default=False)

    username = TextLine(title=_("User name"),
                        required=False)

    private_key = TextLine(title=_("Private key filename"),
                           description=_("Enter name of private key file; use '~' to identify "
                                         "running server user home directory, as in "
                                         "~/.ssh/id_rsa"),
                           required=False)

    password = Password(title=_("Password"),
                        description=_("If not using private key, you must provide user's "
                                      "password"),
                        required=False)

    directory = TextLine(title=_("Directory name"),
                         description=_("Enter absolute directory name"),
                         required=True)

    @invariant
    def check_remote_host(self):
        """Check for password or private key if remote host is defined"""
        if self.host and self.host[1] and (bool(self.private_key) == bool(self.password)):  # pylint: disable=unsubscriptable-object
            raise Invalid(_("You must provide a private key filename OR a password when "
                            "defining remote tasks"))

    def get_handler(self):
        """Get handler matching this directory"""


class IDirectorySyncTaskInfo(Interface):
    """Directory synchronization task info"""

    source = Object(title=_("Source directory"),
                    schema=IDirectoryInfo,
                    required=True)

    filter = TextLine(title=_("Files names filter"),
                      description=_("Filter used to select only a subset of directory "
                                    "contents"),
                      required=False,
                      default='*')

    recursive = Bool(title=_("Recursive copy?"),
                     description=_("If 'yes', sub-directories will also be synchronized"),
                     required=False,
                     default=True)

    follow_symlinks = Bool(title=_("Follow symbolic links?"),
                           description=_("If 'yes', symbolic links targets will be copied as "
                                         "normal files; be warmed that symbolic links can be "
                                         "seen as regular files while using an SFTP source!"),
                           required=False,
                           default=False)

    ignore_read_errors = Bool(title=_("Ignore read errors?"),
                              description=_("If 'yes', source files which can't be opened "
                                            "will just be ignored; otherwise, read errors "
                                            "will stop the synchronization"),
                              required=False,
                              default=False)

    use_datetime = Bool(title=_("Use datetime?"),
                        description=_("If 'yes', last modification time will be used to "
                                      "compare files between source and target, and last "
                                      "modification date will be restored on target after copy"),
                        required=False,
                        default=True)

    delete_source = Bool(title=_("Delete source after copy"),
                         description=_("If 'yes', source directory will be cleared after a "
                                       "successful synchronization"),
                         required=False,
                         default=False)

    ignore_delete_errors = Bool(title=_("Ignore delete errors?"),
                                description=_("If 'yes', source files which can't be deleted "
                                              "after copy will just be ignored; otherwise, "
                                              "delete errors will stop the synchronization"),
                                required=False,
                                default=False)

    target = Object(title=_("Target directory"),
                    schema=IDirectoryInfo,
                    required=True)

    ignore_write_errors = Bool(title=_("Ignore write errors?"),
                               description=_("If 'yes', target files which can't be opened "
                                             "will just be ignored; otherwise, write errors "
                                             "will stop the synchronization"),
                               required=False,
                               default=False)


class IDirectorySyncTask(ITask, IDirectorySyncTaskInfo):
    """Directory synchronization task interface"""


class DirectorySyncError(Exception):
    """Base directory synchronization error"""


class DirectoryReadError(DirectorySyncError):
    """Directory read error"""


class DirectoryWriteError(DirectorySyncError):
    """Directory write error"""
