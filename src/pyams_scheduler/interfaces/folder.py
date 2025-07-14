# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

from zope.container.constraints import contains
from zope.container.interfaces import IContainer
from zope.interface import Interface
from zope.schema import List, Object, TextLine

from pyams_scheduler.interfaces import ITask

__docformat__ = 'restructuredtext'

from pyams_scheduler import _


class ITaskContainer(IContainer):
    """Generic task container interface"""

    contains('pyams_scheduler.interfaces import ITask',
             'pyams_scheduler.interfaces.ITaskContainer')

    folders = List(title=_("Folder sub-folders"),
                   description=_("List of sub-folders assigned to this container"),
                   value_type=Object(schema=Interface),
                   readonly=True)

    tasks = List(title=_("Folder tasks"),
                 description=_("List of tasks assigned to this container"),
                 value_type=Object(schema=ITask),
                 readonly=True)


class ITaskFolder(ITaskContainer):
    """Task folder interface"""

    name = TextLine(title=_("Folder name"),
                    description=_("Descriptive name given to this folder"),
                    required=True)
