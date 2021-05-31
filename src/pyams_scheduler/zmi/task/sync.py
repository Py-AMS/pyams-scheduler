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

"""PyAMS_scheduler.zmi.task.sync module

This module defines the management interface components of directory
synchronization tasks.
"""

from zope.component import getAdapters
from zope.interface import Interface, implementer, implementer_only

from pyams_form.ajax import ajax_form_config
from pyams_form.browser.widget import HTMLFormElement
from pyams_form.converter import BaseDataConverter
from pyams_form.field import Fields
from pyams_form.group import GroupManager
from pyams_form.interfaces import IDataConverter, IObjectFactory
from pyams_form.interfaces.form import IForm, IInnerTabForm
from pyams_form.interfaces.widget import IFieldWidget, IObjectWidget
from pyams_form.subform import InnerAddForm, InnerEditForm
from pyams_form.widget import FieldWidget, Widget
from pyams_layer.interfaces import IFormLayer, IPyAMSLayer
from pyams_scheduler.interfaces import IScheduler, MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.task.sync import IDirectoryHandler, IDirectoryHandlerHostField, \
    IDirectoryInfo, IDirectorySyncTask, IDirectorySyncTaskInfo
from pyams_scheduler.task.sync import DirectoryInfo
from pyams_scheduler.zmi import SchedulerTasksTable
from pyams_scheduler.zmi.interfaces import IDirectoryHandlerHostWidget
from pyams_scheduler.zmi.task import BaseTaskAddForm, BaseTaskEditForm
from pyams_skin.viewlet.menu import MenuItem
from pyams_utils.adapter import adapter_config
from pyams_utils.factory import get_interface_name
from pyams_utils.interfaces.form import NO_VALUE
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.viewlet import IContextAddingsViewletManager


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@adapter_config(name=get_interface_name(IDirectoryInfo),
                required=(Interface, IFormLayer, IForm, IObjectWidget),
                provides=IObjectFactory)
def directory_info_factory(*args):  # pylint: disable=unused-argument
    """Directory info object factory"""
    return DirectoryInfo


#
# Directory handler host widget
#

@adapter_config(required=(IDirectoryHandlerHostField, IDirectoryHandlerHostWidget),
                provides=IDataConverter)
class DirectoryHandlerHostDataConverter(BaseDataConverter):
    """Directory handler host data converter"""

    def to_widget_value(self, value):
        return value

    def to_field_value(self, value):
        return value


@implementer_only(IDirectoryHandlerHostWidget)
class DirectoryHandlerHostWidget(HTMLFormElement, Widget):
    """Directory handler host getter widget"""

    @property
    def display_value(self):
        """Display value getter"""
        return self.value or (None, None)

    def extract(self, default=NO_VALUE):
        params = self.request.params
        marker = params.get('{}-empty-marker'.format(self.name), default)
        if marker is not default:
            protocol = params.get('{}-protocol'.format(self.name))
            hostname = params.get('{}-hostname'.format(self.name))
            return (protocol, hostname) if protocol else default
        return default

    @property
    def protocols(self):
        """Getter of supported protocols"""
        info = DirectoryInfo()
        yield from sorted(name for name, adapter in getAdapters((info,), IDirectoryHandler))


@adapter_config(required=(IDirectoryHandlerHostField, IFormLayer),
                provides=IFieldWidget)
def DirectoryHandlerHostFieldWidget(field, request):  # pylint: disable=invalid-name
    """Directory handler host widget factory"""
    return FieldWidget(field, DirectoryHandlerHostWidget(request))


#
# Directory synchronization base form
#

class IDirectorySyncTaskForm(IForm):
    """Directory synchronization forms interface"""


@implementer(IDirectorySyncTaskForm)
class DirectorySyncTaskFormInfo(GroupManager):
    """Directory synchronization task form info"""

    title = _("Synchronization settings")

    fields = Fields(IDirectorySyncTaskInfo)


#
# Directory synchronization task add form
#

@viewlet_config(name='add-sync-task.menu',
                context=IScheduler, layer=IAdminLayer, view=SchedulerTasksTable,
                manager=IContextAddingsViewletManager, weight=40,
                permission=MANAGE_TASKS_PERMISSION)
class DirectorySyncTaskAddMenu(MenuItem):
    """Directory synchronization task add menu"""

    label = _("Add directory synchronization...")
    href = 'add-sync-task.html'
    modal_target = True


@ajax_form_config(name='add-sync-task.html', context=IScheduler, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class DirectorySyncTaskAddForm(BaseTaskAddForm):
    """Directory synchronization task add form"""

    content_factory = IDirectorySyncTask


@adapter_config(name='sync-task-info.form',
                required=(IScheduler, IAdminLayer, DirectorySyncTaskAddForm),
                provides=IInnerTabForm)
class DirectorySyncTaskAddFormInfo(DirectorySyncTaskFormInfo, InnerAddForm):
    """Directory synchronization task add form info"""


#
# Directory synchronization task edit form
#

@ajax_form_config(name='properties.html', context=IDirectorySyncTask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class DirectorySyncTaskEditForm(BaseTaskEditForm):
    """Directory synchronization task edit form"""


@adapter_config(name='sync-task-info.form',
                required=(IDirectorySyncTask, IAdminLayer, DirectorySyncTaskEditForm),
                provides=IInnerTabForm)
class DirectorySyncTaskEditFormInfo(DirectorySyncTaskFormInfo, InnerEditForm):
    """Directory synchronization task edit form info"""
