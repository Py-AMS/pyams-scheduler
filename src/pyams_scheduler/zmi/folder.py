#
# Copyright (c) 2015-2023 Thierry Florac <tflorac AT ulthar.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

"""PyAMS_scheduler.zmi.folder module

"""

from pyramid.traversal import lineage
from zope.copy import copy
from zope.interface import Interface

from pyams_form.ajax import ajax_form_config
from pyams_form.field import Fields
from pyams_form.interfaces.form import IAJAXFormRenderer
from pyams_layer.interfaces import IPyAMSLayer
from pyams_scheduler.interfaces import IScheduler, MANAGE_SCHEDULER_PERMISSION
from pyams_scheduler.interfaces.folder import ITaskContainer, ITaskFolder
from pyams_scheduler.interfaces.task import ITask
from pyams_scheduler.interfaces.task.pipeline import IPipelineTask
from pyams_scheduler.zmi import TaskContainerTable
from pyams_scheduler.zmi.interfaces import ITaskContainerTable
from pyams_skin.interfaces.viewlet import IBreadcrumbItem, IFormHeaderViewletManager
from pyams_skin.viewlet.help import AlertMessage
from pyams_skin.viewlet.menu import MenuDivider, MenuItem
from pyams_utils.adapter import ContextRequestViewAdapter, adapter_config
from pyams_utils.finder import find_objects_providing
from pyams_utils.intids import get_object_uid
from pyams_utils.traversing import get_parent
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.form import AdminModalAddForm, AdminModalEditForm
from pyams_zmi.helper.event import get_json_table_row_add_callback, get_json_table_row_refresh_callback
from pyams_zmi.interfaces import IAdminLayer, IObjectHint, IObjectLabel, IPageTitle, TITLE_SPAN, TITLE_SPAN_BREAK
from pyams_zmi.interfaces.form import IFormTitle
from pyams_zmi.interfaces.table import ITableElementEditor
from pyams_zmi.interfaces.viewlet import IContextAddingsViewletManager
from pyams_zmi.table import TableElementEditor
from pyams_zmi.utils import get_object_label
from pyams_zmi.zmi.viewlet.breadcrumb import AdminLayerBreadcrumbItem

__docformat__ = 'restructuredtext'

from pyams_scheduler import _


@viewlet_config(name='add-folder.menu',
                context=ITaskContainer, layer=IAdminLayer, view=ITaskContainerTable,
                manager=IContextAddingsViewletManager, weight=1,
                permission=MANAGE_SCHEDULER_PERMISSION)
class TaskFolderAddMenu(MenuItem):
    """Task folder add menu"""

    label = _("Add folder...")
    href = 'add-folder.html'
    modal_target = True
    
    def __new__(cls, context, request, view, manager):
        if IPipelineTask.providedBy(context):
            return None
        return MenuItem.__new__(cls)


@ajax_form_config(name='add-folder.html',
                  context=ITaskContainer, layer=IPyAMSLayer,
                  permission=MANAGE_SCHEDULER_PERMISSION)
class TaskFolderAddForm(AdminModalAddForm):
    """Task folder add form"""

    subtitle = _("New folder")
    legend = _("New folder properties")

    fields = Fields(ITaskFolder).select('name')
    content_factory = ITaskFolder

    def add(self, obj):
        self.context[get_object_uid(obj)] = obj


@adapter_config(required=(ITaskContainer, IAdminLayer, TaskFolderAddForm),
                provides=IFormTitle)
def task_folder_add_form_title(context, request, form):
    """Task folder add form title"""
    if IScheduler.providedBy(context):
        return TITLE_SPAN.format(get_object_label(context, request, form))
    scheduler = get_parent(context, IScheduler)
    return TITLE_SPAN_BREAK.format(
        get_object_label(scheduler, request, form),
        get_object_label(context, request, form))


@adapter_config(required=(ITaskContainer, IAdminLayer, TaskFolderAddForm),
                provides=IAJAXFormRenderer)
