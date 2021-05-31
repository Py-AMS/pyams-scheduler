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

"""PyAMS_scheduler.zmi.task.rest module

This module defines REST API caller task management interface.
"""

from urllib import parse

from pyramid.events import subscriber
from zope.interface import Interface, Invalid, alsoProvides, implementer

from pyams_form.ajax import ajax_form_config
from pyams_form.browser.checkbox import SingleCheckBoxFieldWidget
from pyams_form.field import Fields
from pyams_form.group import GroupManager
from pyams_form.interfaces.form import IDataExtractedEvent, IForm, IGroup, IInnerTabForm
from pyams_form.subform import InnerAddForm, InnerEditForm
from pyams_layer.interfaces import IPyAMSLayer
from pyams_scheduler.interfaces import IScheduler, MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.task.rest import IRESTCallerTask, IRESTCallerTaskInfo
from pyams_scheduler.zmi import SchedulerTasksTable
from pyams_scheduler.zmi.task import BaseTaskAddForm, BaseTaskEditForm
from pyams_skin.interfaces.viewlet import IHelpViewletManager
from pyams_skin.viewlet.help import AlertMessage
from pyams_skin.viewlet.menu import MenuItem
from pyams_utils.adapter import adapter_config
from pyams_utils.interfaces.data import IObjectData
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.form import FormGroupChecker
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.viewlet import IContextAddingsViewletManager


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


class IRESTTaskForm(IForm):
    """REST caller forms common interface"""


@implementer(IRESTTaskForm)
class RESTTaskFormInfo(GroupManager):
    """REST API caller task add form info"""

    title = _("HTTP/REST API settings")
    fields = Fields(IRESTCallerTaskInfo).select('base_url', 'service', 'params', 'verify_ssl',
                                                'connection_timeout', 'ok_status',
                                                'allow_redirects')
    fields['verify_ssl'].widget_factory = SingleCheckBoxFieldWidget
    fields['allow_redirects'].widget_factory = SingleCheckBoxFieldWidget

    def update_widgets(self, prefix=None):
        """Widgets update"""
        super().update_widgets(prefix)  # pylint: disable=no-member
        params = self.widgets.get('params')  # pylint: disable=no-member
        if params is not None:
            params.add_class('height-100')
            params.widget_css_class = "editor height-200px"
            params.object_data = {
                'ams-filename': 'params.json'
            }
            alsoProvides(params, IObjectData)


@subscriber(IDataExtractedEvent, form_selector=RESTTaskFormInfo)
def extract_rest_task_info(event):
    """Extract REST task info"""
    data = event.data
    if 'base_url' in data:
        parsed_url = parse.urlparse(data['base_url'])
        if not (parsed_url.scheme and parsed_url.netloc):
            event.form.widgets.errors += (Invalid(_("Missing base target URI!")), )


@adapter_config(name='rest-auth.group',
                required=(IScheduler, IAdminLayer, IRESTTaskForm),
                provides=IGroup)
@adapter_config(name='rest-auth.group',
                required=(IRESTCallerTask, IAdminLayer, IRESTTaskForm),
                provides=IGroup)
class RESTTaskFormAuthInfo(FormGroupChecker):
    """REST task form auth info"""

    legend = _("Authentication")
    fields = Fields(IRESTCallerTaskInfo).select('authenticate', 'username', 'password')

    weight = 10

    def update_widgets(self, prefix=None):
        super().update_widgets(prefix)
        password = self.widgets.get('password')
        if password is not None:
            password.autocomplete = 'new-password'


@subscriber(IDataExtractedEvent, form_selector=RESTTaskFormAuthInfo)
def extract_rest_auth_info(event):
    """Extract REST task auth info"""
    data = event.data
    authenticate = data.get('authenticate')
    if authenticate and not data.get('username'):
        event.form.widgets.errors += (Invalid(_("Username and password are required to use "
                                                "authentication!")), )


@adapter_config(name='rest-proxy.group',
                required=(IScheduler, IAdminLayer, IRESTTaskForm),
                provides=IGroup)
