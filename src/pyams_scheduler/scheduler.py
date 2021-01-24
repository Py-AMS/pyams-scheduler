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

"""PyAMS_scheduler.scheduler module

This module defines the main persistent scheduler utility class.
"""

__docformat__ = 'restructuredtext'

from zope.container.folder import Folder
from zope.interface import implementer
from zope.intid import IIntIds
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.interfaces import IScheduler, ISchedulerHandler, ISchedulerRoles, \
    SCHEDULER_AUTH_KEY, SCHEDULER_HANDLER_KEY
from pyams_security.interfaces import IDefaultProtectionPolicy, IRolesPolicy
from pyams_security.property import RolePrincipalsFieldProperty
from pyams_security.security import ProtectedObjectMixin, ProtectedObjectRoles
from pyams_utils.adapter import ContextAdapter, adapter_config
from pyams_utils.registry import get_pyramid_registry, query_utility
from pyams_zmq.socket import zmq_response, zmq_socket


@implementer(ISchedulerHandler)
class SchedulerHandler:
    """Scheduler handler utility

    This is just a 'marker' utility which is used to mark nodes in a cluster
    which should run the scheduler
    """


@implementer(IScheduler, IDefaultProtectionPolicy)
class Scheduler(ProtectedObjectMixin, Folder):
    """Scheduler utility"""

    zodb_name = FieldProperty(IScheduler['zodb_name'])
    report_mailer = FieldProperty(IScheduler['report_mailer'])
    report_source = FieldProperty(IScheduler['report_source'])

    @property
    def tasks(self):
        """Scheduler tasks getter"""
        yield from self.values()

    @property
    def history(self):
        """Scheduler full history getter"""
        result = []
        for task in self.values():
            result.extend(task.history)
        result.sort(key=lambda x: x.date)
        return result

    @property
    def internal_id(self):
        """Scheduler internal ID"""
        intids = query_utility(IIntIds)
        if intids is not None:
            return intids.register(self)
        return None

    @staticmethod
    def get_socket():
        """Open ØMQ socket"""
        registry = get_pyramid_registry()
        handler = registry.settings.get(SCHEDULER_HANDLER_KEY, False)
        if handler:
            return zmq_socket(handler, auth=registry.settings.get(SCHEDULER_AUTH_KEY))
        return None

    @staticmethod
    def get_task(task_id):
        """Get task matching given ID"""
        intids = query_utility(IIntIds)
        if intids is not None:
            return intids.queryObject(task_id)
        return None

    def get_jobs(self):
        """Getter of scheduler scheduled jobs"""
        socket = self.get_socket()
        if socket is None:
            return [501, "No socket handler defined in configuration file"]
        socket.send_json(['get_jobs', {}])
        return zmq_response(socket)

    def test_process(self):
        """Send test request to scheduler process"""
        socket = self.get_socket()
        if socket is None:
            return [501, "No socket handler defined in configuration file"]
        socket.send_json(['test', {}])
        return zmq_response(socket)


@implementer(ISchedulerRoles)
class SchedulerRoles(ProtectedObjectRoles):
    """Scheduler roles"""

    scheduler_managers = RolePrincipalsFieldProperty(ISchedulerRoles['scheduler_managers'])

    tasks_managers = RolePrincipalsFieldProperty(ISchedulerRoles['tasks_managers'])


@adapter_config(required=IScheduler,
                provides=ISchedulerRoles)
def scheduler_roles_adapter(context):
    """Scheduler roles adapter"""
    return SchedulerRoles(context)


@adapter_config(name='scheduler_roles',
                required=IScheduler,
                provides=IRolesPolicy)
class SchedulerRolesPolicy(ContextAdapter):
    """Scheduler roles policy"""

    roles_interface = ISchedulerRoles
    weight = 10
