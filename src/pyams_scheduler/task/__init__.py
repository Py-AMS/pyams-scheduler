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

"""PyAMS_scheduler.task module

This module defines base tasks classes.
"""

__docformat__ = 'restructuredtext'

import logging
import traceback
from datetime import datetime
from io import StringIO

import transaction
from persistent import Persistent
from pyramid.config import Configurator
from pyramid.events import subscriber
from pyramid.threadlocal import RequestContext, manager
from transaction.interfaces import ITransactionManager
from zope.component import queryUtility
from zope.component.interfaces import ISite
from zope.container.contained import Contained
from zope.container.folder import Folder
from zope.copy.interfaces import ICopyHook, ResumeCopy
from zope.interface import alsoProvides, implementer, noLongerProvides
from zope.intid import IIntIds
from zope.lifecycleevent import IObjectAddedEvent, IObjectModifiedEvent, IObjectRemovedEvent
from zope.location import locate
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.interfaces import AfterRunJobEvent, BeforeRunJobEvent, IScheduler, ITask, \
    ITaskHistory, MANAGE_TASKS_PERMISSION, SCHEDULER_AUTH_KEY, SCHEDULER_HANDLER_KEY, \
    SCHEDULER_NAME
from pyams_scheduler.interfaces.task import ITaskHistoryContainer, ITaskInfo, \
    ITaskNotificationContainer, ITaskSchedulingMode, TASK_STATUS_EMPTY, \
    TASK_STATUS_ERROR, TASK_STATUS_NONE, TASK_STATUS_OK
from pyams_security.interfaces import IViewContextPermissionChecker
from pyams_site.interfaces import PYAMS_APPLICATION_DEFAULT_NAME, PYAMS_APPLICATION_SETTINGS_KEY
from pyams_utils.adapter import ContextAdapter, adapter_config
from pyams_utils.date import get_duration
from pyams_utils.registry import get_pyramid_registry, get_utility, query_utility, \
    set_local_registry
from pyams_utils.request import check_request
from pyams_utils.timezone import tztime
from pyams_utils.traversing import get_parent
from pyams_utils.zodb import ZODBConnection
from pyams_zmq.socket import zmq_response, zmq_socket


LOGGER = logging.getLogger('PyAMS (scheduler)')


@implementer(ITaskHistory)
class TaskHistoryItem(Persistent, Contained):
    """Task history item"""

    status = FieldProperty(ITaskHistory['status'])
    date = FieldProperty(ITaskHistory['date'])
    duration = FieldProperty(ITaskHistory['duration'])
    report = FieldProperty(ITaskHistory['report'])

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@implementer(ITaskHistoryContainer)
class TaskHistoryContainer(Folder):
    """Task history container"""

    def check_history(self, duration, length):
        """Check history container contents"""
        if duration:
            now = tztime(datetime.utcnow())
            for key in list(self.keys()):
                if (now - tztime(self[key].date)).days > duration:
                    del self[key]
        if length and (len(self) > length):
            keys = sorted(self.keys(), reverse=True)[:length]
            for key in list(self.keys()):
                if key not in keys:
                    del self[key]


