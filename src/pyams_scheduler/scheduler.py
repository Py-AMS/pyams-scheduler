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

from zope.interface import implementer
from zope.intid import IIntIds
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.folder import TaskContainer
from pyams_scheduler.interfaces import IScheduler, ISchedulerHandler, ITask, SCHEDULER_AUTH_KEY, SCHEDULER_HANDLER_KEY
from pyams_utils.factory import factory_config
from pyams_utils.finder import find_objects_providing
from pyams_utils.registry import get_pyramid_registry, query_utility
from pyams_zmq.socket import zmq_response, zmq_socket


@implementer(ISchedulerHandler)
class SchedulerHandler:
    """Scheduler handler utility

    This is just a 'marker' utility which is used to mark nodes in a cluster
    which should run the scheduler
    """


@factory_config(IScheduler)
class Scheduler(TaskContainer):
    """Scheduler utility"""

    zodb_name = FieldProperty(IScheduler['zodb_name'])
    report_mailer = FieldProperty(IScheduler['report_mailer'])
    report_source = FieldProperty(IScheduler['report_source'])
    notified_host = FieldProperty(IScheduler['notified_host'])
    show_home_menu = FieldProperty(IScheduler['show_home_menu'])

    @property
    def history(self):
        """Scheduler full history getter"""
        result = []
        for task in find_objects_providing(self, ITask):
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

    def get_task(self, task_id):
        """Get task matching given ID"""
        intids = query_utility(IIntIds)
        if intids is None:
            intids = self.__parent__.getUtility(IIntIds)
        if isinstance(task_id, str):
            task_id = int(task_id, 16)
        return intids.queryObject(task_id)

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
