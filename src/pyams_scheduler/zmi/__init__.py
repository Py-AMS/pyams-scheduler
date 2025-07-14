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

import json
from itertools import chain

from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.view import view_config
from zope.interface import Interface, implementer

from pyams_layer.interfaces import IPyAMSLayer
from pyams_layer.skin import apply_skin
from pyams_pagelet.pagelet import pagelet_config
from pyams_scheduler.interfaces import IBaseTaskScheduling, IScheduler, ITask, MANAGE_TASKS_PERMISSION, TASKS_SCHEDULER_LABEL
from pyams_scheduler.interfaces.folder import ITaskContainer, ITaskFolder
from pyams_scheduler.interfaces.task.pipeline import IPipelineTask
from pyams_scheduler.zmi.interfaces import ITaskContainerTable
from pyams_security.interfaces.base import VIEW_SYSTEM_PERMISSION
from pyams_table.column import GetAttrColumn
from pyams_table.interfaces import IColumn, IValues
from pyams_utils.adapter import ContextRequestViewAdapter, adapter_config
from pyams_utils.factory import factory_config
from pyams_utils.list import unique_iter
from pyams_utils.url import absolute_url
from pyams_viewlet.manager import viewletmanager_config
from pyams_zmi.helper.container import delete_container_element
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.table import ITableElementEditor
from pyams_zmi.interfaces.viewlet import IMenuHeader, IPropertiesMenu, ISiteManagementMenu
from pyams_zmi.skin import AdminSkin
from pyams_zmi.table import ActionColumn, I18nColumnMixin, IconColumn, NameColumn, Table, TableAdminView, \
    TableElementEditor, TrashColumn
from pyams_zmi.utils import get_object_hint
from pyams_zmi.zmi.viewlet.menu import NavigationMenuItem

__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@adapter_config(required=(IScheduler, IAdminLayer, Interface, ISiteManagementMenu),
                provides=IMenuHeader)
def scheduler_menu_header(context, request, view, manager):  # pylint: disable=unused-argument
    """Scheduler menu header"""
    return TASKS_SCHEDULER_LABEL


@adapter_config(required=(IScheduler, IAdminLayer, Interface),
                provides=ITableElementEditor)
class SchedulerElementEditor(TableElementEditor):
    """Scheduler element editor"""

    view_name = 'admin'
    modal_target = False

    def __new__(cls, context, request, view):  # pylint: disable=unused-argument
        if not request.has_permission(VIEW_SYSTEM_PERMISSION, context=context):
            return None
        return TableElementEditor.__new__(cls)


#
# Task container view
#

@viewletmanager_config(name='tasks-list.menu',
                       context=ITaskContainer, layer=IAdminLayer,
                       manager=ISiteManagementMenu, weight=10,
                       permission=VIEW_SYSTEM_PERMISSION,
                       provides=IPropertiesMenu)
class TaskContainerListMenu(NavigationMenuItem):
    """Task container list menu"""

    label = _("Tasks definition")
    icon_class = 'fa fa-clock'
    href = '#tasks-list.html'


@factory_config(ITaskContainerTable)
class TaskContainerTable(Table):
    """Scheduler tasks table"""

    sort_on = 'table-name-2'
    display_if_empty = True

    @property
    def css_classes(self):
        classes = super().css_classes.copy()
        classes.update({
            'thead': 'droppable' if ITaskFolder.providedBy(self.context) else '',
            'tr': 'draggable'
        })
        return classes

    @reify
    def data_attributes(self):
        attributes = super().data_attributes
        attributes['table'].update({
            'data-ams-modules': 'container',
            'data-ams-order': '2,asc',
            'data-ams-drop-action': 'change-parent.json'
        })
        attributes.setdefault('thead', {}).update({
            'data-ams-droppable-classes': json.dumps({
                'ui-droppable-active': 'bg-secondary',
                'ui-droppable-hover': 'bg-light'
            }),
            'data-ams-droppable-drop': 'MyAMS.container.moveToGrandParent',
            'data-ams-drop-action': 'move-to-parent.json'
        })
        attributes.setdefault('tr', {}).update({
            'data-ams-draggable-axis': 'y',
            'data-ams-draggable-containment': '.table',
            'data-ams-draggable-delay': 50,
            'data-ams-draggable-revert': 'invalid',
            'data-ams-draggable-revert-duration': 250,
            'data-ams-droppable-classes': json.dumps({
                'ui-droppable-active': 'bg-secondary',
                'ui-droppable-hover': 'bg-light'
            }),
            'data-ams-droppable-drop': 'MyAMS.container.moveToNewParent'
        })
        return attributes

    def render_row(self, row, css_class=None):
        item, _col, _colspan = row[0]
        return super().render_row(row, css_class='droppable' if ITaskFolder.providedBy(item) else None)


@adapter_config(required=(ITaskContainer, IAdminLayer, TaskContainerTable),
                provides=IValues)
class TaskContainerTableValues(ContextRequestViewAdapter):
    """Task container values adapter"""

    @property
    def values(self):
        """Scheduler tasks table values getter"""
        yield from unique_iter(chain(self.context.folders, self.context.tasks))


@adapter_config(name='active',
                required=(ITaskContainer, IAdminLayer, TaskContainerTable),
                provides=IColumn)