@implementer(ITask)
class Task(Persistent, Contained):
    """Task definition persistent class"""

    label = None
    icon_class = None

    name = FieldProperty(ITask['name'])
    _schedule_mode = FieldProperty(ITask['schedule_mode'])
    keep_empty_reports = FieldProperty(ITask['keep_empty_reports'])
    _history_duration = FieldProperty(ITask['history_duration'])
    _history_length = FieldProperty(ITask['history_length'])

    settings_view_name = FieldProperty(ITask['settings_view_name'])
    principal_id = None

    _internal_id = None

    def __init__(self):
        history = self.history = TaskHistoryContainer()
        locate(history, self, '++history++')

    @property
    def schedule_mode(self):
        """Scheduler mode getter"""
        return self._schedule_mode

    @schedule_mode.setter
    def schedule_mode(self, value):
        """Scheduler mode setter"""
        if self._schedule_mode is not None:
            mode = query_utility(ITaskSchedulingMode, name=self._schedule_mode)
            if (mode is not None) and mode.marker_interface.providedBy(self):
                noLongerProvides(self, mode.marker_interface)
        self._schedule_mode = value
        if value:
            mode = get_utility(ITaskSchedulingMode, name=value)
            alsoProvides(self, mode.marker_interface)
            mode.schema(self).active = False
            if self.__parent__ is not None:
                self.reset()

    @property
    def history_duration(self):
        """History duration getter"""
        return self._history_duration

    @history_duration.setter
    def history_duration(self, value):
        """History duration setter"""
        self._history_duration = value

    @property
    def history_length(self):
        """History length getter"""
        return self._history_length

    @history_length.setter
    def history_length(self, value):
        """History length setter"""
        self._history_length = value

    def check_history(self):
        """Check history container for old contents"""
        self.history.check_history(self.history_duration, self.history_length)

    @property
    def internal_id(self):
        """Task internal ID getter"""
        if self._internal_id is None:
            site = get_parent(self, ISite)
            sm = site.getSiteManager()  # pylint: disable=invalid-name,too-many-function-args,assignment-from-no-return
            intids = sm.queryUtility(IIntIds)
            if intids is not None:
                self._internal_id = intids.register(self)
        return self._internal_id

    def get_trigger(self):
        """Task trigger getter"""
        mode = queryUtility(ITaskSchedulingMode, self.schedule_mode)
        if mode is None:
            return None
        return mode.get_trigger(self)

    def get_scheduling_info(self):
        """Task scheduling info getter"""
        mode = queryUtility(ITaskSchedulingMode, self.schedule_mode)
        if mode is None:
            return None
        return mode.schema(self, None)

    def reset(self):
        """Task reset launcher"""
        scheduler_util = query_utility(IScheduler)
        if scheduler_util is not None:
            # get task internal ID before transaction ends!!!
            transaction.get().addAfterCommitHook(self._reset_action, kws={
                'scheduler': scheduler_util,
                'registry': get_pyramid_registry(),
                'job_id': self.internal_id
            })

    def _reset_action(self, status, *args, **kwargs):  # pylint: disable=unused-argument
        """Task reset action, called in an after-commit hook"""
        if not status:
            return
        scheduler_util = kwargs.get('scheduler')
        if scheduler_util is None:
            return
        registry = kwargs.get('registry') or get_pyramid_registry()
        handler = registry.settings.get(SCHEDULER_HANDLER_KEY, False)
        if handler:
            zmq_settings = {
                'zodb_name': scheduler_util.zodb_name,
                'task_name': self.__name__,
                'job_id': kwargs.get('job_id')
            }
            LOGGER.debug("Resetting task {0.name} with {1!r}".format(self, zmq_settings))
            socket = zmq_socket(handler, auth=registry.settings.get(SCHEDULER_AUTH_KEY))
            socket.send_json(['reset_task', zmq_settings])
            zmq_response(socket)

    def launch(self):
        """Task immediate launcher"""
        scheduler_util = query_utility(IScheduler)
        if scheduler_util is not None:
            # get task internal ID before transaction ends!!!
            transaction.get().addAfterCommitHook(self._launch_action, kws={
                'scheduler': scheduler_util,
                'registry': get_pyramid_registry(),
                'job_id': self.internal_id
            })

    def _launch_action(self, status, *args, **kwargs):  # pylint: disable=unused-argument
        """Task immediate launch action"""
        if not status:
            return
        scheduler_util = kwargs.get('scheduler')
        if scheduler_util is None:
            return
        registry = kwargs.get('registry') or get_pyramid_registry()
        handler = registry.settings.get(SCHEDULER_HANDLER_KEY, False)
        if handler:
            zmq_settings = {
                'zodb_name': scheduler_util.zodb_name,
                'task_name': self.__name__,
                'job_id': kwargs.get('job_id')
            }
            LOGGER.debug("Running task {0.name} with {1!r}".format(self, zmq_settings))
            socket = zmq_socket(handler, auth=registry.settings.get(SCHEDULER_AUTH_KEY))
            socket.send_json(['run_task', zmq_settings])
            zmq_response(socket)

    def __call__(self, *args, **kwargs):
        report = StringIO()
        return self._run(report, **kwargs)

    def is_runnable(self):
        """Task runnable state getter"""
        mode = queryUtility(ITaskSchedulingMode, self.schedule_mode)
        if mode is None:
            return False
        info = mode.schema(self, None)
        if info is None:
            return False
        return info.active

    def _run(self, report, **kwargs):  # pylint: disable=too-many-locals
        """Task execution wrapper"""
        status = TASK_STATUS_NONE
        result = None
        # initialize ZCA hook
        registry = kwargs.pop('registry')
        manager.push({'registry': registry, 'request': None})
        config = Configurator(registry=registry)
        config.hook_zca()
        # open ZODB connection
        zodb_connection = ZODBConnection(name=kwargs.pop('zodb_name', ''))
        with zodb_connection as root:
            try:
                application_name = registry.settings.get(PYAMS_APPLICATION_SETTINGS_KEY,
                                                         PYAMS_APPLICATION_DEFAULT_NAME)
                sm = root.get(application_name).getSiteManager()  # pylint: disable=invalid-name
                scheduler_util = sm.get(SCHEDULER_NAME)
                task = scheduler_util.get(self.__name__)
                if task is not None:
                    set_local_registry(sm)
                    request = check_request(registry=registry, principal_id=self.principal_id)
                    with RequestContext(request):
                        if not (kwargs.get('run_immediate') or task.is_runnable()):
                            LOGGER.debug("Skipping inactive task {0}".format(task.name))
                            return status, result
                        tm = ITransactionManager(task)  # pylint: disable=invalid-name
                        for attempt in tm.attempts():
                            with attempt as t:  # pylint: disable=invalid-name
                                start_date = datetime.utcnow()
                                duration = 0.
                                try:
                                    registry.notify(BeforeRunJobEvent(task))
                                    (status, result) = task.run(report, **kwargs)
                                    end_date = datetime.utcnow()
                                    duration = (end_date - start_date).total_seconds()
                                    report.write('\n\nTask duration: {0}'.format(
                                        get_duration(start_date, request=request)))
                                except:  # pylint: disable=bare-except
                                    status = TASK_STATUS_ERROR
                                    # pylint: disable=protected-access
                                    task._log_exception(report,
                                                        "An error occurred during execution of "
                                                        "task '{0}'".format(task.name))
                                registry.notify(AfterRunJobEvent(task, status, result))
                                task.store_report(report, status, start_date, duration)
                                task.send_report(report, status, registry)
                            if t.status == 'Committed':
                                break
            except:  # pylint: disable=bare-except
                self._log_exception(None, "Can't execute scheduled job {0}".format(self.name))
            tm = ITransactionManager(self, None)  # pylint: disable=invalid-name
            if tm is not None:
                tm.abort()
        return status, result

    def run(self, report, **kwargs):  # pylint: disable=no-self-use
        """Task run implementation

        May result a tuple containing a status code and a result (which can be empty).
        """
        raise NotImplementedError("The 'run' method must be implemented by Task subclasses!")

    @staticmethod
    def _log_report(report, message, add_timestamp=True, level=logging.INFO):
        """Execution log report"""
        if isinstance(message, bytes):
            message = message.decode()
        if add_timestamp:
            message = '{0} - {1}'.format(tztime(datetime.utcnow()).strftime('%c'), message)
        if report is not None:
            report.write(message + '\n')
        LOGGER.log(level, message)

    @staticmethod
    def _log_exception(report, message=None):
        """Exception log report"""
        if isinstance(message, bytes):
            message = message.decode()
        message = '{0} - {1}'.format(tztime(datetime.utcnow()).strftime('%c'),
                                     message or 'An error occurred') + '\n\n'
        if report is not None:
            report.write(message)
            report.write(traceback.format_exc() + '\n')
        LOGGER.exception(message)

    def store_report(self, report, status, start_date, duration):
        """Execution report store"""
        if (status in (TASK_STATUS_NONE, TASK_STATUS_EMPTY)) and \
                not self.keep_empty_reports:
            return
        item = TaskHistoryItem(status=str(status),
                               date=start_date,
                               duration=duration,
                               report=report.getvalue())
        self.history[item.date.isoformat()] = item
        self.check_history()

    def send_report(self, report, status, registry):
        """Execution report messaging"""
        notifications = ITaskNotificationContainer(self)
        for target in notifications.get_enabled_items():
            handler = target.get_handler()
            if handler is None:
                continue
            if ((status in (TASK_STATUS_NONE, TASK_STATUS_EMPTY)) and
                not target.send_empty_reports) or \
                    ((status == TASK_STATUS_OK) and target.report_errors_only):
                return

            handler.send_report(self, report, status, target, registry)


