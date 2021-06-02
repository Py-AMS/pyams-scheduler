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

"""PyAMS_scheduler.zmi module

This module defines base tasks management views.
"""

from pyramid.view import view_config
from zope.interface import Interface

from pyams_layer.interfaces import IPyAMSLayer
from pyams_pagelet.pagelet import pagelet_config
from pyams_scheduler.interfaces import IBaseTaskScheduling, IScheduler, MANAGE_TASKS_PERMISSION
from pyams_table.column import GetAttrColumn
from pyams_table.interfaces import IColumn, IValues
from pyams_utils.adapter import ContextRequestViewAdapter, adapter_config
from pyams_viewlet.manager import viewletmanager_config
from pyams_zmi.helper.container import delete_container_element
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.table import ITableElementEditor
from pyams_zmi.interfaces.viewlet import IMenuHeader, IPropertiesMenu, ISiteManagementMenu
from pyams_zmi.table import I18nColumnMixin, IconColumn, NameColumn, Table, TableAdminView, \
    TableElementEditor, \
    TrashColumn
from pyams_zmi.zmi.viewlet.menu import NavigationMenuItem


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@adapter_config(required=(IScheduler, IAdminLayer, Interface, ISiteManagementMenu),
                provides=IMenuHeader)
def scheduler_menu_header(context, request, view, manager):  # pylint: disable=unused-argument
    """Scheduler menu header"""
    return _("Tasks scheduler")


@adapter_config(required=(IScheduler, IAdminLayer, Interface),
                provides=ITableElementEditor)
class SchedulerElementEditor(TableElementEditor):
    """Scheduler element editor"""

    view_name = 'admin'
    modal_target = False

    def __new__(cls, context, request, view):  # pylint: disable=unused-argument
        if not request.has_permission(MANAGE_TASKS_PERMISSION, context=context):
            return None
        return TableElementEditor.__new__(cls)


@viewletmanager_config(name='tasks-list.menu',
                       context=IScheduler, layer=IAdminLayer,
                       manager=ISiteManagementMenu, weight=10,
                       permission=MANAGE_TASKS_PERMISSION,
                       provides=IPropertiesMenu)
class SchedulerTasksListMenu(NavigationMenuItem):
    """Scheduler tasks list menu"""

    label = _("Tasks definition")
    icon_class = 'fa fa-clock'
    href = '#tasks-list.html'


class SchedulerTasksTable(Table):
    """Scheduler tasks table"""

    display_if_empty = True

    @property
    def data_attributes(self):
        attributes = super().data_attributes
        attributes['table'].update({
            'data-ams-order': '2,asc'
        })
        return attributes


@adapter_config(required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IValues)
class SchedulerTasksTableValues(ContextRequestViewAdapter):
    """Scheduler tasks values adapter"""

    @property
    def values(self):
        """Scheduler tasks table values getter"""
        yield from self.context.tasks


@adapter_config(name='active',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class SchedulerTaskActiveColumn(IconColumn):
    """Scheduler task active column"""

    weight = 1

    def get_icon_hint(self, item):
        translate = self.request.localizer.translate
        return translate(_("Enabled task")) if IBaseTaskScheduling(item).active \
            else translate(_("Disabled task"))

    def get_icon_class(self, item):
        return 'far fa-check-square' if IBaseTaskScheduling(item).active \
            else 'far fa-square text-danger'


@adapter_config(name='icon',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class SchedulerTaskIconColumn(IconColumn):
    """Scheduler task icon column"""

    weight = 2

    def get_icon_hint(self, item):
        if not item.label:
            return None
        translate = self.request.localizer.translate
        return translate(item.label)

    def get_icon_class(self, item):
        return item.icon_class or None


@adapter_config(name='name',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class SchedulerTaskNameColumn(NameColumn):
    """Scheduler tasks name column"""


@adapter_config(name='id',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class SchedulerTaskIdColumn(I18nColumnMixin, GetAttrColumn):
    """Scheduler task ID column"""

    i18n_header = _("Task ID")
    attr_name = '__name__'
    weight = 20


@adapter_config(name='trash',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class SchedulerTaskTrashColumn(TrashColumn):
    """Scheduler tasks trash column"""

    permission = MANAGE_TASKS_PERMISSION


@pagelet_config(name='tasks-list.html', context=IScheduler, layer=IPyAMSLayer,
                permission=MANAGE_TASKS_PERMISSION)
class SchedulerTasksView(TableAdminView):
    """Scheduler tasks view"""

    title = _("Scheduler tasks")
    table_class = SchedulerTasksTable
    table_label = _("List of scheduler tasks")


@view_config(name='delete-element.json', context=IScheduler, request_type=IPyAMSLayer,
             permission=MANAGE_TASKS_PERMISSION, renderer='json', xhr=True)
def delete_scheduler_task(request):
    """Delete scheduler task"""
    return delete_container_element(request)
