#
# Copyright (c) 2015-2019 Thierry Florac <tflorac AT ulthar.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

"""PyAMS_scheduler.interfaces base module

This module defines base package interfaces.
"""

from zope.annotation import IAttributeAnnotatable
from zope.container.constraints import contains
from zope.interface import Attribute, Interface, implementer
from zope.interface.interfaces import IObjectEvent, ObjectEvent
from zope.schema import Choice, List, Object, TextLine

from pyams_mail.interfaces import MAILERS_VOCABULARY_NAME
from pyams_scheduler.interfaces.task import IBaseTaskScheduling, ITask, ITaskHistory, \
    TASK_SCHEDULING_MODES_VOCABULARY
from pyams_security.interfaces import IContentRoles
from pyams_security.schema import PrincipalsSetField
from pyams_utils.interfaces import ZODB_CONNECTIONS_VOCABULARY_NAME
from pyams_zmq.interfaces import IZMQProcess

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


#
# Scheduler events
#

MANAGE_SCHEDULER_PERMISSION = 'pyams.ManageScheduler'
'''Permission used to manage tasks scheduler properties'''

MANAGE_TASKS_PERMISSION = 'pyams.ManageSchedulerTasks'
'''Permission used to manager scheduler tasks'''

SCHEDULER_MANAGER_ROLE = 'pyams.SchedulerManager'
'''Scheduler manager role'''

TASKS_MANAGER_ROLE = 'pyams.TasksManager'
'''Tasks scheduler manager role'''


class IBeforeRunJobEvent(IObjectEvent):
    """Interface for events notified before a job is run"""


@implementer(IBeforeRunJobEvent)
class BeforeRunJobEvent(ObjectEvent):
    """Before run job event"""


class IAfterRunJobEvent(IObjectEvent):
    """Interface for events notified after a job is run"""

    status = Attribute("Job execution status")

    result = Attribute("Job execution result")


@implementer(IAfterRunJobEvent)
class AfterRunJobEvent(ObjectEvent):
    """After run job event"""

    def __init__(self, obj, status, result):
        super().__init__(obj)
        self.status = status
        self.result = result


#
# Scheduler interface
#

SCHEDULER_NAME = 'Tasks scheduler'
SCHEDULER_STARTER_KEY = 'pyams_scheduler.start_handler'
SCHEDULER_HANDLER_KEY = 'pyams_scheduler.tcp_handler'
SCHEDULER_AUTH_KEY = 'pyams_scheduler.allow_auth'
SCHEDULER_CLIENTS_KEY = 'pyams_scheduler.allow_clients'

SCHEDULER_JOBSTORE_KEY = 'pyams_scheduler.jobs'


class ISchedulerProcess(IZMQProcess):
    """Scheduler process marker interface"""


class ISchedulerHandler(Interface):
    """Scheduler manager marker interface"""


class IScheduler(IAttributeAnnotatable):
    """Scheduler interface"""

    contains(ITask)

    zodb_name = Choice(title=_("ZODB connection name"),
                       description=_("Name of ZODB defining scheduler connection"),
                       required=False,
                       default='',
                       vocabulary=ZODB_CONNECTIONS_VOCABULARY_NAME)

    report_mailer = Choice(title=_("Reports mailer"),
                           description=_("Mail delivery utility used to send mails"),
                           required=False,
                           vocabulary=MAILERS_VOCABULARY_NAME)

    report_source = TextLine(title=_("Reports source"),
                             description=_("Mail address from which reports will be sent"),
                             required=False)

    internal_id = Attribute("Internal ID")

    def get_socket(self):
        """Get ZMQ socket matching scheduler utility"""

    def get_task(self, task_id):
        """Get task matching given task ID"""

    def get_jobs(self):
        """Get text output of running jobs"""

    tasks = List(title=_("Scheduler tasks"),
                 description=_("List of tasks assigned to this scheduler"),
                 value_type=Object(schema=ITask),
                 readonly=True)

    history = List(title=_("History"),
                   description=_("Task history"),
                   value_type=Object(schema=ITaskHistory),
                   readonly=True)


class ISchedulerRoles(IContentRoles):
    """Scheduler roles"""

    scheduler_managers = PrincipalsSetField(title=_("Scheduler managers"),
                                            role_id=SCHEDULER_MANAGER_ROLE,
                                            required=False)

    tasks_managers = PrincipalsSetField(title=_("Tasks manager"),
                                        role_id=TASKS_MANAGER_ROLE,
                                        required=False)
