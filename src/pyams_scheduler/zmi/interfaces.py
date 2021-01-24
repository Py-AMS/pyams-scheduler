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

"""PyAMS_*** module

"""

__docformat__ = 'restructuredtext'

from pyams_form.interfaces import DISPLAY_MODE, INPUT_MODE
from pyams_form.interfaces.form import IForm
from pyams_form.interfaces.widget import IWidget
from pyams_form.template import widget_template_config
from pyams_layer.interfaces import IPyAMSLayer


@widget_template_config(mode=INPUT_MODE,
                        template='templates/directory-host-input.pt', layer=IPyAMSLayer)
@widget_template_config(mode=DISPLAY_MODE,
                        template='templates/directory-host-display.pt', layer=IPyAMSLayer)
class IDirectoryHandlerHostWidget(IWidget):
    """Directory handler host widget interface"""


class ITaskForm(IForm):
    """Base task form interface"""
