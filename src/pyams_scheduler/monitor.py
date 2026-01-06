# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

from pyams_scheduler.interfaces import IScheduler
from pyams_utils.factory import create_object
from pyams_utils.interfaces.monitor import IMonitorExtension, IMonitorExtensionStatus
from pyams_utils.registry import query_utility, utility_config

__docformat__ = 'restructuredtext'


@utility_config(name='pyams_scheduler.monitor',
                provides=IMonitorExtension)
class SchedulerMonitor:
    """Scheduler monitor utility"""
    
    def get_status(self, request):
        scheduler = query_utility(IScheduler)
        if scheduler is None:
            yield create_object(IMonitorExtensionStatus,
                                handler='pyams_scheduler.monitor:scheduler',
                                status='DOWN',
                                message='Missing scheduler utility')
        else:
            yield create_object(IMonitorExtensionStatus,
                                handler='pyams_scheduler.monitor:scheduler',
                                status='UP')
            status_code, message = scheduler.test_process()
            if status_code == 200:
                yield create_object(IMonitorExtensionStatus,
                                    handler='pyams_scheduler.monitor:process',
                                    status='UP',
                                    message=message)
            else:
                yield create_object(IMonitorExtensionStatus,
                                    handler='pyams_scheduler.monitor:process',
                                    status='DOWN',
                                    message=f'Scheduler process not running: {message}')
