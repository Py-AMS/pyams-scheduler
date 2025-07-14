# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

from pyramid.decorator import reify
from pyramid.view import view_config

from pyams_form.ajax import ajax_form_config
from pyams_form.field import Fields
from pyams_form.interfaces.form import IFormContent, IGroup
from pyams_layer.interfaces import IPyAMSLayer
from pyams_pagelet.pagelet import pagelet_config
from pyams_scheduler.interfaces import ITask, MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.folder import ITaskContainer
from pyams_scheduler.interfaces.task.pipeline import IPipelineInput, IPipelineTask
from pyams_scheduler.task.pipeline import PipelineTask
from pyams_scheduler.task.zmi import BaseTaskAddForm, BaseTaskEditForm
from pyams_scheduler.task.zmi.interfaces import ITaskInnerEditForm
from pyams_scheduler.zmi import ITaskContainerTable, TaskContainerTable, TaskContainerView
from pyams_scheduler.zmi.interfaces import IPipelineTaskContainerTable
from pyams_security.interfaces.base import VIEW_SYSTEM_PERMISSION
from pyams_skin.viewlet.menu import MenuDivider, MenuItem
from pyams_table.interfaces import IColumn
from pyams_utils.adapter import adapter_config
from pyams_utils.factory import factory_config
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.form import FormGroupSwitcher
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.viewlet import IContextAddingsViewletManager
from pyams_zmi.table import ReorderColumn, get_ordered_data_attributes

__docformat__ = 'restructuredtext'

from pyams_scheduler import _


@viewlet_config(name='add-pipeline-task.divider',
                context=ITaskContainer, layer=IAdminLayer, view=TaskContainerTable,
                manager=IContextAddingsViewletManager, weight=899,
                permission=MANAGE_TASKS_PERMISSION)
class PipelineTaskAddMenuDivider(MenuDivider):
    """Pipeline task add menu divider"""
    
    def __new__(cls, context, request, view, manager):
        if IPipelineTask.providedBy(context):
            return None
        return MenuDivider.__new__(cls)


@viewlet_config(name='add-pipeline-task.menu',
                context=ITaskContainer, layer=IAdminLayer, view=TaskContainerTable,
                manager=IContextAddingsViewletManager, weight=900,
                permission=MANAGE_TASKS_PERMISSION)
class PipelineTaskAddMenu(MenuItem):
    """Pipeline task add menu"""
    
    label = _("Add pipeline task...")
    href = 'add-pipeline-task.html'
    modal_target = True
    
    def __new__(cls, context, request, view, manager):
        if IPipelineTask.providedBy(context):
            return None
        return MenuItem.__new__(cls)


class PipelineTaskFormInfo:
    """Pipeline task form info"""
    
    
@ajax_form_config(name='add-pipeline-task.html',
                  context=ITaskContainer, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class PipelineTaskAddFormInfo(BaseTaskAddForm):
    """Pipeline task add form info"""
    
    content_factory = IPipelineTask
    content_label = PipelineTask.label


@ajax_form_config(name='properties.html',
                  context=IPipelineTask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class PipelineTaskEditForm(BaseTaskEditForm):
    """Pipeline task edit form"""
    

@factory_config(IPipelineTaskContainerTable)
class PipelineTaskContainerTable(TaskContainerTable):
    """Pipeline task container table"""
    
    container_class = IPipelineTask
    
    @reify
    def data_attributes(self):
        attributes = super().data_attributes
        container = self.container_class(self.context)
        get_ordered_data_attributes(self, attributes, container, self.request)
        return attributes
    
    
@pagelet_config(name='tasks-list.html',
                context=IPipelineTask, layer=IPyAMSLayer,
                permission=VIEW_SYSTEM_PERMISSION)
class PipelineTaskContainerView(TaskContainerView):
    """Pipeline task container view"""

    table_class = IPipelineTaskContainerTable

    
@adapter_config(name='reorder',
                required=(IPipelineTask, IAdminLayer, ITaskContainerTable),
                provides=IColumn)
class PipelineTaskReorderColumn(ReorderColumn):
    """Pipeline task reorder column"""
    
    
@view_config(name='reorder.json',
             context=IPipelineTask, request_type=IPyAMSLayer,
             renderer='json', xhr=True,
             permission=MANAGE_TASKS_PERMISSION)
def reorder_pipeline_tasks(request):
    """Reorder pipeline tasks"""
    order = request.params.get('order').split(';')
    request.context.updateOrder(order)
    return {
        'status': 'success',
        'closeForm': False
    }


#
# Task pipeline input
#

@adapter_config(name='pipeline-input',
                required=(ITask, IAdminLayer, ITaskInnerEditForm),
                provides=IGroup)
class TaskPipelineInputSubForm(FormGroupSwitcher):
    """Task pipeline input sub form"""
    
    def __new__(cls, context, request, view):
        if not IPipelineTask.providedBy(context.__parent__):
            return None
        return FormGroupSwitcher.__new__(cls)
    
    legend = _("Pipeline input")
    fields = Fields(IPipelineInput)
    
    weight = 10
    
    
@adapter_config(required=(ITask, IAdminLayer, TaskPipelineInputSubForm),
                provides=IFormContent)
def task_pipeline_input_form_content(context, request, view):
    """Pipeline task input form content"""
    return IPipelineInput(context)
    