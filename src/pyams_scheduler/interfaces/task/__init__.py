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

"""PyAMS_scheduler.interfaces.task module

This module defines scheduler tasks interfaces.
"""

__docformat__ = 'restructuredtext'

from zope.annotation import IAttributeAnnotatable
from zope.container.constraints import containers, contains
from zope.container.interfaces import IContainer
from zope.interface import Attribute, Interface
from zope.schema import Bool, Bytes, Choice, Datetime, Float, Int, List, Object, Text, TextLine

from pyams_scheduler import _
from pyams_utils.schema import TextLineListField


TASK_STATUS_NONE = None
TASK_STATUS_EMPTY = 'empty'
TASK_STATUS_OK = 'OK'
TASK_STATUS_WARNING = 'warning'
TASK_STATUS_ERROR = 'error'

TASK_STATUS_STYLES = {
    TASK_STATUS_EMPTY: 'table-secondary',
    TASK_STATUS_NONE: 'table-info',
    TASK_STATUS_OK: 'table-success',
    TASK_STATUS_WARNING: 'table-warning',
    TASK_STATUS_ERROR: 'table-danger'
}


#
# Task history item interface
#

class ITaskHistoryContainer(Interface):
    """Task history container interface"""

    contains('pyams_scheduler.interfaces.task.ITaskHistory')


class ITaskHistory(Interface):
    """Scheduler task history item interface"""

    containers(ITaskHistoryContainer)

    status = TextLine(title=_("Execution status"))

    date = Datetime(title=_("Execution start date"),
                    required=True)

    duration = Float(title=_("Execution duration"),
                     required=True)

    report = Text(title=_("Execution report"),
                  required=True)


#
# Scheduler job interface
#

class IJobInfo(Interface):
    """Job interface"""

    id = TextLine(title="Job ID")

    next_run_time = Float(title="Job next run time")

    job_state = Bytes(title="Job state")


#
# Task scheduling modes interfaces
#

TASK_SCHEDULING_MODES_VOCABULARY = 'PyAMS_scheduler.scheduling.modes'


class ITaskSchedulingMode(Interface):
    """Scheduler task scheduling mode"""

    marker_interface = Attribute("Class name of scheduling mode marker interface")

    schema = Attribute("Class name of scheduling mode info interface")

    def get_trigger(self, task):
        """Get trigger for the given task"""

    def schedule(self, task, scheduler):
        """Add given task to the scheduler"""


class ITaskSchedulingMarker(Interface):
    """Base interface for task scheduling mode markers"""


class IBaseTaskScheduling(Interface):
    """Base interface for task scheduling info"""

    active = Bool(title=_("Activate task?"),
                  description=_("You can disable a task by selecting 'No'"),
                  required=True,
                  default=False)

    start_date = Datetime(title=_("First execution date"),
                          description=_("Date and time from which scheduling should start"),
                          required=False)


#
# Scheduler cron-style tasks interfaces
#

SCHEDULER_TASK_CRON_INFO = 'pyams_scheduler.trigger.cron'


class ICronTask(Interface):
    """Cron-style task marker interface"""


class ICronTaskScheduling(IBaseTaskScheduling):
    """Base interface for cron-style scheduled tasks"""

    end_date = Datetime(title=_("Last execution date"),
                        description=_("Date and time past which scheduling should end"),
                        required=False)

    year = TextLine(title=_("Years"),
                    description=_("Years for which to schedule the job"),
                    required=False,
                    default='*')

    month = TextLine(title=_("Months"),
                     description=_("Months (1-12) for which to schedule the job"),
                     required=False,
                     default='*')

    day = TextLine(title=_("Month days"),
                   description=_("Days (1-31) for which to schedule the job"),
                   required=False,
                   default='*')

    week = TextLine(title=_("Weeks"),
                    description=_("Year weeks (1-53) for which to schedule the job"),
                    required=False,
                    default='*')

    day_of_week = TextLine(title=_("Week days"),
                           description=_("Week days (0-6, with 0 as monday) for which to "
                                         "schedule the job"),
                           required=False,
                           default='*')

    hour = TextLine(title=_("Hours"),
                    description=_("Hours (0-23) for which to schedule the job"),
                    required=False,
                    default='*')

    minute = TextLine(title=_("Minutes"),
                      description=_("Minutes (0-59) for which to schedule the job"),
                      required=False,
                      default='*')

    second = TextLine(title=_("Seconds"),
                      description=_("Seconds (0-59) for which to schedule the job"),
                      required=False,
                      default='0')


#
# Scheduler date-style tasks interface
#

SCHEDULER_TASK_DATE_INFO = 'pyams_scheduler.trigger.date'


class IDateTask(Interface):
    """Date-style task marker interface"""


class IDateTaskScheduling(IBaseTaskScheduling):
    """Base interface for date-style scheduled tasks"""

    start_date = Datetime(title=_("Execution date"),
                          description=_("Date and time on which execution should start"),
                          required=True)


