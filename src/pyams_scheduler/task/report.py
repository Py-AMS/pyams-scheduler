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
import re
import traceback
from datetime import datetime, timezone

from pyams_scheduler.interfaces.task import ITask
from pyams_scheduler.interfaces.task.report import IReport, ITaskResultReportInfo
from pyams_utils.adapter import ContextAdapter, adapter_config
from pyams_utils.factory import factory_config
from pyams_utils.registry import get_pyramid_registry
from pyams_utils.text import text_to_html
from pyams_utils.timezone import tztime

__docformat__ = 'restructuredtext'


@factory_config(IReport)
class Report:
    """Report class helper"""

    def __init__(self, renderer='markdown'):
        self.report = io.StringIO()
        self.renderer = renderer
        self.padding = 0
        
    def add_padding(self):
        self.padding += 1
        
    def remove_padding(self):
        self.padding -= 1
        
    def tell(self):
        return self.report.tell()
    
    def seek(self, position):
        return self.report.seek(position)
    
    def truncate(self):
        return self.report.truncate()
        
    def write(self, value, prefix='', suffix=''):
        if prefix and self.padding:
            prefix = f"{'>' * self.padding} {prefix}"
        if suffix and self.padding:
            suffix = f"{'>' * self.padding} {suffix}"
        return self.report.write(f"{'>' * self.padding}{prefix}{value}{suffix}")
    
    def writeln(self, value, prefix='', suffix=''):
        return self.write(f"{value}\n", prefix, suffix)

    def write_code(self, value):
        return self.writeln(value, prefix='\n```\n', suffix='```\n\n')
    
    def write_shell(self, value):
        return self.write_code(re.sub('^\n', '',
                                      re.sub('\n*$', '', value)))
    
    def write_exception(self, *exc_info):
        return self.write_code('\n'.join(filter(bool,
                                                map(lambda x: re.sub('^\n', '',
                                                                     re.sub('\n*$', '', x,
                                                                            flags=re.MULTILINE)),
                                                    traceback.format_exception(*exc_info)))))
    
    def getvalue(self):
        return text_to_html(self.report.getvalue(), self.renderer)

    def close(self):
        return self.report.close()
    
    
@adapter_config(required=str,
                provides=ITaskResultReportInfo)
class StringTaskResultReportInfo(ContextAdapter):
    """String task result report info adapter"""
    
    json = False
    value = None
    
    def __init__(self, result):
        self.value = result
        try:
            _value = json.loads(result)
        except json.JSONDecodeError:
            pass
        else:
            self.json = True
            
    @property
    def mimetype(self):
        return 'application/json; charset=utf-8' if self.json else 'text/plain; charset=utf-8'
    
    @property
    def filename(self):
        now = tztime(datetime.now(timezone.utc))
        return f"report-{now:%Y%m%d}-{now:%H%M%S-%f}{'.json' if self.json else '.txt'}"

    @property
    def content(self):
        return self.value


@adapter_config(required=dict,
                provides=ITaskResultReportInfo)
class DictTaskResultReportInfo(ContextAdapter):
    """Dict task result report info adapter"""
    
    def __init__(self, result):
        self.result = result
        
    @property
    def mimetype(self):
        return 'application/json; charset=utf-8'
    
    @property
    def filename(self):
        now = tztime(datetime.now(timezone.utc))
        return f"report-{now:%Y%m%d}-{now:%H%M%S-%f}.json"

    @property
    def content(self):
        return json.dumps(self.result)
        

@adapter_config(required=(ITask, list),
                provides=ITaskResultReportInfo)
@adapter_config(required=(ITask, tuple),
                provides=ITaskResultReportInfo)
def list_task_result_report_info(task, result):
    """List task result report info adapter"""
    if not result:
        return None
    result = result[0]
    if not result:
        return None
    registry = get_pyramid_registry()
    adapter = registry.queryMultiAdapter((task, result), ITaskResultReportInfo)
    if adapter is None:
        adapter = ITaskResultReportInfo(result, None)
    return adapter
