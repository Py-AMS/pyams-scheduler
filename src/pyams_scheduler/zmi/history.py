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
import heapq
import math
from datetime import timedelta

from pyramid.decorator import reify
from zope.interface import Interface
from zope.traversing.interfaces import ITraversable

from pyams_form.field import Fields
from pyams_layer.interfaces import IPyAMSLayer
from pyams_pagelet.pagelet import pagelet_config
from pyams_scheduler.interfaces import IScheduler, ITask, ITaskHistory, \
    MANAGE_SCHEDULER_PERMISSION, VIEW_HISTORY_PERMISSION
from pyams_scheduler.interfaces.folder import ITaskContainer, ITaskFolder
from pyams_scheduler.interfaces.task import TASK_STATUS_STYLES
from pyams_scheduler.interfaces.task.pipeline import IPipelineTask
from pyams_scheduler.task.report import Report
from pyams_scheduler.task.zmi import TaskBaseFormMixin
from pyams_scheduler.zmi import TaskContainerTable
from pyams_scheduler.zmi.interfaces import ISchedulerHistoryTable
from pyams_skin.interfaces.view import IModalPage
from pyams_skin.interfaces.viewlet import IContentPrefixViewletManager
from pyams_skin.widget.html import HTMLFieldWidget
from pyams_table.column import GetAttrColumn
from pyams_table.interfaces import IColumn, IValues
from pyams_utils.adapter import ContextAdapter, ContextRequestViewAdapter, adapter_config
from pyams_utils.date import SH_DATETIME_FORMAT, get_duration
from pyams_utils.factory import factory_config
from pyams_utils.finder import find_objects_providing
from pyams_utils.interfaces import MISSING_INFO
from pyams_utils.registry import get_utility
from pyams_utils.timezone import tztime
from pyams_utils.traversing import get_parent
from pyams_utils.url import absolute_url
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.form import AdminModalDisplayForm
from pyams_zmi.interfaces import IAdminLayer, TITLE_SPAN_BREAK
from pyams_zmi.interfaces.form import IFormTitle
from pyams_zmi.interfaces.table import ITableElementEditor
from pyams_zmi.interfaces.viewlet import IPropertiesMenu
from pyams_zmi.table import ActionColumn, DateColumn, I18nColumnMixin, InnerTableAdminView, \
    NameColumn, Table, TableAdminView, TableElementEditor
from pyams_zmi.utils import get_object_label
from pyams_zmi.zmi.viewlet.menu import NavigationMenuItem

__docformat__ = 'restructuredtext'


from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@viewlet_config(name='jobs-history.menu',
                context=ITaskContainer, layer=IAdminLayer,
                manager=IPropertiesMenu, weight=30,
                permission=VIEW_HISTORY_PERMISSION)
class SchedulerHistoryMenu(NavigationMenuItem):
    """Scheduler history menu"""

    label = _("Jobs history")
    href = '#jobs-history.html'


@factory_config(ISchedulerHistoryTable)
class SchedulerHistoryTable(Table):
    """Scheduler history table"""

    sort_on = 'table-date-1'
    sort_order = 'descending'
    
    css_classes = {
        'table': 'table table-striped table-hover table-xs datatable'
    }

    @reify
    def data_attributes(self):
        attributes = super().data_attributes
        attributes['table'].update({
            'data-ams-order': '1,desc'
        })
        return attributes

    def get_css_highlight_class(self, column, item, css_class):
        return (css_class or '') + ' ' + TASK_STATUS_STYLES.get(item.status, 'table-warning')
    

@adapter_config(required=(ITaskContainer, IAdminLayer, ISchedulerHistoryTable),
                provides=IValues)
class SchedulerHistoryTableValues(ContextRequestViewAdapter):
    """Scheduler history table values adapter"""

    @property
    def values(self):
        """Scheduler history table values getter"""
        yield from heapq.merge(*(
            reversed(task.history.values())
            for task in find_objects_providing(self.context, ITask)
        ), key=lambda x: tztime(x.date), reverse=True)


@adapter_config(name='name',
                required=(Interface, IAdminLayer, ISchedulerHistoryTable),
                provides=IColumn)
class SchedulerHistoryNameColumn(NameColumn):
    """Scheduler history name column"""

    i18n_header = _("Task name")

    weight = 10

    def get_value(self, obj):
        task = get_parent(obj, ITask)
        return task.get_path()


@adapter_config(name='date',
                required=(Interface, IAdminLayer, ISchedulerHistoryTable),
                provides=IColumn)
class SchedulerHistoryDateColumn(I18nColumnMixin, DateColumn):
    """Scheduler history date column"""

    i18n_header = _("Run date")
    attr_name = 'date'
    formatter = SH_DATETIME_FORMAT

    weight = 20
    
    def get_sort_key(self, item):
        return tztime(item.date)


@adapter_config(name='duration',
                required=(Interface, IAdminLayer, ISchedulerHistoryTable),
                provides=IColumn)
