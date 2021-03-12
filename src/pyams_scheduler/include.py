#
# Copyright (c) 2015-2019 Thierry Florac <tflorac AT ulthar.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

"""PyAMS scheduler.include module

This module is used for Pyramid integration.
"""

import atexit
import logging
import os.path
import sys

from pyramid.events import subscriber
from pyramid.interfaces import IApplicationCreated
from pyramid.settings import asbool
from zope.interface.interfaces import ComponentLookupError

from pyams_scheduler.interfaces import MANAGE_SCHEDULER_PERMISSION, MANAGE_TASKS_PERMISSION, \
    SCHEDULER_AUTH_KEY, SCHEDULER_CLIENTS_KEY, SCHEDULER_HANDLER_KEY, SCHEDULER_MANAGER_ROLE, \
    SCHEDULER_NAME, SCHEDULER_STARTER_KEY, TASKS_MANAGER_ROLE
from pyams_scheduler.process import SchedulerMessageHandler, SchedulerProcess
from pyams_security.interfaces import ADMIN_USER_ID, SYSTEM_ADMIN_ROLE
from pyams_security.interfaces.base import MANAGE_ROLES_PERMISSION, ROLE_ID
from pyams_site.interfaces import PYAMS_APPLICATION_DEFAULT_NAME, PYAMS_APPLICATION_SETTINGS_KEY
from pyams_utils.protocol.tcp import is_port_in_use
from pyams_utils.registry import get_pyramid_registry, set_local_registry
from pyams_utils.zodb import get_connection_from_settings
from pyams_zmq.process import process_exit_func


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


LOGGER = logging.getLogger('PyAMS (scheduler)')


def include_package(config):
    """Pyramid package include"""

    # add translations
    config.add_translation_dirs('pyams_scheduler:locales')

    # add scheduler permissions and roles
    config.register_permission({
        'id': MANAGE_SCHEDULER_PERMISSION,
        'title': _("Manage scheduler properties")
    })
    config.register_permission({
        'id': MANAGE_TASKS_PERMISSION,
        'title': _("Manage scheduler tasks")
    })

    # upgrade system manager roles
    config.upgrade_role(SYSTEM_ADMIN_ROLE,
                        permissions={
                            MANAGE_SCHEDULER_PERMISSION,
                            MANAGE_TASKS_PERMISSION
                        })

    # register new roles
    config.register_role({
        'id': SCHEDULER_MANAGER_ROLE,
        'title': _("Scheduler manager (role)"),
        'permissions': {
            MANAGE_ROLES_PERMISSION,
            MANAGE_SCHEDULER_PERMISSION,
            MANAGE_TASKS_PERMISSION
        },
        'managers': {
            ADMIN_USER_ID,
            ROLE_ID.format(SYSTEM_ADMIN_ROLE)
        }
    })
    config.register_role({
        'id': TASKS_MANAGER_ROLE,
        'title': _("Tasks manager (role)"),
        'permissions': {
            MANAGE_TASKS_PERMISSION
        },
        'managers': {
            ADMIN_USER_ID,
            ROLE_ID.format(SYSTEM_ADMIN_ROLE),
            ROLE_ID.format(SCHEDULER_MANAGER_ROLE)
        }
    })

    try:
        import pyams_zmi  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError:
        config.scan(ignore='pyams_scheduler.zmi')
    else:
        config.scan()


@subscriber(IApplicationCreated)
def handle_new_application(event):  # pylint: disable=unused-argument,too-many-locals,too-many-branches
    """Start scheduler process when application is created"""

    # Check for PyAMS command line script
    cmdline = os.path.split(sys.argv[0])[-1]
    if cmdline.startswith('pyams_'):
        return

    registry = get_pyramid_registry()
    settings = registry.settings
    start_handler = asbool(settings.get(SCHEDULER_STARTER_KEY, False))
    if not start_handler:
        return

    # check if port is available
    handler_address = settings.get(SCHEDULER_HANDLER_KEY, '127.0.0.1:5555')
    hostname, port = handler_address.split(':')
    if is_port_in_use(int(port), hostname):
        LOGGER.warning("Scheduler port already used, aborting...")
        return

    # get database connection
    connection = get_connection_from_settings(settings)
    root = connection.root()
    # get application
    application_name = settings.get(PYAMS_APPLICATION_SETTINGS_KEY,
                                    PYAMS_APPLICATION_DEFAULT_NAME)
    application = root.get(application_name)
    if application is None:
        return

    process = None
    sm = application.getSiteManager()  # pylint: disable=invalid-name
    set_local_registry(sm)
    try:
        scheduler_util = sm.get(SCHEDULER_NAME)
        if scheduler_util is None:
            return
        try:
            zodb_name = scheduler_util.zodb_name
        except ComponentLookupError:
            pass
        else:
            # create scheduler process
            process = SchedulerProcess(handler_address,
                                       SchedulerMessageHandler,
                                       settings.get(SCHEDULER_AUTH_KEY),
                                       settings.get(SCHEDULER_CLIENTS_KEY),
                                       registry)
            # load tasks
            for task in scheduler_util.values():
                if not task.is_runnable():
                    continue
                trigger = task.get_trigger()
                LOGGER.debug("Adding scheduler job for task '{0.name}'".format(task))
                process.scheduler.add_job(task, trigger,
                                          id=str(task.internal_id),
                                          name=task.name,
                                          kwargs={
                                              'zodb_name': zodb_name,
                                              'registry': registry
                                          })
            # start process
            LOGGER.info("Starting tasks scheduler {0!r}...".format(process))
            process.start()
            if process.is_alive():
                atexit.register(process_exit_func, process=process)
                LOGGER.info("Started tasks scheduler with PID {0}.".format(process.pid))
    finally:
        if process and not process.is_alive():
            process.terminate()
            process.join()
        set_local_registry(None)
