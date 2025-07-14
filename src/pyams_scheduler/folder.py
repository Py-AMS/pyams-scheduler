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

"""PyAMS_scheduler.task.folder module

This module defines the TaskFolder component, which is a task container.
"""

from zope.container.folder import Folder
from zope.interface import implementer
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.interfaces import ITask, ITaskContainerRoles, MANAGE_SCHEDULER_PERMISSION
from pyams_scheduler.interfaces.folder import ITaskContainer, ITaskFolder
from pyams_security.interfaces import IDefaultProtectionPolicy, IRolesPolicy, IViewContextPermissionChecker
from pyams_security.property import RolePrincipalsFieldProperty
from pyams_security.security import ProtectedObjectMixin, ProtectedObjectRoles
from pyams_utils.adapter import ContextAdapter, adapter_config
from pyams_utils.factory import factory_config

__docformat__ = 'restructuredtext'

from pyams_scheduler import _


@implementer(ITaskContainer)
class BaseTaskContainerMixin:
    """Base task container persistent class"""

    @property
    def folders(self):
        """Container folders getter """
        yield from filter(ITaskFolder.providedBy, self.values())

    @property
    def tasks(self):
        """Container tasks getter"""
        yield from filter(ITask.providedBy, self.values())


@implementer(IDefaultProtectionPolicy)
class TaskContainer(BaseTaskContainerMixin, ProtectedObjectMixin, Folder):
    """Task container persistent class"""
    

@factory_config(ITaskContainerRoles)
class TaskContainerRoles(ProtectedObjectRoles):
    """Task container roles"""

    scheduler_managers = RolePrincipalsFieldProperty(ITaskContainerRoles['scheduler_managers'])
    tasks_managers = RolePrincipalsFieldProperty(ITaskContainerRoles['tasks_managers'])
    scheduler_guests = RolePrincipalsFieldProperty(ITaskContainerRoles['scheduler_guests'])


@adapter_config(required=ITaskContainer,
                provides=ITaskContainerRoles)
def task_container_roles_adapter(context):
    """Task container roles adapter"""
    return TaskContainerRoles(context)


@adapter_config(name='scheduler_roles',
                required=ITaskContainer,
                provides=IRolesPolicy)
class TaskContainerRolesPolicy(ContextAdapter):
    """Task container roles policy"""

    roles_interface = ITaskContainerRoles
    weight = 10


@factory_config(ITaskFolder)
class TaskFolder(TaskContainer):
    """Task folder"""

    label = _("Folder")
    icon_class = 'far fa-folder'

    name = FieldProperty(ITaskFolder['name'])


@adapter_config(required=ITaskFolder,
                provides=IViewContextPermissionChecker)
class TaskFolderPermissionChecker(ContextAdapter):
    """Task folder permission checker"""

    edit_permission = MANAGE_SCHEDULER_PERMISSION
