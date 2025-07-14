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

import logging
import traceback
from datetime import datetime, timezone

from persistent import Persistent
from pyramid.config import Configurator
from pyramid.events import subscriber
from pyramid.threadlocal import RequestContext, manager
from pyramid.traversal import lineage
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

try:
    from pyams_chat.message import ChatMessage
except ImportError:
    ChatMessage = None

from pyams_file.property import FileProperty
from pyams_scheduler.interfaces import AfterRunJobEvent, BeforeRunJobEvent, IScheduler, \
    MANAGE_TASKS_PERMISSION, SCHEDULER_AUTH_KEY, SCHEDULER_GUEST_ROLE, \
    SCHEDULER_HANDLER_KEY, SCHEDULER_MANAGER_ROLE, SCHEDULER_NAME, TASKS_MANAGER_ROLE
from pyams_scheduler.interfaces.folder import ITaskContainer, ITaskFolder
from pyams_scheduler.interfaces.task import FailedTaskRunException, ITaskHistoryContainer, \
    ITask, ITaskHistory, ITaskInfo, ITaskNotificationContainer, ITaskSchedulingMode, TASK_STATUS_CLASS, \
    TASK_STATUS_EMPTY, TASK_STATUS_ERROR, TASK_STATUS_FAIL, TASK_STATUS_NONE, TASK_STATUS_OK
from pyams_scheduler.interfaces.task.report import IReport, ITaskResultReportInfo
from pyams_scheduler.task.report import Report
from pyams_security.interfaces import IProtectedObject, IViewContextPermissionChecker
from pyams_security.interfaces.names import ADMIN_USER_ID, INTERNAL_USER_ID, SYSTEM_ADMIN_ROLE
from pyams_site.interfaces import PYAMS_APPLICATION_DEFAULT_NAME, PYAMS_APPLICATION_SETTINGS_KEY
from pyams_utils.adapter import ContextAdapter, adapter_config, query_adapter
from pyams_utils.date import get_duration
from pyams_utils.factory import create_object, factory_config
from pyams_utils.interfaces.transaction import ITransactionClient
from pyams_utils.registry import get_local_registry, get_pyramid_registry, get_utility, query_utility, \
    set_local_registry
from pyams_utils.request import check_request
from pyams_utils.timezone import tztime
from pyams_utils.transaction import COMMITTED_STATUS, TransactionClient, transactional
from pyams_utils.traversing import get_parent, get_parents_until
from pyams_utils.zodb import ZODBConnection
from pyams_zmi.interfaces import IObjectLabel
from pyams_zmi.utils import get_object_label
from pyams_zmq.socket import zmq_response, zmq_socket


__docformat__ = 'restructuredtext'

from pyams_scheduler import _


LOGGER = logging.getLogger('PyAMS (scheduler)')


@factory_config(ITaskHistory)
class TaskHistoryItem(Persistent, Contained):
    """Task history item"""

    status = FieldProperty(ITaskHistory['status'])
    date = FieldProperty(ITaskHistory['date'])
    duration = FieldProperty(ITaskHistory['duration'])
    report = FieldProperty(ITaskHistory['report'])
    report_file = FileProperty(ITaskHistory['report_file'])

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@implementer(ITaskHistoryContainer)
class TaskHistoryContainer(Folder):
    """Task history container"""

    def check_history(self, duration, length):
        """Check history container contents"""
        if duration:
            now = tztime(datetime.now(timezone.utc))
            for key in list(self.keys()):
                if (now - tztime(self[key].date)).days > duration:
                    del self[key]
        if length and (len(self) > length):
            keys = sorted(self.keys(), reverse=True)[:length]
            for key in list(self.keys()):
                if key not in keys:
                    del self[key]


class TaskHandler(TransactionClient):
    """Generic task handler"""

    @transactional
    def execute(self, task, action, job_id, registry=None):
        """Execute scheduler action"""
        scheduler = query_utility(IScheduler)
        if scheduler is not None:
            registry = registry if registry is not None else get_pyramid_registry()
            handler = registry.settings.get(SCHEDULER_HANDLER_KEY, False)
            if handler:
                zmq_settings = {
                    'zodb_name': scheduler.zodb_name,
                    'task_name': task.internal_id,
                    'job_id': job_id
                }
                LOGGER.debug(f"Starting '{action}' on task {task.name} with {zmq_settings!r}")
                socket = zmq_socket(handler, auth=registry.settings.get(SCHEDULER_AUTH_KEY))
                socket.send_json([action, zmq_settings])
                zmq_response(socket)


