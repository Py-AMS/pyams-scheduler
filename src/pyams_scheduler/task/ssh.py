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

"""PyAMS_scheduler.task.ssh module

This module defines a scheduler task which can be used to run local or
remote commands.
"""

import os
import subprocess
import sys
import traceback
from contextlib import contextmanager
from socket import gethostname

from paramiko import AutoAddPolicy, SSHClient, SSHException
from persistent import Persistent
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.interfaces.task import TASK_STATUS_ERROR, TASK_STATUS_OK
from pyams_scheduler.interfaces.task.ssh import ISSHCallerTask, ISSHConnectionInfo
from pyams_scheduler.task import Task
from pyams_utils.factory import factory_config


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@factory_config(ISSHConnectionInfo)
class SSHConnectionInfo(Persistent):
    """SFTP base info"""

    hostname = FieldProperty(ISSHConnectionInfo['hostname'])
    auto_add_host_key = FieldProperty(ISSHConnectionInfo['auto_add_host_key'])
    port = FieldProperty(ISSHConnectionInfo['port'])
    username = FieldProperty(ISSHConnectionInfo['username'])
    private_key = FieldProperty(ISSHConnectionInfo['private_key'])
    _password = FieldProperty(ISSHConnectionInfo['password'])

    def __init__(self, data=None):  # pylint: disable=unused-argument
        super().__init__()

    def __bool__(self):
        return bool(self.hostname)

    def __repr__(self):
        if self.hostname:
            return '{}@{}:{}'.format(self.username, self.hostname, self.port)
        return gethostname()

    @property
    def password(self):
        """Password getter"""
        return self._password

    @password.setter
    def password(self, value):
        """Password setter"""
        if value == '*****':
            return
        self._password = value

    @contextmanager
    def get_connection(self):
        """Open SSH connection"""
        ssh = SSHClient()
        try:
            if self.auto_add_host_key:
                ssh.set_missing_host_key_policy(AutoAddPolicy())
            ssh.connect(self.hostname, self.port, self.username, self.password,
                        key_filename=os.path.expanduser(self.private_key)
                        if self.private_key else None)
            yield ssh
        finally:
            ssh.close()

    @contextmanager
    def get_sftp_client(self):
        """Get SFTP client"""
        with self.get_connection() as ssh_client:
            try:
                yield ssh_client.open_sftp()
            finally:
                ssh_client.close()


@factory_config(ISSHCallerTask)
class SSHCallerTask(Task):
    """SSH command caller task"""

    label = _("Command line")
    icon_class = 'fas fa-terminal'

    connection = FieldProperty(ISSHCallerTask['connection'])
    cmdline = FieldProperty(ISSHCallerTask['cmdline'])
    ok_status = FieldProperty(ISSHCallerTask['ok_status'])

    @property
    def ok_status_list(self):
        """OK exit codes list getter"""
        return map(int, self.ok_status.split(','))

    def run(self, report, **kwargs):  # pylint: disable=unused-argument
        report.write('Shell command output\n'
                     '====================\n'
                     'Shell command: \n    {!r}: {}\n\n'.format(self.connection, self.cmdline))
        if self.connection:
            return self._run_remote(report, **kwargs)
        return self._run_local(report, **kwargs)

    def _run_remote(self, report, **kwargs):  # pylint: disable=unused-argument
        """Run remote SSH command"""
        try:
            with self.connection.get_connection() as ssh_client:
                stdin, stdout, stderr = ssh_client.exec_command(self.cmdline)
                stdin.close()
                report.write(stdout.read().decode())
                errors = stderr.read()
                if errors:
                    report.write('\n\n'
                                 'Some errors occurred\n'
                                 '====================\n')
                    report.write(errors.decode())
                return (
                    TASK_STATUS_OK if stdout.channel.exit_status in self.ok_status_list
                        else stdout.channel.exit_status,
                    stdout
                )
        except SSHException:
            etype, value, tb = sys.exc_info()  # pylint: disable=invalid-name
            report.write('\n\n'
                         'An SSH error occurred\n'
                         '=====================\n')
            report.write(''.join(traceback.format_exception(etype, value, tb)))
            return TASK_STATUS_ERROR, None

    def _run_local(self, report, **kwargs):  # pylint: disable=unused-argument
        """Run local system command"""
        shell = subprocess.Popen(self.cmdline, shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        stdout, stderr = shell.communicate()
        report.write(stdout.decode())
        if stderr:
            report.write('\n\n'
                         'Some errors occurred\n'
                         '====================\n')
            report.write(stderr.decode())
        return (
            TASK_STATUS_OK if shell.returncode in self.ok_status_list else shell.returncode,
            stdout
        )