class TaskContainerActiveColumn(IconColumn):
    """Scheduler task active column"""

    def __new__(cls, context, request, table):
        if IPipelineTask.providedBy(context):
            return None
        return IconColumn.__new__(cls)
    
    weight = 1

    checker = ITask.providedBy

    def get_icon_hint(self, item):
        translate = self.request.localizer.translate
        return translate(_("Enabled task")) if IBaseTaskScheduling(item).active \
            else translate(_("Disabled task"))

    def get_icon_class(self, item):
        return 'far fa-check-square' if IBaseTaskScheduling(item).active \
            else 'far fa-square text-danger'


@adapter_config(name='icon',
                required=(ITaskContainer, IAdminLayer, TaskContainerTable),
                provides=IColumn)
class TaskContainerIconColumn(IconColumn):
    """Task container icon column"""

    weight = 2

    def get_icon_hint(self, item):
        return get_object_hint(item, self.request, self.table)

    def get_icon_class(self, item):
        return getattr(item, 'icon_class', None)


@adapter_config(name='name',
                required=(ITaskContainer, IAdminLayer, TaskContainerTable),
                provides=IColumn)
class TaskContainerNameColumn(NameColumn):
    """Task container name column"""


@adapter_config(name='id',
                required=(ITaskContainer, IAdminLayer, TaskContainerTable),
                provides=IColumn)
class TaskContainerIdColumn(I18nColumnMixin, GetAttrColumn):
    """Task container ID column"""

    i18n_header = _("Task ID")
    attr_name = '__name__'
    weight = 20
    
    def get_value(self, obj):
        if ITaskContainer.providedBy(obj):
            translate = self.request.localizer.translate
            return translate(_("({} elements)")).format(len(obj))
        return super().get_value(obj)


@adapter_config(name='clone',
                required=(ITaskContainer, IAdminLayer, TaskContainerTable),
                provides=IColumn)
class TaskContainerCloneColumn(ActionColumn):
    """Task container clone column"""

    folder_hint = _("Clone folder")
    task_hint = _("Clone task")

    icon_class = 'far fa-clone'

    def has_permission(self, item):
        return self.request.has_permission(MANAGE_TASKS_PERMISSION, context=item)

    def get_icon_hint(self, item):
        translate = self.request.localizer.translate
        if ITaskFolder.providedBy(item):
            return translate(self.folder_hint)
        return translate(self.task_hint)

    def get_url(self, item):
        href = 'clone-task.html' if ITask.providedBy(item) else 'clone-folder.html'
        return absolute_url(item, self.request, href)

    weight = 100


@adapter_config(name='trash',
                required=(ITaskContainer, IAdminLayer, TaskContainerTable),
                provides=IColumn)
class TaskContainerTrashColumn(TrashColumn):
    """Task container trash column"""

    permission = MANAGE_TASKS_PERMISSION


@pagelet_config(name='tasks-list.html',
                context=ITaskContainer, layer=IPyAMSLayer,
                permission=VIEW_SYSTEM_PERMISSION)
class TaskContainerView(TableAdminView):
    """Task container view"""

    title = _("Scheduler tasks")
    table_class = ITaskContainerTable
    table_label = _("List of scheduler tasks")

    @property
    def back_url(self):
        """Form back URL getter"""
        if IScheduler.providedBy(self.context):
            return absolute_url(self.request.root, self.request, 'admin#utilities.html')  # pylint: disable=no-member
        return absolute_url(self.context.__parent__, self.request, 'admin')

    back_url_target = None


@view_config(name='change-parent.json',
             context=ITaskContainer, request_type=IPyAMSLayer,
             permission=MANAGE_TASKS_PERMISSION,
             renderer='json', xhr=True)
def change_parent(request):
    """Update task parent"""
    apply_skin(request, AdminSkin)
    container = ITaskContainer(request.context)
    source_name = request.params.get('source')
    if (not source_name) or (source_name not in container):
        raise HTTPNotFound
    parent_name = request.params.get('parent')
    if (not parent_name) or (parent_name not in container):
        raise HTTPNotFound
    source = container[source_name]
    parent = container[parent_name]
    parent[source.__name__] = source
    del container[source.__name__]
    if ITask.providedBy(source):
        source.reset()
    return {
        'status': 'reload'
    }


@view_config(name='move-to-parent.json',
             context=ITaskContainer, request_type=IPyAMSLayer,
             permission=MANAGE_TASKS_PERMISSION,
             renderer='json', xhr=True)
def move_to_parent(request):
    """Move element to grandparent"""
    apply_skin(request, AdminSkin)
    container = ITaskContainer(request.context)
    source_name = request.params.get('source')
    if (not source_name) or (source_name not in container):
        raise HTTPNotFound
    parent = container.__parent__
    if not ITaskContainer.providedBy(parent):
        raise HTTPBadRequest
    source = container[source_name]
    parent[source.__name__] = source
    del container[source.__name__]
    if ITask.providedBy(source):
        source.reset()
    return {
        'status': 'success'
    }


@view_config(name='delete-element.json',
             context=ITaskContainer, request_type=IPyAMSLayer,
             permission=MANAGE_TASKS_PERMISSION,
             renderer='json', xhr=True)
def delete_container_task(request):
    """Delete scheduler task"""
    return delete_container_element(request)
