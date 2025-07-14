# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

from zope.interface import Interface
from zope.schema import Bool, Int

from pyams_scheduler.interfaces import ITask
from pyams_scheduler.interfaces.folder import ITaskFolder

__docformat__ = 'restructuredtext'

from pyams_scheduler import _


TASK_PIPELINE_INPUT_KEY = 'pyams_scheduler.task.pipeline.input'


class IPipelineInput(Interface):
    """Pipeline input interface"""
    
    execution_delay = Int(title=_("Execution delay"),
                          description=_("Execution pipeline will wait for the given number of seconds "
                                        "before starting this task"),
                          default=0,
                          min=0)
    
    ignore_input_params = Bool(title=_("Ignore input from previous task"),
                               description=_("If 'yes', output from previous task in the pipeline will be ignored "
                                             "instead of being used as this task input"),
                               required=True,
                               default=False)
    
    stop_on_empty_params = Bool(title=_("Stop pipeline on empty params"),
                                description=_("If 'yes', the pipeline execution will be stopped if params "
                                              "provided by previous task are empty"),
                                required=True,
                                default=False)


class IPipelineOutput(Interface):
    """Pipeline output interface"""
    
    def get_values(self, result):
        """Extract output values mapping from the task execution result
        
        If set, these values will be used as next pipeline task execution parameters.
        """


class IPipelineTaskInfo(Interface):
    """Pipeline task info interface"""


class IPipelineTask(ITaskFolder, ITask, IPipelineTaskInfo):
    """Pipeline task interface"""