@implementer(ITask, ITransactionClient)
class BaseTaskMixin:
    """Task definition persistent class"""

    label = None
    icon_class = None

    name = FieldProperty(ITask['name'])
    _schedule_mode = FieldProperty(ITask['schedule_mode'])
    keep_empty_reports = FieldProperty(ITask['keep_empty_reports'])
    _history_duration = FieldProperty(ITask['history_duration'])
    _history_length = FieldProperty(ITask['history_length'])

    attach_reports = FieldProperty(ITask['attach_reports'])

    settings_view_name = FieldProperty(ITask['settings_view_name'])
    principal_id = None

    _internal_id = None

    is_zodb_task = False

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

    def get_path(self):
        """Task full path"""
        request = check_request()
        return ' / '.join((
            get_object_label(parent, request)
            for parent in reversed(list(lineage(self)))
            if ITaskFolder.providedBy(parent) or ITask.providedBy(parent)
        ))

    def get_path_elements(self):
        """Get path elements from task to scheduler"""
        def get_elements():
            yield self.__name__
            for item in lineage(self):
                if ITaskContainer.providedBy(item):
                    yield item.__name__

        yield from reversed(list(get_elements()))

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
        handler = TaskHandler()
        handler.execute(self, 'reset_task', self.internal_id)

    def launch(self):
        """Task immediate launcher"""
        handler = TaskHandler()
        handler.execute(self, 'run_task', self.internal_id)

    def __call__(self, *args, **kwargs):
        report = create_object(IReport)
        if report is None:
            report = Report()
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

    def get_param_value(self, input, **params):
        """Apply incoming params to input string"""
        if not input:
            return input
        return input.format(**params)

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
                application = root.get(application_name)
                old_registry = get_local_registry()
                try:
                    sm = application.getSiteManager()  # pylint: disable=invalid-name
                    set_local_registry(sm)
                    scheduler_util = sm.get(SCHEDULER_NAME)
                    task = scheduler_util.get_task(self.internal_id)
                    if task is not None:
                        request = check_request(base_url=scheduler_util.notified_host,
                                                registry=registry, principal_id=self.principal_id)
                        request.root = application
                        with RequestContext(request):
                            if not (kwargs.get('run_immediate') or task.is_runnable()):
                                LOGGER.debug(f"Skipping inactive task {task.name}")
                                return status, result
                            if task.is_zodb_task:
                                (status, result) = task.run_zodb_task(request, registry, scheduler_util,
                                                                      report, **kwargs)
                            else:
                                (status, result) = task.run_external_task(request, registry, scheduler_util,
                                                                          report, **kwargs)
                finally:
                    set_local_registry(old_registry)
            except:  # pylint: disable=bare-except
                self._log_exception(None, f"Can't execute scheduled job {self.name}")
            tm = ITransactionManager(self, None)  # pylint: disable=invalid-name
            if tm is not None:
                tm.abort()
        return status, result
    
    def run_zodb_task(self, request, registry, scheduler, report, notify=True, **kwargs):
        """Run a ZODB-based task
        
        ZODB-based tasks are tasks that update the ZODB; they use transaction attempts
        to handle conflict errors
        """
        translate = request.localizer.translate
        status = TASK_STATUS_NONE
        result = None
        position = report.tell()
        tm = ITransactionManager(self)  # pylint: disable=invalid-name
        for index, attempt in enumerate(tm.attempts()):
            with attempt as t:  # pylint: disable=invalid-name
                message = None
                report.seek(position)
                report.truncate()
                start_date = datetime.now(timezone.utc)
                duration = 0.
                try:
                    registry.notify(BeforeRunJobEvent(self))
                    (status, result) = self.run(report, **kwargs)
                    if status == TASK_STATUS_FAIL:
                        raise FailedTaskRunException
                    end_date = datetime.now(timezone.utc)
                    duration = (end_date - start_date).total_seconds()
                    report.write(f'Task duration: '
                                   f'{get_duration(start_date, end_date, request=request)}')
                    if index > 0:
                        report.write(f' (on attempt #{index+1})')
                    report.writeln('\n')
                    if notify:
                        history_item = self.store_report(result, report, status, start_date, duration)
                        if (ChatMessage is not None) and scheduler.notified_host:
                            if status == TASK_STATUS_ERROR:
                                message_text = translate(_("Task '{}' was executed "
                                                           "with error")).format(self.name)
                            else:
                                message_text = translate(_("Task '{}' was executed "
                                                           "without error")).format(self.name)
                            message = self.get_chat_message(request, scheduler, status,
                                                            message_text, history_item)
                except FailedTaskRunException:  # pylint: disable=bare-except
                    # pylint: disable=protected-access
                    self._log_exception(report,
                                        f"An error occurred during execution of "
                                        f"task '{self.name}'")
                    if notify:
                        history_item = self.store_report(result, report, status, start_date, duration)
                        if (ChatMessage is not None) and scheduler.notified_host:
                            message_text = translate(_("An error occurred during execution of task "
                                                       "'{}'")).format(self.name)
                            message = self.get_chat_message(request, scheduler, TASK_STATUS_FAIL,
                                                            message_text, history_item)
                if notify and (message is not None):
                    message.send()
                registry.notify(AfterRunJobEvent(self, status, result))
                if notify:
                    self.send_report(report, status, history_item, registry)
            if t.status == COMMITTED_STATUS:
                break
        return status, result
    
    def run_external_task(self, request, registry, scheduler, report, notify=True, **kwargs):
        """Run an external task
        
        External tasks are tasks that run outside the ZODB; transaction attempts are
        only used to handle conflict errors when storing the execution report.
        """
        translate = request.localizer.translate
        status = TASK_STATUS_NONE
        result = None
        message = None
        start_date = datetime.now(timezone.utc)
        duration = 0.
        tm = ITransactionManager(self)  # pylint: disable=invalid-name
        try:
            registry.notify(BeforeRunJobEvent(self))
            (status, result) = self.run(report, **kwargs)
            if status == TASK_STATUS_FAIL:
                raise FailedTaskRunException
            end_date = datetime.now(timezone.utc)
            duration = (end_date - start_date).total_seconds()
            report.writeln(f'Task duration: '
                           f'{get_duration(start_date, end_date, request=request)}', suffix='\n')
            position = report.tell()
            for attempt in tm.attempts():
                with attempt as t:  # pylint: disable=invalid-name
                    report.seek(position)
                    report.truncate()
                    if notify:
                        history_item = self.store_report(result, report, status, start_date, duration)
                        if status == TASK_STATUS_ERROR:
                            message_text = translate(_("Task '{}' was executed "
                                                       "with error")).format(self.name)
                        else:
                            message_text = translate(_("Task '{}' was executed "
                                                       "without error")).format(self.name)
                        message = self.get_chat_message(request, scheduler, status,
                                                        message_text, history_item)
                if t.status == COMMITTED_STATUS:
                    break
        except FailedTaskRunException:  # pylint: disable=bare-except
            # pylint: disable=protected-access
            self._log_exception(report,
                                f"An error occurred during execution of "
                                f"task '{self.name}'")
            for attempt in tm.attempts():
                with attempt as t:  # pylint: disable=invalid-name
                    if notify:
                        history_item = self.store_report(result, report, status, start_date, duration)
                        message_text = translate(_("An error occurred during execution of task "
                                                   "'{}'")).format(self.name),
                        message = self.get_chat_message(request, scheduler, TASK_STATUS_FAIL,
                                                        message_text, history_item)
                if t.status == COMMITTED_STATUS:
                    break
        if notify and (message is not None):
            message.send()
        registry.notify(AfterRunJobEvent(self, status, result))
        if notify:
            self.send_report(report, status, history_item, registry)
        tm.commit()  # required to send a transactional chat message!
        return status, result
        
    def run(self, report, **kwargs):  # pylint: disable=no-self-use
        """Task run implementation

        May result a tuple containing a status code and a result (which can be empty).
        """
        raise NotImplementedError("The 'run' method must be implemented by Task subclasses!")

    def get_chat_message(self, request, scheduler, status, message, history_item):
        """Chat message getter"""
        if (ChatMessage is None) or not scheduler.notified_host:
            return None
        translate = request.localizer.translate
        return ChatMessage(request=request,
                           host=scheduler.notified_host,
                           action='notify',
                           category='scheduler.run',
                           status=TASK_STATUS_CLASS.get(status, 'info'),
                           source=INTERNAL_USER_ID,
                           title=translate(_("Task execution")),
                           message=message,
                           url='/'.join(('', '++etc++site') +
                                        tuple(self.get_path_elements()) +
                                        ('++history++', history_item.__name__, 'history.html')),
                           modal=True,
                           task=self)

    @staticmethod
    def _log_report(report, message, add_timestamp=True, level=logging.INFO):
        """Execution log report"""
        if isinstance(message, bytes):
            message = message.decode()
        if add_timestamp:
            message = f"{tztime(datetime.now(timezone.utc)).strftime('%c')} - {message}"
        if report is not None:
            report.write(f'{message}\n')
        LOGGER.log(level, message)

    @staticmethod
    def _log_exception(report, message=None):
        """Exception log report"""
        if isinstance(message, bytes):
            message = message.decode()
        message = f"{tztime(datetime.now(timezone.utc)).strftime('%c')} - {message or 'An error occurred'}\n\n"
        if report is not None:
            report.write(message)
            report.write(traceback.format_exc() + '\n')
        LOGGER.exception(message)

    @staticmethod
    def get_report_mimetype(result=None):
        if not result:
            return None
        if isinstance(result, (list, tuple)):
            result = result[-1]
        report_info = ITaskResultReportInfo(result, None)
        return report_info.mimetype if report_info is not None else None

    @staticmethod
    def get_report_filename(result=None):
        if not result:
            return None
        if isinstance(result, (list, tuple)):
            result = result[-1]
        report_info = ITaskResultReportInfo(result, None)
        return report_info.filename if report_info is not None else None
    
    @staticmethod
    def get_report_content(result):
        if not result:
            return None
        if isinstance(result, (list, tuple)):
            result = result[-1]
        report_info = ITaskResultReportInfo(result, None)
        return report_info.content if report_info is not None else None
    
    def store_report(self, result, report, status, start_date, duration):
        """Execution report store"""
        if (status in (TASK_STATUS_NONE, TASK_STATUS_EMPTY)) and \
                not self.keep_empty_reports:
            return
        item = create_object(ITaskHistory,
                             status=str(status),
                             date=start_date,
                             duration=duration,
                             report=report.report.getvalue())
        self.history[item.date.isoformat()] = item
        if result and self.attach_reports:
            registry = get_pyramid_registry()
            report_info = registry.queryMultiAdapter((self, result), ITaskResultReportInfo)
            if report_info is None:
                report_info = ITaskResultReportInfo(result, None)
            if report_info is not None:
                filename = report_info.filename
                mimetype = report_info.mimetype
                if filename and mimetype:
                    item.report_file = (f'{filename};{mimetype}', report_info.content)
        self.check_history()
        return item

    def send_report(self, report, status, history_item, registry):
        """Execution report messaging"""
        notifications = ITaskNotificationContainer(self)
        for target in notifications.get_enabled_items():
            handler = target.get_handler()
            if handler is None:
                continue
            if ((status in (TASK_STATUS_NONE, TASK_STATUS_EMPTY)) and not target.send_empty_reports) or \
                    ((status == TASK_STATUS_OK) and target.report_errors_only):
                continue
            handler.send_report(self, report, status, history_item, target, registry)


