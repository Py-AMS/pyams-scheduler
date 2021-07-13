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

"""PyAMS_scheduler.task.notification module

This module defines mail notification for scheduler tasks.
"""

from persistent import Persistent
from pyramid_mailer import IMailer
from pyramid_mailer.message import Message
from zope.component import queryUtility
from zope.container.contained import Contained
from zope.container.folder import Folder
from zope.interface import implementer
from zope.interface.interfaces import ComponentLookupError
from zope.schema.fieldproperty import FieldProperty
from zope.traversing.interfaces import ITraversable

from pyams_scheduler.interfaces import IScheduler, ITask, MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.task import IMailNotification, ITaskNotification, \
    ITaskNotificationContainer, ITaskNotificationMode, SCHEDULER_TASK_NOTIFICATIONS_KEY, \
    TASK_STATUS_ERROR, TASK_STATUS_WARNING
from pyams_security.interfaces import IViewContextPermissionChecker
from pyams_utils.adapter import ContextAdapter, adapter_config, get_annotation_adapter
from pyams_utils.factory import factory_config
from pyams_utils.registry import utility_config
from pyams_utils.traversing import get_parent
from pyams_zmi.interfaces import IObjectLabel


__docformat__ = 'restructuredtext'


#
# Task notifications container
#

@factory_config(ITaskNotificationContainer)
class TaskNotificationContainer(Folder):
    """Task notification container"""

    def get_enabled_items(self):
        """Get iterator over enabled notifications"""
        yield from (notification for notification in self.values() if notification.enabled)


@adapter_config(required=ITask,
                provides=ITaskNotificationContainer)
def task_notifications_container_factory(context):
    """Task notifications container factory"""
    return get_annotation_adapter(context, SCHEDULER_TASK_NOTIFICATIONS_KEY,
                                  ITaskNotificationContainer,
                                  name='++notify++')


@adapter_config(name='notify',
                required=ITask,
                provides=ITraversable)
class TaskNotificationsTraverser(ContextAdapter):
    """Task notifications traverser"""

    def traverse(self, name, furtherpath=None):  # pylint: disable=unused-argument
        """Traverser to task notifications"""
        container = ITaskNotificationContainer(self.context)
        if name:
            return container.get(name)
        return container


#
# Base task notifications classes
#

@implementer(ITaskNotification)
class TaskNotification(Persistent, Contained):
    """Base task notification info"""

    enabled = FieldProperty(ITaskNotification['enabled'])
    report_errors_only = FieldProperty(ITaskNotification['report_errors_only'])
    send_empty_reports = FieldProperty(ITaskNotification['send_empty_reports'])

    def get_handler(self):
        """Get notification handler utility"""
        return queryUtility(ITaskNotificationMode, name=self.mode)


@adapter_config(required=ITaskNotification,
                provides=IViewContextPermissionChecker)
class TaskNotificationPermissionChecker(ContextAdapter):
    """Task notification permission checker"""

    edit_permission = MANAGE_TASKS_PERMISSION


#
# Mail notifications classes
#

MAIL_NOTIFICATION_MODE = 'mail'


@factory_config(IMailNotification)
class MailNotification(TaskNotification):
    """Mail notification info"""

    mode = MAIL_NOTIFICATION_MODE

    target_email = FieldProperty(IMailNotification['target_email'])


@adapter_config(required=IMailNotification,
                provides=IObjectLabel)
def mail_notification_label(context):
    """Mail notification name adapter"""
    return ', '.join(context.target_email or ())


@utility_config(name=MAIL_NOTIFICATION_MODE,
                provides=ITaskNotificationMode)
class MailNotificationMode:
    """Scheduler task mail notification mode"""

    @staticmethod
    def send_report(task, report, status, target, registry=None):
        # pylint: disable=unused-argument
        """Send mail report to given target"""
        if not IMailNotification.providedBy(target):
            return
        scheduler = get_parent(task, IScheduler)
        try:
            mailer_name = scheduler.report_mailer
        except (TypeError, AttributeError, ComponentLookupError):
            return
        mailer = queryUtility(IMailer, mailer_name)
        if mailer is not None:
            report_source = scheduler.report_source
            if status == TASK_STATUS_ERROR:
                subject = "[SCHEDULER !ERROR!] {}".format(task.name)
            elif status == TASK_STATUS_WARNING:
                subject = "[SCHEDULER WARNING] {}".format(task.name)
            else:
                subject = "[scheduler] {}".format(task.name)
            for email in target.target_email or ():
                message = Message(subject=subject,
                                  sender=report_source,
                                  recipients=(email,),
                                  body=report.getvalue())
                mailer.send(message)
