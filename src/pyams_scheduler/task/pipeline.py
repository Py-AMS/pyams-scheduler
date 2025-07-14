# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
import io
import json
import zipfile
from datetime import datetime, timezone
from time import sleep

from persistent import Persistent
from pyramid.config import Configurator
from pyramid.threadlocal import RequestContext, manager
from transaction.interfaces import ITransactionManager
from zope.container.contained import Contained
from zope.interface import Interface
from zope.schema.fieldproperty import FieldProperty

from pyams_scheduler.folder import BaseTaskContainerMixin
from pyams_scheduler.interfaces import AfterRunJobEvent, BeforeRunJobEvent, ITask, SCHEDULER_NAME
from pyams_scheduler.interfaces.task import TASK_STATUS_ERROR, TASK_STATUS_NONE, TASK_STATUS_OK
from pyams_scheduler.interfaces.task.pipeline import IPipelineInput, IPipelineOutput, IPipelineTask, \
    TASK_PIPELINE_INPUT_KEY
from pyams_scheduler.interfaces.task.report import ITaskResultReportInfo
from pyams_scheduler.task import BaseTaskMixin, LOGGER
from pyams_site.interfaces import PYAMS_APPLICATION_DEFAULT_NAME, PYAMS_APPLICATION_SETTINGS_KEY
from pyams_table.testing import OrderedContainer
from pyams_utils.adapter import ContextAdapter, adapter_config, get_annotation_adapter
from pyams_utils.date import get_duration
from pyams_utils.dict import DotDict
from pyams_utils.factory import factory_config
from pyams_utils.registry import get_local_registry, get_pyramid_registry, set_local_registry
from pyams_utils.request import check_request
from pyams_utils.timezone import tztime
from pyams_utils.transaction import COMMITTED_STATUS
from pyams_utils.zodb import ZODBConnection

__docformat__ = 'restructuredtext'

from pyams_scheduler import _


@factory_config(IPipelineInput)
class PipelineInputInfo(Persistent, Contained):
    """Pipeline input persistent info"""
    
    execution_delay = FieldProperty(IPipelineInput['execution_delay'])
    ignore_input_params = FieldProperty(IPipelineInput['ignore_input_params'])
    stop_on_empty_params = FieldProperty(IPipelineInput['stop_on_empty_params'])
    
    
@adapter_config(required=ITask,
                provides=IPipelineInput)
def task_pipeline_input(context):
    """Task pipeline input adapter"""
    return get_annotation_adapter(context, TASK_PIPELINE_INPUT_KEY, IPipelineInput)
    
    
class BasePipelineOutput(ContextAdapter):
    """Base pipeline output adapter"""

    def get_values(self, result):
        if not result:
            return {}
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = {}
        if isinstance(result, dict):
            return DotDict(result)
        result = [
            DotDict(item)
            for item in result
        ]
        return result[0] if len(result) == 1 else result
    
    