@adapter_config(name='rest-proxy.group',
                required=(IRESTCallerTask, IAdminLayer, IRESTTaskForm),
                provides=IGroup)
class RESTTaskFormProxyInfo(FormGroupChecker):
    """REST task form proxy info"""

    legend = _("Proxy settings")
    fields = Fields(IRESTCallerTaskInfo).select('use_proxy', 'proxy_server', 'proxy_port',
                                                'proxy_username', 'proxy_password')

    weight = 20

    def update_widgets(self, prefix=None):
        super().update_widgets(prefix)
        password = self.widgets.get('proxy_password')
        if password is not None:
            password.autocomplete = 'new-password'


@subscriber(IDataExtractedEvent, form_selector=RESTTaskFormProxyInfo)
def extract_rest_proxy_info(event):
    """Extract REST task proxy info"""
    data = event.data
    use_proxy = data.get('use_proxy')
    if use_proxy and not data.get('proxy_server'):
        event.form.widgets.errors += (Invalid(_("Proxy access defined without proxy server!")), )


@adapter_config(name='rest-jwt-authority.group',
                required=(IScheduler, IAdminLayer, IRESTTaskForm),
                provides=IGroup)
@adapter_config(name='rest-jwt-authority.group',
                required=(IRESTCallerTask, IAdminLayer, IRESTTaskForm),
                provides=IGroup)
class RESTTaskFormJWTInfo(FormGroupChecker):
    """REST task form JWT info"""

    fields = Fields(IRESTCallerTaskInfo).select('use_jwt_authority', 'jwt_authority_url',
                                                'jwt_token_service', 'jwt_token_attribute',
                                                'jwt_use_proxy')
    fields['jwt_use_proxy'].widget_factory = SingleCheckBoxFieldWidget

    weight = 30


@viewlet_config(name='rest-jwt-authority.help',
                context=Interface, layer=IAdminLayer, view=RESTTaskFormJWTInfo,
                manager=IHelpViewletManager, weight=10)
class RESTTaskFormJWTHelp(AlertMessage):
    """REST task form JWT help"""

    css_class = 'mb-1 p-2'

    _message = _("If this service require a JWT token, you can define the authentication "
                 "authority which will be used to get new access tokens.")


@subscriber(IDataExtractedEvent, form_selector=RESTTaskFormJWTInfo)
def extract_rest_jwt_info(event):
    """Extract REST task JWT info"""
    data = event.data
    use_jwt_authority = data.get('use_jwt_authority')
    if use_jwt_authority and not data.get('jwt_authority_url'):
        event.form.widgets.errors += (Invalid(_("JWT authority location is required to enable "
                                                "JWT authentication!")), )


#
# REST API task add forms
#

@viewlet_config(name='add-rest-task.menu',
                context=IScheduler, layer=IAdminLayer, view=SchedulerTasksTable,
                manager=IContextAddingsViewletManager, weight=20,
                permission=MANAGE_TASKS_PERMISSION)
class RESTTaskAddMenu(MenuItem):
    """REST task add menu"""

    label = _("Add HTTP/REST API caller task...")
    href = 'add-rest-task.html'
    modal_target = True


@ajax_form_config(name='add-rest-task.html', context=IScheduler, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class RESTTaskAddForm(BaseTaskAddForm):
    """REST task add form"""

    content_factory = IRESTCallerTask


@adapter_config(name='rest-task-info.form',
                required=(IScheduler, IAdminLayer, RESTTaskAddForm),
                provides=IInnerTabForm)
class RESTTaskAddFormInfo(RESTTaskFormInfo, InnerAddForm):
    """REST task add form info"""


#
# REST task edit forms
#

@ajax_form_config(name='properties.html', context=IRESTCallerTask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class RESTTaskEditForm(BaseTaskEditForm):
    """REST task edit form"""


@adapter_config(name='rest-task-info.form',
                required=(IRESTCallerTask, IAdminLayer, RESTTaskEditForm),
                provides=IInnerTabForm)
class RESTTaskEditFormInfo(RESTTaskFormInfo, InnerEditForm):
    """REST task edit form info"""
