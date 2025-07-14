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

from zope.copy import copy
from zope.interface import Interface

from pyams_form.ajax import ajax_form_config
from pyams_form.field import Fields
from pyams_form.interfaces.form import IAJAXFormRenderer, IInnerTabForm
from pyams_form.subform import InnerAddForm, InnerEditForm
from pyams_layer.interfaces import IPyAMSLayer
from pyams_scheduler.interfaces import IScheduler, ITask, MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.folder import ITaskContainer
from pyams_scheduler.interfaces.task import ITaskInfo
from pyams_scheduler.interfaces.task.pipeline import IPipelineTask
from pyams_scheduler.zmi.interfaces import IPipelineTaskContainerTable, ITaskContainerTable
from pyams_skin.viewlet.help import AlertMessage
from pyams_utils.adapter import ContextRequestViewAdapter, adapter_config
from pyams_utils.interfaces import MISSING_INFO
from pyams_utils.intids import get_object_uid
from pyams_utils.registry import query_utility
from pyams_utils.traversing import get_parent
from pyams_zmi.form import AdminModalAddForm, AdminModalEditForm
from pyams_zmi.helper.event import get_json_table_row_add_callback, \
    get_json_table_row_refresh_callback
from pyams_zmi.interfaces import IAdminLayer, IObjectHint, IObjectLabel, TITLE_SPAN_BREAK
from pyams_zmi.interfaces.form import IFormTitle
from pyams_zmi.interfaces.table import ITableElementEditor
from pyams_zmi.table import TableElementEditor
from pyams_zmi.utils import get_object_label

__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


#
# Task history mixin inner form
#

class TaskHistoryHelpMessage(AlertMessage):
    """Task history help message"""

    css_class = 'mb-1 p-2'
    _message = _("You can limit history conservation to a duration or to a number of iterations. "
                 "If both are specified, the first encountered limit will take precedence.")


#
# Base task add form
#


class BaseTaskAddForm(AdminModalAddForm):  # pylint: disable=abstract-method
    """Base task add form"""

    subtitle = _("New task")
    legend = _("New task properties")
    content_label = MISSING_INFO

    fields = Fields(ITaskInfo).select('name', 'schedule_mode')

    def add(self, obj):
        self.context[get_object_uid(obj)] = obj


@adapter_config(name='base-task-info',
                required=(ITaskContainer, IAdminLayer, BaseTaskAddForm),
                provides=IInnerTabForm)
class BaseTaskAddFormInfo(InnerAddForm):
    """Base task add form general information tab"""

    title = _("Task reports")

    fields = Fields(ITaskInfo).select('keep_empty_reports', 'history_duration',
                                      'history_length', 'attach_reports')
    weight = 100

    def update_widgets(self, prefix=None):
        """Widgets update"""
        super().update_widgets(prefix)
        widget = self.widgets.get('history_duration')
        if widget is not None:
            widget.prefix = TaskHistoryHelpMessage(self.context, self.request, self, None)


@adapter_config(required=(ITaskContainer, IAdminLayer, BaseTaskAddForm),
                provides=IFormTitle)
def scheduler_task_add_form_title(context, request, form):
    """Scheduler task add form title"""
    translate = request.localizer.translate
    return TITLE_SPAN_BREAK.format(
        get_object_label(context, request, form),
        translate(form.content_label))


@adapter_config(required=(ITaskContainer, IAdminLayer, BaseTaskAddForm),
                provides=IAJAXFormRenderer)