#
# Scheduler loop-style tasks interface
#

SCHEDULER_TASK_LOOP_INFO = 'pyams_scheduler.trigger.loop'


class ILoopTask(Interface):
    """Loop-style task marker interface"""


class ILoopTaskScheduling(IBaseTaskScheduling):
    """Base interface for loop-style scheduled tasks"""

    end_date = Datetime(title=_("Last execution date"),
                        description=_("Date and time past which scheduling should end"),
                        required=False)

    weeks = Int(title=_("Weeks interval"),
                description=_("Number of weeks between executions"),
                required=True,
                default=0)

    days = Int(title=_("Days interval"),
               description=_("Number of days between executions"),
               required=True,
               default=0)

    hours = Int(title=_("Hours interval"),
                description=_("Number of hours between executions"),
                required=True,
                default=0)

    minutes = Int(title=_("Minutes interval"),
                  description=_("Number of minutes between executions"),
                  required=True,
                  default=1)

    seconds = Int(title=_("Seconds interval"),
                  description=_("Number of seconds between executions"),
                  required=True,
                  default=0)


#
# Scheduler task interfaces
#

class ITaskInfo(Interface):
    """Scheduler task interface"""

    containers('.IScheduler')

    name = TextLine(title=_("Task name"),
                    description=_("Descriptive name given to this task"),
                    required=True)

    schedule_mode = Choice(title=_("Scheduling mode"),
                           description=_("Scheduling mode defines how task will be scheduled"),
                           vocabulary=TASK_SCHEDULING_MODES_VOCABULARY,
                           required=True)

    keep_empty_reports = Bool(title=_("Keep empty reports history?"),
                              description=_("If 'Yes', empty reports will be kept in task "
                                            "history"),
                              required=True,
                              default=False)

    history_duration = Int(title=_("History duration"),
                           description=_("Number of days during which execution reports are "
                                         "kept in history; enter 0 to remove limit"),
                           required=False)

    history_length = Int(title=_("History max length"),
                         description=_("Number of execution reports to keep in history; enter 0 "
                                       "to remove limit"),
                         required=False)


class ITask(ITaskInfo, IAttributeAnnotatable):
    """Complete task interface"""

    label = Attribute("Task label")

    icon_class = Attribute("FontAwesome icon class")

    settings_view_name = TextLine(title=_("Settings view name"),
                                  default='settings.html',
                                  required=False)

    history = List(title=_("History"),
                   description=_("Task history"),
                   value_type=Object(schema=ITaskHistory))

    runnable = Attribute("Is the task runnable?")

    internal_id = Attribute("Internal ID")

    def get_trigger(self):
        """Get scheduler job trigger"""

    def get_scheduling_info(self):
        """Get scheduling info"""

    def run(self, report, **kwargs):
        """Launch job execution"""

    def store_report(self, report, status, start_date, duration):
        """Store task execution report in task's history"""

    def send_report(self, report, status, target=None):
        """Send task execution report by mail"""

    def reset(self):
        """Re-schedule job execution"""

    def launch(self):
        """Ask task for immediate execution"""


#
# Task notifications interfaces
#

TASK_NOTIFICATION_MODES_VOCABULARY = 'PyAMS_scheduler.notifications.modes'


class ITaskNotificationMode(Interface):
    """Task notification mode utility interface"""

    def send_report(self, task, report, status, target, registry=None):  # pylint: disable=too-many-arguments
        """Send report to given target"""


class ITaskNotification(Interface):
    """Task notification"""

    enabled = Bool(title=_("Enabled?"),
                   description=_("Recipient will not be notified if notification is disabled"),
                   required=True,
                   default=True)

    report_errors_only = Bool(title=_("Only report errors?"),
                              description=_("If 'Yes', only error reports will be sent to given "
                                            "errors target"),
                              required=True,
                              default=False)

    send_empty_reports = Bool(title=_("Send empty reports?"),
                              description=_("If 'No', empty reports will not be sent by mail"),
                              required=True,
                              default=False)

    mode = Attribute("Notification mode")

    def get_handler(self):
        """Return notification handler utility"""


SCHEDULER_TASK_NOTIFICATIONS_KEY = 'pyams_scheduler.task.notifications'


class ITaskNotificationContainer(IContainer):
    """Task notifications container interface"""

    contains(ITaskNotification)

    def get_enabled_items(self):
        """Get iterator over enabled notifications"""


#
# Task mail notifications interfaces
#

class IMailNotification(ITaskNotification):
    """Mail notification info interface"""

    target_email = TextLineListField(title=_("Target's email"),
                                     description=_("Email address of report's recipient; you can "
                                                   "enter email address in a simple form or in "
                                                   "in a complete \"Name <adresse@domain.com>\" "
                                                   "form"),
                                     required=True)