class TaskFolderAddFormAJAXRenderer(ContextRequestViewAdapter):
    """Task folder add form AJAX renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if not changes:
            return None
        return {
            'callbacks': [
                get_json_table_row_add_callback(self.context, self.request,
                                                TaskContainerTable, changes)
            ]
        }


@viewlet_config(name='add-folder.divider',
                context=ITaskContainer, layer=IAdminLayer, view=ITaskContainerTable,
                manager=IContextAddingsViewletManager, weight=2,
                permission=MANAGE_SCHEDULER_PERMISSION)
class TaskFolderAddMenuDivider(MenuDivider):
    """Task folder add menu divider"""
    
    def __new__(cls, context, request, view, manager):
        if IPipelineTask.providedBy(context):
            return None
        return MenuDivider.__new__(cls)


@adapter_config(required=(ITaskFolder, IAdminLayer, Interface),
                provides=IObjectHint)
def task_folder_hint(context, request, view):
    """Task folder hint"""
    translate = request.localizer.translate
    return translate(_("Task folder"))


@adapter_config(required=ITaskFolder,
                provides=IObjectLabel)
def task_folder_label(context):
    """Task folder label"""
    return context.name


@adapter_config(required=(ITaskFolder, IAdminLayer, Interface),
                provides=ITableElementEditor)
class TaskFolderElementEditor(TableElementEditor):
    """Task folder element editor"""

    view_name = 'admin'
    modal_target = False


@adapter_config(required=(ITaskFolder, IAdminLayer, Interface),
                provides=IPageTitle)
def task_folder_title(context, request, view):
    """Task folder view title adapter"""
    scheduler = get_parent(context, IScheduler)
    scheduler_label = get_object_label(scheduler, request, view)
    return (f'{scheduler_label}' +
            ''.join((
                f'<small>'
                f'  <small><i class="px-2 fas fa-chevron-right"></i></small> '
                f'  {get_object_label(element, request, view)}'
                f'</small>'
                for element in reversed(list(lineage(context)))
                if ITaskFolder.providedBy(element)))
            )


@adapter_config(required=(ITaskFolder, IAdminLayer, Interface),
                provides=IBreadcrumbItem)
class TaskFolderBreadcrumbItem(AdminLayerBreadcrumbItem):
    """Task folder breadcrumb item"""

    @property
    def label(self):
        return self.context.name


@ajax_form_config(name='properties.html',
                  context=ITaskFolder,
                  permission=MANAGE_SCHEDULER_PERMISSION)
class TaskFolderPropertiesEditForm(AdminModalEditForm):
    """Task folder properties edit form"""

    legend = _("Folder name")

    fields = Fields(ITaskFolder).select('name')


@adapter_config(required=(ITaskFolder, IAdminLayer, TaskFolderPropertiesEditForm),
                provides=IAJAXFormRenderer)
class TaskFolderPropertiesEditFormAJAXRenderer(ContextRequestViewAdapter):
    """Task folder properties edit form AJAX renderer"""

    def render(self, changes):
        if not changes:
            return None
        container = get_parent(self.context, ITaskContainer, allow_context=False)
        return {
            'callbacks': [
                get_json_table_row_refresh_callback(container, self.request,
                                                    TaskContainerTable, self.context)
            ]
        }


@ajax_form_config(name='clone-folder.html',
                  context=ITaskFolder,
                  permission=MANAGE_SCHEDULER_PERMISSION)
class TaskFolderCloneForm(AdminModalAddForm):
    """Task folder clone form"""

    legend = _("Clone folder")

    fields = Fields(ITaskFolder).select('name')

    def create(self, data):
        return copy(self.context)

    def add(self, obj):
        self.context.__parent__[get_object_uid(obj)] = obj
        for task in list(find_objects_providing(obj, ITask)):
            name = task.__name__
            parent = task.__parent__
            parent[get_object_uid(task)] = task
            del parent[name]


@viewlet_config(name='clone-folder.help',
                context=ITaskFolder, layer=IAdminLayer, view=TaskFolderCloneForm,
                manager=IFormHeaderViewletManager, weight=10)
class TaskFolderCloneFormHelp(AlertMessage):
    """Task folder clone form help"""

    status = 'warning'
    _message = _("WARNING: this will duplicate the folder and all it's content, including "
                 "tasks and inner folders; copied tasks will be automatically disabled")


@adapter_config(required=(ITaskFolder, IAdminLayer, TaskFolderCloneForm),
                provides=IAJAXFormRenderer)
class TaskFolderCloneFormAJAXRenderer(ContextRequestViewAdapter):
    """Task folder clone form AJAX renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if changes is None:
            return None
        container = get_parent(self.context, ITaskContainer, allow_context=False)
        return {
            'callbacks': [
                get_json_table_row_add_callback(container, self.request,
                                                TaskContainerTable, changes)
            ]
        }