class SchedulerHistoryDurationColumn(I18nColumnMixin, GetAttrColumn):
    """Scheduler history duration column"""

    i18n_header = _("Duration")
    attr_name = 'duration'

    weight = 30

    def get_value(self, obj):
        duration = super().get_value(obj)
        if math.isclose(duration, 0.):
            return MISSING_INFO
        return get_duration(timedelta(seconds=duration), request=self.request)


@adapter_config(name='status',
                required=(Interface, IAdminLayer, ISchedulerHistoryTable),
                provides=IColumn)
class SchedulerHistoryStatusColumn(I18nColumnMixin, GetAttrColumn):
    """Scheduler history status column"""

    i18n_header = _("Status")
    attr_name = 'status'

    weight = 40


@pagelet_config(name='jobs-history.html',
                context=ITaskContainer, layer=IPyAMSLayer,
                permission=VIEW_HISTORY_PERMISSION)
class SchedulerHistoryView(TableAdminView):
    """Scheduler history view"""

    title = _("Tasks execution history")

    table_class = ISchedulerHistoryTable
    table_label = _("List of executed tasks")


#
# Task history view
#

@adapter_config(name='history',
                required=(ITaskContainer, IAdminLayer, TaskContainerTable),
                provides=IColumn)
class SchedulerTaskHistoryColumn(ActionColumn):
    """Scheduler task history column"""

    folder_href = 'properties.html'
    folder_icon_class = 'fas fa-edit'
    folder_hint = _("Rename folder")
    folder_permission = MANAGE_SCHEDULER_PERMISSION

    task_href = 'jobs-history.html'
    task_icon_class = 'fas fa-history'
    task_hint = _("Task run history")
    task_permission = VIEW_HISTORY_PERMISSION

    weight = 70

    def has_permission(self, item):
        if ITask.providedBy(item):
            permission = self.task_permission
        else:
            permission = self.folder_permission
        return self.request.has_permission(permission, context=item)

    def get_icon_class(self, item):
        if ITaskFolder.providedBy(item):
            return self.folder_icon_class
        return self.task_icon_class

    def get_icon_hint(self, item):
        translate = self.request.localizer.translate
        if IPipelineTask.providedBy(item):
            return translate(_("Task properties"))
        if ITask.providedBy(item):
            return translate(self.task_hint)
        return translate(self.folder_hint)

    def get_url(self, item):
        if ITaskFolder.providedBy(item):
            return absolute_url(item, self.request, self.folder_href)
        return absolute_url(item, self.request, self.task_href)


@pagelet_config(name='jobs-history.html',
                context=ITask, layer=IPyAMSLayer,
                permission=VIEW_HISTORY_PERMISSION)
class TaskHistoryView(TaskBaseFormMixin, AdminModalDisplayForm):
    """Task history view"""

    modal_class = 'modal-xl'


@viewlet_config(name='jobs-history-table',
                context=ITask, layer=IAdminLayer, view=TaskHistoryView,
                manager=IContentPrefixViewletManager, weight=10)
class TaskHistoryTableView(InnerTableAdminView):
    """Task history table view"""

    table_class = ISchedulerHistoryTable
    table_label = _("List of executed jobs")


@adapter_config(required=(ITask, IAdminLayer, ISchedulerHistoryTable),
                provides=IValues)
class TaskHistoryTableValues(ContextRequestViewAdapter):
    """Task history table values adapter"""

    @property
    def values(self):
        """Task history table values getter"""
        yield from self.context.history.values()


@adapter_config(name='history',
                required=ITask,
                provides=ITraversable)
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


@pagelet_config(name='history.html',
                context=ITaskHistory, layer=IPyAMSLayer)
class JobHistoryView(AdminModalDisplayForm):
    """Job run history display form"""

    modal_class = 'modal-max'

    subtitle = _("Task run history")
    legend = _("Task execution log")

    label_css_class = 'col-sm-3 col-md-2'
    input_css_class = 'col-sm-9 col-md-10'

    fields = Fields(ITaskHistory).omit('__parent__', '__name__')
    fields['report'].widget_factory = HTMLFieldWidget

    def update_widgets(self, prefix=None):
        super().update_widgets(prefix)
        duration = self.widgets.get('duration')
        if duration is not None:
            duration.value = get_duration(timedelta(seconds=self.context.duration))
        report = self.widgets.get('report')
        if report is not None:
            report_value = Report()
            report_value.write(self.context.report)
            report.value = report_value.getvalue()
            report.add_class('bg-light')


@adapter_config(required=(ITaskHistory, IAdminLayer, IModalPage),
                provides=IFormTitle)
def task_history_form_title(context, request, view):
    """Task history form title"""
    scheduler = get_utility(IScheduler)
    task = get_parent(context, ITask)
    return TITLE_SPAN_BREAK.format(
        get_object_label(scheduler, request, view),
        get_object_label(task, request, view, name='form-title'))
