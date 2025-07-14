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

"""PyAMS_scheduler.task.rest module

This module defines REST caller task.
"""

import codecs
import json
import mimetypes
import pprint
import sys
from datetime import datetime, timezone
from urllib import parse

import chardet
import requests
from requests import RequestException
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.interfaces.task import ITask, TASK_STATUS_ERROR, TASK_STATUS_FAIL, TASK_STATUS_OK
from pyams_scheduler.interfaces.task.pipeline import IPipelineOutput
from pyams_scheduler.interfaces.task.report import ITaskResultReportInfo
from pyams_scheduler.interfaces.task.rest import GET_METHOD, IRESTCallerTask, JSON_CONTENT_TYPE
from pyams_scheduler.task import Task
from pyams_scheduler.task.pipeline import BasePipelineOutput
from pyams_security.interfaces.names import UNCHANGED_PASSWORD
from pyams_utils.adapter import ContextAdapter, ContextRequestAdapter, adapter_config
from pyams_utils.dict import format_dict
from pyams_utils.factory import factory_config
from pyams_utils.html import html_to_text
from pyams_utils.registry import get_pyramid_registry
from pyams_utils.text import render_text
from pyams_utils.timezone import tztime

__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


@factory_config(IRESTCallerTask)
class RESTCallerTask(Task):
    """REST API caller task"""

    label = _("HTTP service")
    icon_class = 'fab fa-battle-net'

    base_url = FieldProperty(IRESTCallerTask['base_url'])
    service = FieldProperty(IRESTCallerTask['service'])
    headers = FieldProperty(IRESTCallerTask['headers'])
    params = FieldProperty(IRESTCallerTask['params'])
    content_type = FieldProperty(IRESTCallerTask['content_type'])
    verify_ssl = FieldProperty(IRESTCallerTask['verify_ssl'])
    ssl_certs = FieldProperty(IRESTCallerTask['ssl_certs'])
    connection_timeout = FieldProperty(IRESTCallerTask['connection_timeout'])
    allow_redirects = FieldProperty(IRESTCallerTask['allow_redirects'])
    ok_status = FieldProperty(IRESTCallerTask['ok_status'])
    use_proxy = FieldProperty(IRESTCallerTask['use_proxy'])
    proxy_server = FieldProperty(IRESTCallerTask['proxy_server'])
    proxy_port = FieldProperty(IRESTCallerTask['proxy_port'])
    proxy_username = FieldProperty(IRESTCallerTask['proxy_username'])
    _proxy_password = FieldProperty(IRESTCallerTask['proxy_password'])
    authenticate = FieldProperty(IRESTCallerTask['authenticate'])
    username = FieldProperty(IRESTCallerTask['username'])
    _password = FieldProperty(IRESTCallerTask['password'])
    use_jwt_authority = FieldProperty(IRESTCallerTask['use_jwt_authority'])
    jwt_authority_url = FieldProperty(IRESTCallerTask['jwt_authority_url'])
    jwt_token_service = FieldProperty(IRESTCallerTask['jwt_token_service'])
    jwt_login_field = FieldProperty(IRESTCallerTask['jwt_login_field'])
    jwt_password_field = FieldProperty(IRESTCallerTask['jwt_password_field'])
    jwt_token_attribute = FieldProperty(IRESTCallerTask['jwt_token_attribute'])
    jwt_use_proxy = FieldProperty(IRESTCallerTask['jwt_use_proxy'])
    use_api_key = FieldProperty(IRESTCallerTask['use_api_key'])
    api_key_header = FieldProperty(IRESTCallerTask['api_key_header'])
    api_key_value = FieldProperty(IRESTCallerTask['api_key_value'])

    @property
    def password(self):
        """Password getter"""
        return self._password

    @password.setter
    def password(self, value):
        """Password setter"""
        if value == UNCHANGED_PASSWORD:
            return
        self._password = value

    @property
    def proxy_password(self):
        """Proxy password getter"""
        return self._proxy_password

    @proxy_password.setter
    def proxy_password(self, value):
        """Proxy password setter"""
        if value == UNCHANGED_PASSWORD:
            return
        self._proxy_password = value

    @property
    def ok_status_list(self):
        """OK status list getter"""
        return map(int, self.ok_status.split(','))

    def get_request_headers(self, **params):
        """Request HTTP headers getter"""
        result = {}
        for header in (self.headers or ()):
            if not header:
                continue
            try:
                name, value = header.split('=', 1)
            except ValueError:
                continue
            else:
                result[name] = self.get_param_value(value, **params)
        return result

    def get_request_params(self, method, params):
        """Request params getter"""
        result = {}
        if method == GET_METHOD:
            result['params'] = params
        else:
            if self.content_type == JSON_CONTENT_TYPE:
                result['json'] = params
            else:
                result['data'] = params
        return result

    def run(self, report, **kwargs):
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        # get remote service URL
        method, service = self.service
        # check proxy configuration
        proxies = {}
        if self.use_proxy:
            parsed = parse.urlparse(self.base_url)
            if self.proxy_username:
                proxy_auth = f'{self.proxy_username}:{self.proxy_password}@'
            else:
                proxy_auth = ''
            proxies[parsed.scheme] = f'http://{proxy_auth}{self.proxy_server}:{self.proxy_port}'
        # check custom headers
        headers = self.get_request_headers(**kwargs)
        # check authorizations
        auth = None
        if self.use_jwt_authority:  # JWT authentication
            jwt_method, jwt_service = self.jwt_token_service
            jwt_service = f'{self.jwt_authority_url}{jwt_service}'
            jwt_params = {
                self.jwt_login_field: self.username,
                self.jwt_password_field: self.password
            }
            try:
                jwt_request = requests.request(jwt_method, jwt_service,
                                               params=jwt_params if jwt_method == 'GET' else None,
                                               json=jwt_params if jwt_method != 'GET' else None,
                                               proxies=proxies if self.jwt_use_proxy else None,
                                               timeout=self.connection_timeout,
                                               allow_redirects=False)
            except RequestException:
                report.writeln('**An HTTP error occurred while getting JWT token**', suffix='\n')
                report.write_exception(*sys.exc_info())
                return TASK_STATUS_FAIL, None
            else:
                status_code = jwt_request.status_code
                report.writeln(f'JWT token status code: {status_code}')
                if status_code != requests.codes.ok:  # pylint: disable=no-member
                    report.writeln(f'JWT headers: {format_dict(jwt_request.headers)}')
                    report.writeln(f'JWT params: {format_dict(jwt_params)}')
                    report.writeln(f'JWT report: {jwt_request.text}', suffix='\n')
                    return TASK_STATUS_ERROR, None
                headers['Authorization'] = f'Bearer ' \
                                           f'{jwt_request.json().get(self.jwt_token_attribute)}'
        elif self.authenticate and self.username:  # Basic authentication
            auth = self.username, self.password
        # launch HTTP request
        results = []
        kwargs_params = kwargs.pop('params', {})
        if isinstance(kwargs_params, dict):
            kwargs_params = [kwargs_params]
        status_code = 0
        for input_params in kwargs_params:
            rest_service = (f'{render_text(self.base_url, **input_params)}'
                            f'{render_text(service, **input_params)}')
            report.writeln(f'HTTP service output', prefix='### ')
            report.writeln(f'HTTP service: `{method} {rest_service}`\n\n')
            if self.use_api_key:  # API key authentication
                headers[self.api_key_header] = self.api_key_value
            if headers:
                report.write(f'Request headers: {format_dict(headers)}\n')
            # check params
            params = self.params or {}
            if params:
                params = json.loads(render_text(params, **input_params))
                params.update(input_params)
            else:
                params = input_params
            params.update(kwargs)
            if params:
                report.write(f'Request params:')
                report.write_code(format_dict(params))
            # build HTTP request
            try:
                rest_request = requests.request(method, rest_service,
                                                auth=auth,
                                                headers=headers,
                                                verify=self.ssl_certs or self.verify_ssl,
                                                proxies=proxies,
                                                timeout=self.connection_timeout,
                                                allow_redirects=self.allow_redirects,
                                                **self.get_request_params(method, params))
            except RequestException:
                report.writeln('**An HTTP error occurred**', suffix='\n')
                report.write_exception(*sys.exc_info())
                return TASK_STATUS_FAIL, None
            else:
                # check request status
                status_code = rest_request.status_code
                report.writeln(f'Response status code: `{status_code}`', suffix='\n')
                report.write(f'Headers:')
                report.write_code(format_dict(rest_request.headers))
                # check request content
                content_type = self.get_report_mimetype(rest_request)
                if content_type.startswith('application/json'):
                    response = rest_request.json()
                    message = pprint.pformat(response)
                elif content_type.startswith('text/html'):
                    message = html_to_text(rest_request.text)
                elif content_type.startswith('text/'):
                    message = rest_request.text
                else:
                    content = rest_request.content
                    if 'charset=' in content_type.lower():
                        charset = content_type.split('=', 1)[1]
                    else:
                        charset = chardet.detect(content).get('encoding') or 'utf-8'
                    message = codecs.decode(content, charset)
                report.writeln(message, suffix='\n')
                results.append(rest_request)
        return (
            TASK_STATUS_OK if status_code in self.ok_status_list else status_code,
            results
        )