class TaskAddFormAJAXRenderer(ContextRequestViewAdapter):
    """Base task add form AJAX renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if not changes:
            return None
        return {
            'callbacks': [
                get_json_table_row_add_callback(
                        self.context, self.request,
                        IPipelineTaskContainerTable if IPipelineTask.providedBy(self.context) else ITaskContainerTable,
                        changes)
            ]
        }


#
# Base task edit form
#

@adapter_config(required=(ITask, IPyAMSLayer, Interface),
                provides=IObjectHint)
@adapter_config(required=(IPipelineTask, IPyAMSLayer, Interface),
                provides=IObjectHint)
def task_hint(context, request, view):
    """Task table element hint factory"""
    if not context.label:
        return None
    translate = request.localizer.translate
    return translate(context.label)


@adapter_config(required=(ITask, IPyAMSLayer, Interface),
                provides=IObjectLabel)
def task_label(context, request, view):  # pylint: disable=unused-argument
    """Task table element name factory"""
    return context.name


@adapter_config(name='form-title',
                required=(ITask, IPyAMSLayer, Interface),
                provides=IObjectLabel)
def task_form_label(context, request, view):  # pylint: disable=unused-argument
    """Task table element name factory"""
    translate = request.localizer.translate
    return translate(_("Task: {}")).format(context.name)


@adapter_config(required=(ITask, IAdminLayer, Interface),
                provides=ITableElementEditor)
class TaskTableElementEditor(TableElementEditor):
    """Task table element editor"""

    def __new__(cls, context, request, view):
        if not request.has_permission(MANAGE_TASKS_PERMISSION, context=context):
            return None
        return TableElementEditor.__new__(cls)


class TaskBaseFormMixin:
    """Task base edit form mixin"""

    @property
    def subtitle(self):
        return get_object_label(self.context, self.request, self, name='form-title')


@adapter_config(required=(ITask, IAdminLayer, TaskBaseFormMixin),
                provides=IFormTitle)
def scheduler_task_edit_form_title(context, request, form):
    """Scheduler task edit form title"""
    translate = request.localizer.translate
    scheduler = query_utility(IScheduler)
    task = get_parent(context, ITask)
    return TITLE_SPAN_BREAK.format(
        get_object_label(scheduler, request, form),
        translate(task.label))


class BaseTaskEditForm(TaskBaseFormMixin, AdminModalEditForm):
    """Base task edit form"""

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

    fields = Fields(ITaskInfo).select('keep_empty_reports', 'history_duration',
                                      'history_length', 'attach_reports')
    weight = 100

    def update_widgets(self, prefix=None):
        """Widgets update"""
        super().update_widgets(prefix)
        widget = self.widgets.get('history_duration')
        if widget is not None:
            widget.prefix = TaskHistoryHelpMessage(self.context, self.request, self, None)


@adapter_config(required=(ITask, IAdminLayer, BaseTaskEditForm),
                provides=IAJAXFormRenderer)
class TaskEditFormAJAXRenderer(ContextRequestViewAdapter):
    """Task edit form AJAX renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if not changes:
            return None
        container = get_parent(self.context, ITaskContainer, allow_context=False)
        return {
            'callbacks': [
                get_json_table_row_refresh_callback(
                        container, self.request,
                        IPipelineTaskContainerTable if IPipelineTask.providedBy(container) else ITaskContainerTable,
                        self.context)
            ]
        }


#
# Task clone form
#

@ajax_form_config(name='clone-task.html',
                  context=ITask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class TaskCloneForm(TaskBaseFormMixin, AdminModalAddForm):
    """Task clone form"""

    legend = _("Clone task")

    fields = Fields(ITask).select('name')

    def create(self, data):
        return copy(self.context)

    def add(self, obj):
        self.context.__parent__[get_object_uid(obj)] = obj


@adapter_config(required=(ITask, IAdminLayer, TaskCloneForm),
                provides=IAJAXFormRenderer)
class TaskCloneFormAJAXRenderer(ContextRequestViewAdapter):
    """Task clone form AJAX renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if not changes:
            return None
        container = get_parent(self.context, ITaskContainer, allow_context=False)
        return {
            'callbacks': [
                get_json_table_row_add_callback(
                        container, self.request,
                        IPipelineTaskContainerTable if IPipelineTask.providedBy(container) else ITaskContainerTable,
                        changes)
            ]
        }
