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

"""PyAMS_scheduler.interfaces.task.rest module

This module defines interface of REST API caller task.
"""

from zope.interface import Interface
from zope.schema import Bool, Int, Password, Text, TextLine, URI

from pyams_scheduler.interfaces import ITask
from pyams_utils.schema import HTTPMethodField


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


class IRESTCallerTaskInfo(Interface):
    """REST API caller task info"""

    base_url = URI(title=_("Base target URI"),
                   description=_("Base URI, including protocol and hostname of remote service"),
                   required=True)

    service = HTTPMethodField(title=_("REST service"),
                              description=_("Method and relative URL of REST service"),
                              required=True,
                              default=('GET', '/'))

    params = Text(title=_("Service parameters"),
                  description=_("Enter service parameters, in JSON object format"),
                  required=False)

    verify_ssl = Bool(title=_("Verify SSL?"),
                      description=_("If 'no', SSL certificates will not be verified"),
                      required=False,
                      default=True)

    connection_timeout = Int(title=_("Connection timeout"),
                             description=_("Connection timeout, in seconds; keep empty to use "
                                           "system's default, which is also none by default"),
                             required=False,
                             default=30)

    allow_redirects = Bool(title=_("Allow redirects?"),
                           description=_("If disabled, redirections will now be handled"),
                           required=False,
                           default=True)

    ok_status = TextLine(title=_("OK status"),
                         description=_("Comma-separated list of HTTP status which may be "
                                       "considered as success"),
                         required=True,
                         default='200')

    authenticate = Bool(title=_("Required authentication?"),
                        description=_(""),
                        required=False,
                        default=False)

    username = TextLine(title=_("User name"),
                        description=_("Service login"),
                        required=False)

    password = Password(title=_("Password"),
                        description=_("Service password"),
                        required=False)

    use_proxy = Bool(title=_("Use proxy server?"),
                     description=_("Check if an HTTP proxy is required"),
                     required=False,
                     default=False)

    proxy_server = TextLine(title=_("Proxy server"),
                            description=_("Proxy server name"),
                            required=False)

    proxy_port = Int(title=_("Proxy port"),
                     description=_("Proxy server port"),
                     required=False,
                     default=8080)

    proxy_username = TextLine(title=_("Proxy user name"),
                              required=False)

    proxy_password = Password(title=_("Proxy password"),
                              required=False)

    use_jwt_authority = Bool(title=_("Use JWT authority?"),
                             description=_("If 'yes', get JWT token from authentication "
                                           "authority"),
                             required=False,
                             default=False)

    jwt_authority_url = URI(title=_("JWT authority location"),
                            description=_("Base URL (protocol and hostname) or JWT "
                                          "authentication authority"),
                            required=False)

    jwt_token_service = HTTPMethodField(title=_("Token getter service"),
                                        description=_("Method and relative URL of REST API used "
                                                      "to get access tokens"),
                                        required=False,
                                        default=('POST', '/api/auth/jwt/token'))

    jwt_token_attribute = TextLine(title=_("JWT token attribute"),
                                   description=_("Name of the attribute containing the access "
                                                 "token in JSON response"),
                                   required=False,
                                   default='accessToken')

    jwt_use_proxy = Bool(title=_("Use proxy settings for JWT API?"),
                         description=_("If 'yes', proxy settings defined above will also be used "
                                       "to get access to JWT authority"),
                         required=False,
                         default=False)


class IRESTCallerTask(ITask, IRESTCallerTaskInfo):
    """REST API caller interface"""
