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

"""PyAMS_scheduler.zmi.task.ssh module

This modules defines SSH task management interface.
"""

from zope.interface import Interface, implementer

from pyams_form.ajax import ajax_form_config
from pyams_form.browser.object import ObjectWidget
from pyams_form.field import Fields
from pyams_form.group import GroupManager
from pyams_form.interfaces import IObjectFactory
from pyams_form.interfaces.form import IForm, IInnerTabForm
from pyams_form.interfaces.widget import IObjectWidget
from pyams_form.subform import InnerAddForm, InnerEditForm
from pyams_form.widget import FieldWidget
from pyams_layer.interfaces import IFormLayer, IPyAMSLayer
from pyams_scheduler.interfaces import IScheduler, MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.task.ssh import ISSHCallTaskInfo, ISSHCallerTask, \
    ISSHConnectionInfo
from pyams_scheduler.task.ssh import SSHConnectionInfo
from pyams_scheduler.zmi import SchedulerTasksTable
from pyams_scheduler.zmi.task import BaseTaskAddForm, BaseTaskEditForm
from pyams_skin.viewlet.menu import MenuItem
from pyams_utils.adapter import adapter_config
from pyams_utils.factory import get_interface_name
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.viewlet import IContextAddingsViewletManager


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


#
# SSH connection object widget
#

@adapter_config(name=get_interface_name(ISSHConnectionInfo),
                required=(Interface, IFormLayer, IForm, IObjectWidget),
                provides=IObjectFactory)
def ssh_connection_factory(*args, **kwargs):  # pylint: disable=unused-argument
    """SSH connection object factory"""
    return SSHConnectionInfo


class SSHConnectionWidget(ObjectWidget):
    """SSH connection widget"""

    def update_widgets(self, set_errors=True):
        super().update_widgets(set_errors)
        password = self.widgets.get('password')  # pylint: disable=no-member
        if password is not None:
            password.autocomplete = 'new-password'


def SSHConnectionFieldWidget(field, request):  # pylint: disable=invalid-name
    """SSH connection field widget"""
    return FieldWidget(field, SSHConnectionWidget(request))


#
# Base SSH task form
#

class ISSHTaskForm(IForm):
    """SSH caller forms common interface"""


@implementer(ISSHTaskForm)
class SSHTaskFormInfo(GroupManager):
    """SSH task form info"""

    title = _("Command settings")
    fields = Fields(ISSHCallTaskInfo)
    fields['connection'].widget_factory = SSHConnectionFieldWidget


#
# SSH task add form
#

@viewlet_config(name='add-ssh-task.menu',
                context=IScheduler, layer=IAdminLayer, view=SchedulerTasksTable,
                manager=IContextAddingsViewletManager, weight=10,
                permission=MANAGE_TASKS_PERMISSION)
class SSHTaskAddMenu(MenuItem):
    """SSH task add menu"""

    label = _("Add local/remote command launcher...")
    href = 'add-ssh-task.html'
    modal_target = True


@ajax_form_config(name='add-ssh-task.html', context=IScheduler, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class SSHTaskAddForm(BaseTaskAddForm):
    """SSH task add form"""

    content_factory = ISSHCallerTask


@adapter_config(name='ssh-task-info.form',
                required=(IScheduler, IAdminLayer, SSHTaskAddForm),
                provides=IInnerTabForm)
class SSHTaskAddFormInfo(SSHTaskFormInfo, InnerAddForm):
    """SSH task add form info"""


#
# SSH task edit form
#

@ajax_form_config(name='properties.html', context=ISSHCallerTask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class SSHTaskEditForm(BaseTaskEditForm):
    """SSH task edit form"""


@adapter_config(name='ssh-task-info.form',
                required=(ISSHCallerTask, IAdminLayer, SSHTaskEditForm),
                provides=IInnerTabForm)
class SSHTaskEditFormInfo(SSHTaskFormInfo, InnerEditForm):
    """SSH task edit form info"""
