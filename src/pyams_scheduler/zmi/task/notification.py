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

"""PyAMS_scheduler.task.zmi.notification module

This module provides components used to manage tasks notifications.
"""

from pyramid.view import view_config
from zope.interface import Interface
from zope.intid import IIntIds

from pyams_form.ajax import ajax_form_config
from pyams_form.field import Fields
from pyams_form.interfaces.form import IAJAXFormRenderer
from pyams_layer.interfaces import IPyAMSLayer
from pyams_pagelet.pagelet import pagelet_config
from pyams_scheduler.interfaces import IScheduler, ITask, MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.task import IMailNotification, ITaskNotification, \
    ITaskNotificationContainer
from pyams_scheduler.zmi import SchedulerTasksTable
from pyams_skin.interfaces.viewlet import IContentPrefixViewletManager
from pyams_skin.viewlet.menu import MenuItem
from pyams_table.interfaces import IColumn, IValues
from pyams_utils.adapter import ContextRequestViewAdapter, adapter_config
from pyams_utils.data import ObjectDataManagerMixin
from pyams_utils.registry import get_utility
from pyams_utils.traversing import get_parent
from pyams_utils.url import absolute_url
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.form import AdminModalAddForm, AdminModalDisplayForm, AdminModalEditForm
from pyams_zmi.helper.container import delete_container_element, switch_element_attribute
from pyams_zmi.helper.event import get_json_table_row_add_callback, \
    get_json_table_row_refresh_callback
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.table import ITableElementEditor
from pyams_zmi.interfaces.viewlet import IContextAddingsViewletManager
from pyams_zmi.table import ActionColumn, IconColumn, InnerTableAdminView, JsActionColumn, \
    NameColumn, Table, TableElementEditor, TrashColumn


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@adapter_config(name='notifications',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class TaskNotificationsColumn(ActionColumn):
    """Task notifications column"""

    hint = _("Task notifications")
    icon_class = 'far fa-envelope'

    href = 'notifications.html'

    weight = 35


@pagelet_config(name='notifications.html',
                context=ITask, layer=IPyAMSLayer,
                permission=MANAGE_TASKS_PERMISSION)
class TaskNotificationsView(AdminModalDisplayForm):
    """Task notifications view"""

    @property
    def title(self):
        """Title getter"""
        return self.context.name


#
# Task notifications table
#

class TaskNotificationsTable(Table):
    """Task notifications table"""

    @property
    def data_attributes(self):
        attributes = super().data_attributes
        container = ITaskNotificationContainer(self.context)
        attributes['table'].update({
            'data-ams-location': absolute_url(container, self.request),
            'data-ams-order': '1,asc'
        })
        return attributes

    display_if_empty = True


@adapter_config(required=(ITask, IAdminLayer, TaskNotificationsTable),
                provides=IValues)
class TaskNotificationsTableValues(ContextRequestViewAdapter):
    """Task notifications table values adapter"""

    @property
    def values(self):
        """Task notifications table values getter"""
        yield from ITaskNotificationContainer(self.context).values()


@adapter_config(name='enabled',
                required=(ITask, IAdminLayer, TaskNotificationsTable),
                provides=IColumn)
class TaskNotificationsTableEnabledColumn(ObjectDataManagerMixin, JsActionColumn):
    """Task notifications table enabled column"""

    hint = _("Click icon to enable or disable notification")

    href = 'MyAMS.container.switchElementAttribute'
    modal_target = False

    object_data = {
        'ams-modules': 'container',
        'ams-update-target': 'switch-active-notification.json',
        'ams-attribute-name': 'enabled',
        'ams-icon-on': 'far fa-bell',
        'ams-icon-off': 'far fa-bell-slash'
    }

    weight = 1

    def get_icon_class(self, item):
        """Icon class getter"""
        return 'far fa-bell' if item.enabled else 'far fa-bell-slash'


@view_config(name='switch-active-notification.json',
             context=ITaskNotificationContainer, request_type=IPyAMSLayer,
             renderer='json', xhr=True)
def switch_active_notification(request):
    """Switch active notification"""
    return switch_element_attribute(request)


@adapter_config(name='label',
                required=(ITask, IAdminLayer, TaskNotificationsTable),
                provides=IColumn)
class TaskNotificationsTableNameColumn(NameColumn):
    """Task notifications table label column"""

    i18n_header = _("Target")


@adapter_config(name='send-errors-only',
                required=(ITask, IAdminLayer, TaskNotificationsTable),
                provides=IColumn)
class TaskNotificationsTableErrorsColumn(IconColumn):
    """Task notifications table errors-only column"""

    icon_class = 'fas fa-bug'
    hint = _("Send errors reports only")

    weight = 50

    def get_icon_class(self, item):
        """Icon class getter"""
        if item.report_errors_only:
            return self.icon_class
        return '{} text-secondary'.format(self.icon_class)

    def get_icon_hint(self, item):
        """Icon hint getter"""
        hint = self.hint if item.report_errors_only else _("Send all reports")
        return self.request.localizer.translate(hint)


@adapter_config(name='send-empty',
                required=(ITask, IAdminLayer, TaskNotificationsTable),
                provides=IColumn)
class TaskNotificationsTableEmptyColumn(IconColumn):
    """Task notifications table empty reports column"""

    icon_class = 'far fa-file'
    hint = _("Send empty reports")

    weight = 55

    def get_icon_class(self, item):
        """Icon class getter"""
        if item.send_empty_reports:
            return self.icon_class
        return '{} text-secondary'.format(self.icon_class)

    def get_icon_hint(self, item):
        """Icon hint getter"""
        hint = self.hint if item.send_empty_reports else _("Don't send empty reports")
        return self.request.localizer.translate(hint)


@adapter_config(name='trash',
                required=(ITask, IAdminLayer, TaskNotificationsTable),
                provides=IColumn)
class TaskNotificationsTableTrashColumn(TrashColumn):
    """Task notifications table trash column"""


@view_config(name='delete-element.json',
             context=ITaskNotificationContainer, request_type=IPyAMSLayer,
             renderer='json', xhr=True,
             permission=MANAGE_TASKS_PERMISSION)
def delete_task_notification(request):
    """Delete task notification"""
    return delete_container_element(request)


#
# Task notifications table view
#

@viewlet_config(name='task-notifications-table',
                context=ITask, layer=IAdminLayer, view=TaskNotificationsView,
                manager=IContentPrefixViewletManager, weight=10)
class TaskNotificationsTableView(InnerTableAdminView):
    """Task notifications table view"""

    title = _("Task notifications")
    table_class = TaskNotificationsTable
    table_label = _("List of defined task notifications")


#
# Base notifications add and edit forms
#

class TaskNotificationAddForm(AdminModalAddForm):
    """Base task notification add form"""

    legend = _("New notification properties")

    def add(self, obj):
        intids = get_utility(IIntIds)
        container = ITaskNotificationContainer(self.context)
        container[hex(intids.register(obj))[2:]] = obj


@adapter_config(required=(ITask, IAdminLayer, TaskNotificationAddForm),
                provides=IAJAXFormRenderer)
class TaskNotificationAddFormRenderer(ContextRequestViewAdapter):
    """Task notification add form AJAX renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if not changes:
            return None
        return {
            'callbacks': [
                get_json_table_row_add_callback(self.context, self.request,
                                                TaskNotificationsTable, changes)
            ]
        }


@adapter_config(required=(ITaskNotification, IAdminLayer, Interface),
                provides=ITableElementEditor)
class TaskNotificationEditor(TableElementEditor):
    """Task notification editor adapter"""


class TaskNotificationEditForm(AdminModalEditForm):
    """Base task notification edit form"""

    legend = _("Notification properties")


@adapter_config(required=(ITaskNotification, IAdminLayer, TaskNotificationEditForm),
                provides=IAJAXFormRenderer)
class TaskNotificationEditFormRenderer(ContextRequestViewAdapter):
    """Task notification edit form renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if changes is None:
            return None
        task = get_parent(self.context, ITask)
        return {
            'status': 'success',
            'message': self.request.localizer.translate(self.view.success_message),
            'callbacks': [
                get_json_table_row_refresh_callback(task, self.request,
                                                    TaskNotificationsTable, self.context)
            ]
        }


#
# Mail notifications views
#

@viewlet_config(name='add-mail-notification.menu',
                context=ITask, layer=IAdminLayer, view=TaskNotificationsTable,
                manager=IContextAddingsViewletManager, weight=10,
                permission=MANAGE_TASKS_PERMISSION)
class MailNotificationAddMenu(MenuItem):
    """Mail notification add menu"""

    label = _("Add mail notification...")
    href = 'add-mail-notification.html'
    modal_target = True

    def get_href(self):
        """Link URL getter"""
        return absolute_url(self.context, self.request, self.href)


@ajax_form_config(name='add-mail-notification.html',
                  context=ITask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class MailNotificationAddForm(TaskNotificationAddForm):
    """Mail notification add form"""

    title = _("Add new mail notification")

    fields = Fields(IMailNotification).omit('__name__', '__parent__', 'enabled')
    content_factory = IMailNotification


@ajax_form_config(name='properties.html',
                  context=ITaskNotification, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class MailNotificationEditForm(TaskNotificationEditForm):
    """Mail notification edit form"""

    fields = Fields(IMailNotification).omit('__name__', '__parent__', 'enabled')
