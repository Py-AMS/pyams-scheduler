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

"""PyAMS_scheduler.zmi.jobs module

This module defines components used to display scheduled jobs.
"""

from datetime import datetime

from pyams_layer.interfaces import IPyAMSLayer
from pyams_pagelet.pagelet import pagelet_config
from pyams_scheduler.interfaces import IScheduler, MANAGE_TASKS_PERMISSION
from pyams_table.column import GetAttrColumn
from pyams_table.interfaces import IColumn, IValues
from pyams_utils.adapter import ContextRequestViewAdapter, adapter_config
from pyams_utils.date import format_datetime
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.viewlet import IPropertiesMenu
from pyams_zmi.table import I18nColumnMixin, Table, TableAdminView
from pyams_zmi.zmi.viewlet.menu import NavigationMenuItem

__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@viewlet_config(name='jobs-list.menu',
                context=IScheduler, layer=IAdminLayer,
                manager=IPropertiesMenu, weight=20,
                permission=MANAGE_TASKS_PERMISSION)
class SchedulerJobsMenu(NavigationMenuItem):
    """Scheduler jobs menu"""

    label = _("Scheduled jobs")
    href = '#jobs-list.html'


class SchedulerJobsTable(Table):
    """Scheduler jobs table"""


@adapter_config(required=(IScheduler, IAdminLayer, SchedulerJobsTable),
                provides=IValues)
class SchedulerJobsTableValues(ContextRequestViewAdapter):
    """Scheduler jobs values adapter"""

    @property
    def values(self):
        """Scheduler jobs table values getter"""
        status_code, response = self.context.get_jobs()
        if status_code == 200:
            yield from response


class JobsColumn(I18nColumnMixin, GetAttrColumn):
    """Base jobs column"""

    def get_value(self, obj):
        return obj.get(self.attr_name, '--')


@adapter_config(name='name',
                required=(IScheduler, IAdminLayer, SchedulerJobsTable),
                provides=IColumn)
class SchedulerJobsNameColumn(JobsColumn):
    """Scheduler jobs name column"""

    i18n_header = _("Name")
    attr_name = 'name'
    weight = 10


@adapter_config(name='id',
                required=(IScheduler, IAdminLayer, SchedulerJobsTable),
                provides=IColumn)
class SchedulerJobsIDColumn(JobsColumn):
    """Scheduler jobs ID column"""

    i18n_header = _("ID")
    attr_name = 'id'
    weight = 20


@adapter_config(name='trigger',
                required=(IScheduler, IAdminLayer, SchedulerJobsTable),
                provides=IColumn)
class SchedulerJobsTriggerColumn(JobsColumn):
    """Scheduler jobs trigger column"""

    i18n_header = _("Trigger")
    attr_name = 'trigger'
    weight = 30


@adapter_config(name='next_run',
                required=(IScheduler, IAdminLayer, SchedulerJobsTable),
                provides=IColumn)
class SchedulerJobsNextRunColumn(JobsColumn):
    """Scheduler jobs next run column"""

    i18n_header = _("Next run")
    attr_name = 'next_run'
    weight = 40

    def get_value(self, obj):
        value = super().get_value(obj)
        if not value:
            return '--'
        return format_datetime(datetime.utcfromtimestamp(value), request=self.request)


@pagelet_config(name='jobs-list.html', context=IScheduler, layer=IPyAMSLayer,
                permission=MANAGE_TASKS_PERMISSION)
class SchedulerJobsView(TableAdminView):
    """Scheduler jobs view"""

    title = _("Scheduler jobs")
    table_class = SchedulerJobsTable
    table_label = _("List of scheduler jobs")
