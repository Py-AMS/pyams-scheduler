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

"""PyAMS_scheduler.zmi.history module

This module defines views which are used to display content history.
"""

from datetime import timedelta

from zope.interface import Interface
from zope.traversing.interfaces import ITraversable

from pyams_form.field import Fields
from pyams_layer.interfaces import IPyAMSLayer
from pyams_pagelet.pagelet import pagelet_config
from pyams_scheduler.interfaces import IScheduler, ITask, ITaskHistory, MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.task import TASK_STATUS_STYLES
from pyams_scheduler.zmi import SchedulerTasksTable
from pyams_skin.interfaces.viewlet import IContentPrefixViewletManager
from pyams_table.column import GetAttrColumn
from pyams_table.interfaces import IColumn, IValues
from pyams_utils.adapter import ContextAdapter, ContextRequestViewAdapter, adapter_config
from pyams_utils.date import SH_DATETIME_FORMAT, get_duration
from pyams_utils.traversing import get_parent
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.form import AdminModalDisplayForm
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.table import ITableElementEditor
from pyams_zmi.interfaces.viewlet import IPropertiesMenu
from pyams_zmi.table import ActionColumn, DateColumn, I18nColumnMixin, InnerTableAdminView, \
    NameColumn, Table, TableAdminView, TableElementEditor
from pyams_zmi.zmi.viewlet.menu import NavigationMenuItem


__docformat__ = 'restructuredtext'


from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@viewlet_config(name='jobs-history.menu',
                context=IScheduler, layer=IAdminLayer,
                manager=IPropertiesMenu, weight=30,
                permission=MANAGE_TASKS_PERMISSION)
class SchedulerHistoryMenu(NavigationMenuItem):
    """Scheduler history menu"""

    label = _("Jobs history")
    href = '#jobs-history.html'


class SchedulerHistoryTable(Table):
    """Scheduler history table"""

    css_classes = {
        'table': 'table table-striped table-hover table-xs datatable'
    }

    @property
    def data_attributes(self):
        attributes = super().data_attributes
        attributes['table'].update({
            'data-ams-order': '1,desc'
        })
        return attributes

    def get_css_highlight_class(self, column, item, css_class):
        return (css_class or '') + ' ' + TASK_STATUS_STYLES.get(item.status, 'table-warning')


@adapter_config(required=(IScheduler, IAdminLayer, SchedulerHistoryTable),
                provides=IValues)
class SchedulerHistoryTableValues(ContextRequestViewAdapter):
    """Scheduler history table values adapter"""

    @property
    def values(self):
        """Scheduler history table values getter"""
        for task in self.context.values():
            yield from task.history.values()


@adapter_config(name='name',
                required=(Interface, IAdminLayer, SchedulerHistoryTable),
                provides=IColumn)
class SchedulerHistoryNameColumn(NameColumn):
    """Scheduler history name column"""

    i18n_header = _("Task name")

    weight = 10

    def get_value(self, obj):
        task = get_parent(obj, ITask)
        return task.name


@adapter_config(name='date',
                required=(Interface, IAdminLayer, SchedulerHistoryTable),
                provides=IColumn)
class SchedulerHistoryDateColumn(I18nColumnMixin, DateColumn):
    """Scheduler history date column"""

    i18n_header = _("Run date")
    attr_name = 'date'
    formatter = SH_DATETIME_FORMAT

    weight = 20


@adapter_config(name='duration',
                required=(Interface, IAdminLayer, SchedulerHistoryTable),
                provides=IColumn)
class SchedulerHistoryDurationColumn(I18nColumnMixin, GetAttrColumn):
    """Scheduler history duration column"""

    i18n_header = _("Duration")
    attr_name = 'duration'

    weight = 30

    def get_value(self, obj):
        duration = super().get_value(obj)
        if duration == 0.:
            return '--'
        return get_duration(timedelta(seconds=duration), request=self.request)


@adapter_config(name='status',
                required=(Interface, IAdminLayer, SchedulerHistoryTable),
                provides=IColumn)
class SchedulerHistoryStatusColumn(I18nColumnMixin, GetAttrColumn):
    """Scheduler history status column"""

    i18n_header = _("Status")
    attr_name = 'status'

    weight = 40


@pagelet_config(name='jobs-history.html',
                context=IScheduler, layer=IPyAMSLayer,
                permission=MANAGE_TASKS_PERMISSION)
class SchedulerHistoryView(TableAdminView):
    """Scheduler history view"""

    title = _("Tasks execution history")
    table_class = SchedulerHistoryTable
    table_label = _("List of executed tasks")


#
# Task history view
#

@adapter_config(name='history',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class SchedulerTaskHistoryColumn(ActionColumn):
    """Scheduler task history column"""

    href = 'jobs-history.html'
    icon_class = 'fas fa-history'
    hint = _("Task run history")

    permission = MANAGE_TASKS_PERMISSION

    weight = 70


@pagelet_config(name='jobs-history.html', context=ITask, layer=IPyAMSLayer,
                permission=MANAGE_TASKS_PERMISSION)
class TaskHistoryView(AdminModalDisplayForm):
    """Task history view"""

    @property
    def title(self):
        """Title getter"""
        return self.context.name

    modal_class = 'modal-xl'


@viewlet_config(name='jobs-history-table',
                context=ITask, layer=IAdminLayer, view=TaskHistoryView,
                manager=IContentPrefixViewletManager, weight=10)
class TaskHistoryTableView(InnerTableAdminView):
    """Task history table view"""

    title = _("Task execution history")
    table_class = SchedulerHistoryTable
    table_label = _("List of executed jobs")


@adapter_config(required=(ITask, IAdminLayer, SchedulerHistoryTable),
                provides=IValues)
class TaskHistoryTableValues(ContextRequestViewAdapter):
    """Task history table values adapter"""

    @property
    def values(self):
        """Task history table values getter"""
        yield from self.context.history.values()


@adapter_config(name='history', required=ITask, provides=ITraversable)
class TaskHistoryTraverser(ContextAdapter):
    """Task history traverser"""

    def traverse(self, name, furtherpath=None):  # pylint: disable=unused-argument
        """Task history traverser"""
        return self.context.history


@adapter_config(required=(ITaskHistory, IAdminLayer, Interface),
                provides=ITableElementEditor)
class TaskHistoryElementEditor(TableElementEditor):
    """Task history element editor"""

    view_name = 'history.html'


@pagelet_config(name='history.html', context=ITaskHistory, layer=IPyAMSLayer)
class JobHistoryView(AdminModalDisplayForm):
    """Job run history display form"""

    @property
    def title(self):
        """Title getter"""
        return get_parent(self.context, ITask).name

    legend = _("Task run history")
    modal_class = 'modal-max'

    label_css_class = 'col-sm-3 col-md-2'
    input_css_class = 'col-sm-9 col-md-8'

    fields = Fields(ITaskHistory).omit('__parent__', '__name__')

    def update_widgets(self, prefix=None):
        super().update_widgets(prefix)
        duration = self.widgets.get('duration')
        if duration is not None:
            duration.value = get_duration(timedelta(seconds=self.context.duration))
        report = self.widgets.get('report')
        if report is not None:
            report.rows = 15
            report.add_class('monospace')