@subscriber(IObjectAddedEvent, context_selector=ITask)
def handle_new_task(event):
    """Handle new task"""
    event.object.reset()


@subscriber(IObjectModifiedEvent, context_selector=ITask)
def handle_modified_task(event):
    """Handle modified task"""
    for changes in event.descriptions:
        if (changes.interface == ITaskInfo) and \
                (('history_duration' in changes.attributes) or
                 ('history_length' in changes.attributes)):
            event.object.check_history()
            break


@subscriber(IObjectRemovedEvent, context_selector=ITask)
def handle_removed_task(event):
    """Handle removed task"""
    request = check_request()
    if request.registry is not None:
        handler = request.registry.settings.get(SCHEDULER_HANDLER_KEY, False)
        if handler:
            task = event.object
            scheduler_util = query_utility(IScheduler)
            zmq_settings = {
                'zodb_name': scheduler_util.zodb_name,
                'task_name': task.__name__,
                'job_id': task.internal_id
            }
            LOGGER.debug("Removing task {0.name} with {1!r}".format(task, zmq_settings))
            socket = zmq_socket(handler, auth=request.registry.settings.get(SCHEDULER_AUTH_KEY))
            socket.send_json(['remove_task', zmq_settings])
            zmq_response(socket)


@adapter_config(required=ITask,
                provides=ICopyHook)
class TaskCopyHook(ContextAdapter):
    """Task copy hook"""

    def __call__(self, toplevel, register):
        register(self._copy_history)
        raise ResumeCopy

    def _copy_history(self, translate):
        task = translate(self.context)
        task._internal_id = None
        # create empty history
        history = task.history = TaskHistoryContainer()
        locate(history, task, '++history++')
        # disable task
        scheduling_mode = task.get_scheduling_info()
        scheduling_mode.active = False


@adapter_config(required=ITask,
                provides=IViewContextPermissionChecker)
class TaskPermissionChecker(ContextAdapter):
    """Task permission checker"""

    edit_permission = MANAGE_TASKS_PERMISSION