@adapter_config(required=IRESTCallerTask,
                provides=IPipelineOutput)
class RESTCallerTaskPipelineOutput(ContextAdapter):
    """REST caller task pipeline output"""
    
    def get_values(self, results):
        registry = get_pyramid_registry()
        values = []
        for result in results:
            content_type = result.headers.get('Content-Type', 'text/plain')
            adapter = registry.queryAdapter(self.context, IPipelineOutput,
                                            name=content_type)
            if adapter is None:
                content_type, _ignored = map(str.strip, content_type.split(';', 1))
                adapter = registry.queryAdapter(self.context, IPipelineOutput,
                                                name=content_type)
            if adapter is not None:
                values.append(adapter.get_values(result))
        return values


@adapter_config(name='text/plain',
                required=IRESTCallerTask,
                provides=IPipelineOutput)
class RESTCallerTaskTextPipelineOutput(BasePipelineOutput):
    """REST caller task plain text pipeline output"""

            
@adapter_config(name='application/json',
                required=IRESTCallerTask,
                provides=IPipelineOutput)
class RESTCallerTaskJSONPipelineOutput(BasePipelineOutput):
    """REST caller task JSON pipeline output"""

    def get_values(self, result):
        return super().get_values(result.json())
    

@adapter_config(required=requests.Response,
                provides=ITaskResultReportInfo)
@adapter_config(required=(ITask, requests.Response),
                provides=ITaskResultReportInfo)
class ResponseReportInfo:
    """HTTP response report info"""

    def __init__(self, *args):
        self.result = args[-1]

    @property
    def mimetype(self):
        return self.result.headers.get('Content-Type', 'text/plain')
    
    @property
    def filename(self):
        content_type = self.mimetype
        if ';' in content_type:
            content_type, _encoding = content_type.split(';', 1)
        extension = mimetypes.guess_extension(content_type)
        now = tztime(datetime.now(timezone.utc))
        return f"report-{now:%Y%m%d}-{now:%H%M%S-%f}{extension or '.txt'}"

    @property
    def content(self):
        result = self.result
        content_type = self.mimetype
        if content_type.startswith('application/json'):
            response = json.dumps(result.json())
        elif content_type.startswith('text/'):
            response = result.text
        else:
            content = result.content
            if 'charset=' in content_type.lower():
                charset = content_type.split('=', 1)[1]
            else:
                charset = chardet.detect(content).get('encoding') or 'utf-8'
            response = codecs.decode(content, charset)
        return response
