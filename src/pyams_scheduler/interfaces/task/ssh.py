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

"""PyAMS_scheduler.interfaces.task.ssh module

This module defines interface of SSH caller task.
"""

from zope.interface import Interface, Invalid, invariant
from zope.schema import Bool, Int, Object, Password, TextLine

from pyams_scheduler.interfaces import ITask


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


class ISSHConnectionInfo(Interface):
    """SSH connection info interface"""

    hostname = TextLine(title=_("Hostname or IP address"),
                        description=_("Enter hostname or IP address of a remote host; "
                                      "keep empty for local server host"),
                        required=False)

    auto_add_host_key = Bool(title=_("Automatically add host key?"),
                             description=_("If 'yes', connection will be opened event if "
                                           "server key is unknown"),
                             required=False,
                             default=False)

    port = Int(title=_("Port number"),
               default=22,
               required=False)

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

    @invariant
    def check_remote_host(self):
        """Check for password or private key if remote host is defined"""
        if self.hostname and (bool(self.private_key) == bool(self.password)):
            raise Invalid(_("You must provide a private key filename OR a password when "
                            "defining remote tasks"))

    def get_connection(self):
        """Get SSH connection"""

    def get_sftp_client(self):
        """Get SFTP client"""


class ISSHCallTaskInfo(Interface):
    """SSH caller task info"""

    connection = Object(title=_("SSH connection"),
                        schema=ISSHConnectionInfo,
                        required=True)

    cmdline = TextLine(title=_("Command line"),
                       description=_("Enter command line, using absolute path names"),
                       required=True)

    ok_status = TextLine(title=_("OK status"),
                         description=_("Comma-separated list of command exit codes which "
                                       "should be considered as success"),
                         required=True,
                         default='0')


class ISSHCallerTask(ITask, ISSHCallTaskInfo):
    """SSH caller interface"""