@factory_config(IPipelineTask)
class PipelineTask(OrderedContainer, BaseTaskContainerMixin, BaseTaskMixin):
    """Pipeline task persistent class"""
    
    label = _("Pipeline task")
    icon_class = 'fas fa-link'

    def __init__(self):
        OrderedContainer.__init__(self)
        BaseTaskMixin.__init__(self)

    def _run(self, report, **kwargs):
        """Task execution wrapper"""
        status = TASK_STATUS_NONE
        result = None
        # initialize ZCA hook
        registry = kwargs.pop('registry', None)
        if registry is None:
            registry = get_pyramid_registry()
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
                        tm = ITransactionManager(task)
                        registry.notify(BeforeRunJobEvent(task))
                        start_date = datetime.now(timezone.utc)
                        request = check_request(base_url=scheduler_util.notified_host,
                                                registry=registry, principal_id=self.principal_id)
                        request.root = application
                        translate = request.localizer.translate
                        task._v_zip_output = zip_output = io.BytesIO()
                        with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            with RequestContext(request):
                                if not (kwargs.get('run_immediate') or task.is_runnable()):
                                    LOGGER.debug(f"Skipping inactive task {task.name}")
                                    return status, result
                                params = kwargs
                                report.writeln(f'Pipeline execution log for task: **{task.name}**', prefix='# ')
                                # loop over internal tasks
                                for inner_task in task.values():
                                    report.writeln('---')
                                    report.writeln(f"Starting task: <strong>{inner_task.name}</strong>",
                                                   prefix='## ')
                                    # check task inputs
                                    task_input = IPipelineInput(inner_task, None)
                                    if task_input is not None:
                                        if task_input.execution_delay:
                                            report.writeln(f'Task execution start delay: '
                                                           f'{task_input.execution_delay} seconds')
                                            sleep(task_input.execution_delay)
                                        if (not params) and task_input.stop_on_empty_params:
                                            report.writeln(f'**Empty params: pipeline execution stopped!**', suffix='\n')
                                            break
                                        if task_input.ignore_input_params:
                                            params = {}
                                    # run internal task
                                    if inner_task.is_zodb_task:
                                        (status, result) = inner_task.run_zodb_task(request, registry,
                                                                                    scheduler_util, report,
                                                                                    notify=False, **params)
                                    else:
                                        (status, result) = inner_task.run_external_task(request, registry,
                                                                                        scheduler_util, report,
                                                                                        notify=False, **params)
                                    if status != TASK_STATUS_OK:
                                        report.writeln('**Pipeline execution break!**', suffix='\n')
                                        break
                                    # get next task params from execution result
                                    task_output = IPipelineOutput(inner_task, None)
                                    if task_output is not None:
                                        params = {'params': task_output.get_values(result)}
                                    else:
                                        params = {'params': result or {}}
                                    # add task result to internal ZIP
                                    report_info = registry.queryMultiAdapter((inner_task, result),
                                                                             ITaskResultReportInfo)
                                    if report_info is None:
                                        report_info = ITaskResultReportInfo(result, None)
                                    if report_info is not None:
                                        filename = report_info.filename
                                        if filename:
                                            zip_file.writestr(filename, report_info.content)
                                else:
                                    report.writeln('---')
                                    report.writeln('Pipeline execution terminated without error!',
                                                   prefix='### ', suffix='\n')
                        end_date = datetime.now(timezone.utc)
                        duration = (end_date - start_date).total_seconds()
                        report.writeln(f'Total task duration: '
                                       f'**{get_duration(start_date, end_date, request=request)}**', suffix='\n')
                        for attempt in tm.attempts():
                            with attempt as t:
                                history_item = task.store_report(result, report, status, start_date, duration)
                                if status == TASK_STATUS_ERROR:
                                    message_text = translate(_("Task '{}' was executed "
                                                               "with error")).format(task.name)
                                else:
                                    message_text = translate(_("Task '{}' was executed "
                                                               "without error")).format(task.name)
                                message = task.get_chat_message(request, scheduler_util, status,
                                                                message_text, history_item)
                                message.send()
                                registry.notify(AfterRunJobEvent(task, status, result))
                                task.send_report(report, status, history_item, registry)
                            if t.status == COMMITTED_STATUS:
                                break
                finally:
                    set_local_registry(old_registry)
            except:  # pylint: disable=bare-except
                self._log_exception(None, f"Can't execute scheduled job {self.name}")
            tm = ITransactionManager(self, None)  # pylint: disable=invalid-name
            if tm is not None:
                tm.abort()
        return status, result

    def run(self, report, **kwargs):
        return self._run(report, **kwargs)


@adapter_config(required=(IPipelineTask, Interface),
                provides=ITaskResultReportInfo)
class PipelineTaskReportInfo:
    """Pipeline task report info adapter"""
    
    def __init__(self, task, result=None):
        self.task = task
        
    mimetype = 'application/zip'
    
    @property
    def filename(self):
        now = tztime(datetime.now(timezone.utc))
        return f"report-{now:%Y%m%d}-{now:%H%M%S-%f}.zip"

    @property
    def content(self):
        output = getattr(self.task, '_v_zip_output', None)
        if output is not None:
            output.seek(0)
            return output.read()
        return ''
