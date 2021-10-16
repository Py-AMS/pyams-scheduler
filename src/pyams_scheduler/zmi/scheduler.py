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
from pyams_scheduler.interfaces import IScheduler, MANAGE_SCHEDULER_PERMISSION, \
    TASKS_SCHEDULER_LABEL
from pyams_site.interfaces import ISiteRoot
from pyams_skin.interfaces.viewlet import IBreadcrumbItem
from pyams_utils.adapter import adapter_config
from pyams_utils.registry import get_utility, query_utility
from pyams_utils.url import absolute_url
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.form import AdminEditForm
from pyams_zmi.interfaces import IAdminLayer, IObjectLabel
from pyams_zmi.interfaces.viewlet import IControlPanelMenu, ISiteManagementMenu
from pyams_zmi.zmi.viewlet.breadcrumb import AdminLayerBreadcrumbItem
from pyams_zmi.zmi.viewlet.menu import NavigationMenuItem


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@adapter_config(required=(IScheduler, IPyAMSLayer, Interface),
                provides=IObjectLabel)
def scheduler_label(context, request, view):  # pylint: disable=unused-argument
    """Scheduler label"""
    return request.localizer.translate(TASKS_SCHEDULER_LABEL)


@adapter_config(required=(IScheduler, IAdminLayer, Interface),
                provides=IBreadcrumbItem)
class SchedulerBreadcrumbItem(AdminLayerBreadcrumbItem):
    """Scheduler breadcrumb item"""

    label = TASKS_SCHEDULER_LABEL


@viewlet_config(name='scheduler.menu',
                context=ISiteRoot, layer=IAdminLayer,
                manager=IControlPanelMenu, weight=25,
                permission=MANAGE_SCHEDULER_PERMISSION)
class SchedulerMenu(NavigationMenuItem):
    """Scheduler root menu"""

    label = TASKS_SCHEDULER_LABEL
    icon_class = 'fa fa-clock'

    def __new__(cls, context, request, view, manager):  # pylint: disable=unused-argument
        scheduler = query_utility(IScheduler)
        if (scheduler is None) or not scheduler.show_home_menu:
            return None
        return NavigationMenuItem.__new__(cls)

    def get_href(self):
        """Menu URL getter"""
        scheduler = get_utility(IScheduler)
        return absolute_url(scheduler, self.request, 'admin')


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

    title = TASKS_SCHEDULER_LABEL
    legend = _("Scheduler configuration")

    fields = Fields(IScheduler).select('zodb_name', 'report_mailer', 'report_source',
                                       'notified_host', 'show_home_menu')
