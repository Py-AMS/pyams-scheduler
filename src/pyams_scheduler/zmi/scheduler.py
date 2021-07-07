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

"""PyAMS_scheduler.zmi.scheduler module

This module defines main scheduler tasks view.
"""

from zope.interface import Interface

from pyams_form.ajax import ajax_form_config
from pyams_form.field import Fields
from pyams_layer.interfaces import IPyAMSLayer
from pyams_scheduler.interfaces import IScheduler, MANAGE_SCHEDULER_PERMISSION
from pyams_skin.interfaces.viewlet import IBreadcrumbItem
from pyams_utils.adapter import adapter_config
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.form import AdminEditForm
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.viewlet import ISiteManagementMenu
from pyams_zmi.zmi.viewlet.breadcrumb import AdminLayerBreadcrumbItem
from pyams_zmi.zmi.viewlet.menu import NavigationMenuItem


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@adapter_config(required=(IScheduler, IAdminLayer, Interface),
                provides=IBreadcrumbItem)
class SchedulerBreadcrumbItem(AdminLayerBreadcrumbItem):
    """Scheduler breadcrumb item"""

    label = _("Tasks scheduler")


@viewlet_config(name='configuration.menu',
                context=IScheduler, layer=IAdminLayer,
                manager=ISiteManagementMenu, weight=20,
                permission=MANAGE_SCHEDULER_PERMISSION)
class SchedulerConfigurationMenu(NavigationMenuItem):
    """Scheduler configuration menu"""

    label = _("Configuration")
    icon_class = 'fas fa-sliders-h'
    href = '#configuration.html'


@ajax_form_config(name='configuration.html', context=IScheduler, layer=IPyAMSLayer,
                  permission=MANAGE_SCHEDULER_PERMISSION)
class SchedulerConfigurationEditForm(AdminEditForm):
    """Scheduler configuration edit form"""

    title = _("Tasks scheduler")
    legend = _("Scheduler configuration")

    fields = Fields(IScheduler).select('zodb_name', 'report_mailer', 'report_source')