class Task(BaseTaskMixin, Persistent, Contained):
    """Task persistent class"""
    

@adapter_config(required=ITask,
                provides=IObjectLabel)
def task_label(context):
    """Task label getter"""
    return context.name


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
            LOGGER.debug(f"Removing task {task.name} with {zmq_settings!r}")
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
        task._internal_id = None  # pylint: disable=protected-access
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


if ChatMessage is not None:

    from pyams_chat.interfaces import IChatMessage, IChatMessageHandler

    @adapter_config(name='scheduler.run',
                    required=IChatMessage,
                    provides=IChatMessageHandler)
    class SchedulerTaskRunMessageHandler(ContextAdapter):
        """Scheduler task run message handler"""

        def get_target(self):
            """Chat message targets getter"""
            principals = {ADMIN_USER_ID}
            root = self.context.request.root
            protection = IProtectedObject(root, None)
            if protection is not None:
                principals |= protection.get_principals(SYSTEM_ADMIN_ROLE)
            task = self.context.user_data.get('task')
            if task is not None:
                for parent in get_parents_until(task, IScheduler):
                    protection = IProtectedObject(parent, None)
                    if protection is not None:
                        principals |= protection.get_principals(SCHEDULER_MANAGER_ROLE)
                        principals |= protection.get_principals(TASKS_MANAGER_ROLE)
                        principals |= protection.get_principals(SCHEDULER_GUEST_ROLE)
            return {
                'principals': tuple(principals)
            }
