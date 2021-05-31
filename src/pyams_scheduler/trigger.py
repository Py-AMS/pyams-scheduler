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

"""PyAMS_scheduler.trigger module

This modules defines tasks triggers, matching selected scheduling modes.
"""

from datetime import timedelta

from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from persistent import Persistent
from zope.componentvocabulary.vocabulary import UtilityVocabulary
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.interfaces import TASK_SCHEDULING_MODES_VOCABULARY
from pyams_scheduler.interfaces.task import ICronTask, ICronTaskScheduling, IDateTask, \
    IDateTaskScheduling, ILoopTask, ILoopTaskScheduling, ITaskSchedulingMode, \
    SCHEDULER_TASK_CRON_INFO, SCHEDULER_TASK_DATE_INFO, SCHEDULER_TASK_LOOP_INFO
from pyams_utils.adapter import adapter_config, get_annotation_adapter
from pyams_utils.date import date_to_datetime
from pyams_utils.factory import factory_config
from pyams_utils.registry import utility_config
from pyams_utils.timezone import tztime
from pyams_utils.vocabulary import vocabulary_config


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@vocabulary_config(name=TASK_SCHEDULING_MODES_VOCABULARY)
class SchedulingModesVocabulary(UtilityVocabulary):
    """Scheduling modes vocabulary"""

    interface = ITaskSchedulingMode
    nameOnly = True


#
# Immediate task trigger
#

class ImmediateTaskTrigger(BaseTrigger):  # pylint: disable=no-init
    """Immediate-style task scheduler"""

    def get_next_fire_time(self, previous_fire_time, now):
        """Get next task fire time"""
        if previous_fire_time:
            return None
        return now + timedelta(seconds=5)


#
# Cron-style scheduling mode
#

@factory_config(ICronTaskScheduling)
class CronTaskScheduleInfo(Persistent):
    """Cron-style schedule info"""

    active = FieldProperty(ICronTaskScheduling['active'])
    start_date = FieldProperty(ICronTaskScheduling['start_date'])
    end_date = FieldProperty(ICronTaskScheduling['end_date'])
    year = FieldProperty(ICronTaskScheduling['year'])
    month = FieldProperty(ICronTaskScheduling['month'])
    day = FieldProperty(ICronTaskScheduling['day'])
    week = FieldProperty(ICronTaskScheduling['week'])
    day_of_week = FieldProperty(ICronTaskScheduling['day_of_week'])
    hour = FieldProperty(ICronTaskScheduling['hour'])
    minute = FieldProperty(ICronTaskScheduling['minute'])
    second = FieldProperty(ICronTaskScheduling['second'])


@adapter_config(required=ICronTask, provides=ICronTaskScheduling)
def cron_task_scheduler_info_factory(context):
    """Cron-style task scheduling info factory"""
    return get_annotation_adapter(context, SCHEDULER_TASK_CRON_INFO, ICronTaskScheduling,
                                  notify=False, locate=False)


@utility_config(name='Cron-style scheduling', provides=ITaskSchedulingMode)
class CronTaskScheduler:
    """Cron-style scheduler mode"""

    marker_interface = ICronTask
    schema = ICronTaskScheduling

    def get_trigger(self, task):
        """Get cron-like task trigger"""
        if not self.marker_interface.providedBy(task):
            raise Exception(_("Task is not configured for cron-style scheduling!"))
        info = self.schema(task, None)
        if info is None:
            return None
        return CronTrigger(year=info.year or '*',
                           month=info.month or '*',
                           day=info.day or '*',
                           week=info.week or '*',
                           day_of_week=info.day_of_week or '*',
                           hour=info.hour or '*',
                           minute=info.minute or '*',
                           second=info.second or '0',
                           start_date=tztime(date_to_datetime(info.start_date)),
                           end_date=tztime(date_to_datetime(info.end_date)))


#
# Date-style scheduling mode
#

@factory_config(IDateTaskScheduling)
class DateTaskScheduleInfo(Persistent):
    """Date-style schedule info"""

    active = FieldProperty(IDateTaskScheduling['active'])
    start_date = FieldProperty(IDateTaskScheduling['start_date'])


@adapter_config(required=IDateTask, provides=IDateTaskScheduling)
def date_task_scheduler_info_factory(context):
    """Date-style task scheduling info factory"""
    return get_annotation_adapter(context, SCHEDULER_TASK_DATE_INFO, IDateTaskScheduling,
                                  notify=False, locate=False)


@utility_config(name='Date-style scheduling', provides=ITaskSchedulingMode)
class DateTaskScheduler:
    """Date-style scheduler mode"""

    marker_interface = IDateTask
    schema = IDateTaskScheduling

    def get_trigger(self, task):
        """Get date trigger"""
        if not self.marker_interface.providedBy(task):
            raise Exception(_("Task is not configured for date-style scheduling!"))
        info = self.schema(task, None)
        if info is None:
            return None
        return DateTrigger(run_date=tztime(date_to_datetime(info.start_date)))


#
# Loop-style scheduling mode
#

@factory_config(ILoopTaskScheduling)
class LoopTaskScheduleInfo(Persistent):
    """Loop-style schedule info"""

    active = FieldProperty(ILoopTaskScheduling['active'])
    start_date = FieldProperty(ILoopTaskScheduling['start_date'])
    end_date = FieldProperty(ILoopTaskScheduling['end_date'])
    weeks = FieldProperty(ILoopTaskScheduling['weeks'])
    days = FieldProperty(ILoopTaskScheduling['days'])
    hours = FieldProperty(ILoopTaskScheduling['hours'])
    minutes = FieldProperty(ILoopTaskScheduling['minutes'])
    seconds = FieldProperty(ILoopTaskScheduling['seconds'])


@adapter_config(required=ILoopTask, provides=ILoopTaskScheduling)
def loop_task_scheduler_info_factory(context):
    """Loop-style task scheduling info factory"""
    return get_annotation_adapter(context, SCHEDULER_TASK_LOOP_INFO, ILoopTaskScheduling,
                                  notify=False, locate=False)


@utility_config(name='Loop-style scheduling', provides=ITaskSchedulingMode)
class LoopTaskScheduler:
    """Loop-style scheduler mode"""

    marker_interface = ILoopTask
    schema = ILoopTaskScheduling

    def get_trigger(self, task):
        """Get loop interval trigger"""
        if not self.marker_interface.providedBy(task):
            raise Exception(_("Task is not configured for loop-style scheduling!"))
        info = self.schema(task, None)
        if info is None:
            return None
        return IntervalTrigger(weeks=info.weeks,
                               days=info.days,
                               hours=info.hours,
                               minutes=info.minutes,
                               seconds=info.seconds,
                               start_date=tztime(date_to_datetime(info.start_date)),
                               end_date=tztime(date_to_datetime(info.end_date)))
