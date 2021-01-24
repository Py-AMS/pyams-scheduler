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

"""PyAMS_scheduler.zmi.task base module

This module defines base tasks management forms.
"""

from zope.interface import Interface
from zope.intid import IIntIds

from pyams_form.browser.checkbox import SingleCheckBoxFieldWidget
from pyams_form.field import Fields
from pyams_form.interfaces.form import IAJAXFormRenderer, IInnerTabForm
from pyams_form.subform import InnerAddForm, InnerEditForm
from pyams_scheduler.interfaces import IScheduler, ITask, ITaskInfo
from pyams_scheduler.zmi import SchedulerTasksTable
from pyams_skin.viewlet.help import AlertMessage
from pyams_utils.adapter import ContextRequestViewAdapter, adapter_config
from pyams_utils.registry import get_utility
from pyams_zmi.form import AdminModalAddForm, AdminModalEditForm
from pyams_zmi.helper.event import get_json_table_row_refresh_callback
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.table import ITableElementEditor, ITableElementName
from pyams_zmi.table import TableElementEditor


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


#
# Base task add form
#

class BaseTaskAddForm(AdminModalAddForm):  # pylint: disable=abstract-method
    """Base task add form"""

    title = _("Add new task")
    legend = _("New task properties")

    fields = Fields(ITaskInfo).select('name', 'schedule_mode')

    def add(self, obj):
        intids = get_utility(IIntIds)
        self.context[hex(intids.register(obj))[2:]] = obj


@adapter_config(name='base-task-info',
                required=(IScheduler, IAdminLayer, BaseTaskAddForm),
                provides=IInnerTabForm)
class BaseTaskAddFormInfo(InnerAddForm):
    """Base task add form general information tab"""

    title = _("Task reports")

    fields = Fields(ITaskInfo).omit('__parent__', '__name__', 'name', 'schedule_mode')
    weight = 100


#
# Base task edit form
#

@adapter_config(required=ITask, provides=ITableElementName)
def task_element_name_factory(context):
    """Task table element name factory"""
    return context.name


@adapter_config(required=(ITask, IAdminLayer, Interface),
                provides=ITableElementEditor)
class TaskTableElementEditor(TableElementEditor):
    """Task table element editor"""


class BaseTaskEditForm(AdminModalEditForm):
    """Base task edit form"""

    @property
    def title(self):
        """Title getter"""
        return self.context.name

    legend = _("Task properties")

    fields = Fields(ITaskInfo).select('name', 'schedule_mode')

    def apply_changes(self, data):
        changes = super().apply_changes(data)
        if changes:
            self.context.reset()
        return changes


@adapter_config(name='base-task-info',
                required=(ITask, IAdminLayer, BaseTaskEditForm),
                provides=IInnerTabForm)
class BaseTaskEditFormInfo(InnerEditForm):
    """Base task edit form general information tab"""

    title = _("Task reports")

    fields = Fields(ITaskInfo).omit('__parent__', '__name__', 'name', 'schedule_mode')
    weight = 100

    def update_widgets(self, prefix=None):
        super().update_widgets(prefix)
        widget = self.widgets.get('history_duration')
        if widget is not None:
            widget.prefix = TaskHistoryHelpMessage(self.context, self.request, self, None)


class TaskHistoryHelpMessage(AlertMessage):
    """Task history help message"""

    css_class = 'mb-1 p-2'
    _message = _("You can limit history conservation to a duration or to a number of iterations. "
                 "If both are specified, the first encountered limit will take precedence.")


@adapter_config(required=(ITask, IAdminLayer, BaseTaskEditForm),
                provides=IAJAXFormRenderer)
class TaskEditFormAJAXRenderer(ContextRequestViewAdapter):
    """Task edit form AJAX renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if not changes:
            return None
        task = self.view.context
        return {
            'callbacks': [
                get_json_table_row_refresh_callback(task.__parent__, self.request,
                                                    SchedulerTasksTable, task)
            ]
        }
