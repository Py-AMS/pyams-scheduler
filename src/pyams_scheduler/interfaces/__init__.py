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
from zope.interface import Attribute, Interface, implementer
from zope.interface.interfaces import IObjectEvent, ObjectEvent
from zope.schema import Bool, Choice, List, Object, TextLine

from pyams_mail.interfaces import MAILERS_VOCABULARY_NAME
from pyams_scheduler.interfaces.task import IBaseTaskScheduling, ITask, ITaskHistory, \
    TASK_SCHEDULING_MODES_VOCABULARY
from pyams_security.interfaces import IContentRoles
from pyams_security.schema import PrincipalsSetField
from pyams_utils.interfaces import ZODB_CONNECTIONS_VOCABULARY_NAME
from pyams_zmq.interfaces import IZMQProcess

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


#
# Scheduler permissions and roles
#

MANAGE_SCHEDULER_PERMISSION = 'pyams.ManageScheduler'
'''Permission used to manage tasks scheduler properties'''

MANAGE_TASKS_PERMISSION = 'pyams.ManageSchedulerTasks'
'''Permission used to manager scheduler tasks'''

VIEW_HISTORY_PERMISSION = 'pyams.ViewTasksHistory'
'''Permission used to view tasks execution history'''


SCHEDULER_MANAGER_ROLE = 'pyams.SchedulerManager'
'''Scheduler manager role'''

TASKS_MANAGER_ROLE = 'pyams.TasksManager'
'''Tasks scheduler manager role'''

SCHEDULER_GUEST_ROLE = 'pyams.SchedulerGuest'
'''Scheduler guest role'''


#
# Scheduler events
#

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
# Scheduler interfaces
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


TASKS_SCHEDULER_LABEL = _("Tasks scheduler")


class IScheduler(IAttributeAnnotatable):
    """Scheduler interface"""

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

    notified_host = TextLine(title=_("Notified host"),
                             description=_("If websockets notifications are enabled, this is "
                                           "the host (including protocol) which will "
                                           "be notified"),
                             required=False)

    show_home_menu = Bool(title=_("Access menu from home"),
                          description=_("If 'yes', a menu will be displayed to get access to "
                                        "tasks scheduler from site admin home page"),
                          required=True,
                          default=False)

    internal_id = Attribute("Internal ID")

    def get_socket(self):
        """Get ZMQ socket matching scheduler utility"""

    def get_task(self, task_id):
        """Get task matching given task ID"""

    def get_jobs(self):
        """Get text output of running jobs"""

    history = List(title=_("History"),
                   description=_("Task history"),
                   value_type=Object(schema=ITaskHistory),
                   readonly=True)


class ITaskContainerRoles(IContentRoles):
    """Scheduler roles"""

    scheduler_managers = PrincipalsSetField(title=_("Scheduler managers"),
                                            description=_("Scheduler managers can handle all scheduler and tasks "
                                                          "properties, including roles"),
                                            role_id=SCHEDULER_MANAGER_ROLE,
                                            required=False)

    tasks_managers = PrincipalsSetField(title=_("Tasks manager"),
                                        description=_("Tasks managers can manage tasks properties and launch them; "
                                                      "they can't manage scheduler or tasks roles"),
                                        role_id=TASKS_MANAGER_ROLE,
                                        required=False)

    scheduler_guests = PrincipalsSetField(title=_("Guests"),
                                          description=_("Guests are only allowed to display tasks properties "
                                                        "and execution history"),
                                          role_id=SCHEDULER_GUEST_ROLE,
                                          required=False)
