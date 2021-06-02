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

"""PyAMS_scheduler.zmi.trigger module

This module defines views used for tasks triggers management.
"""

from io import StringIO

from zope.interface import Interface

from pyams_form.ajax import ajax_form_config
from pyams_form.button import Buttons, handler
from pyams_form.field import Fields
from pyams_form.interfaces.form import IAJAXFormRenderer, IGroup
from pyams_layer.interfaces import IPyAMSLayer
from pyams_scheduler.interfaces import IScheduler, ITask, \
    MANAGE_TASKS_PERMISSION
from pyams_scheduler.interfaces.task import ICronTask, ICronTaskScheduling, IDateTask, \
    IDateTaskScheduling, ILoopTask, ILoopTaskScheduling
from pyams_scheduler.zmi import SchedulerTasksTable
from pyams_skin.interfaces.viewlet import IHelpViewletManager
from pyams_skin.schema.button import SubmitButton
from pyams_skin.viewlet.help import AlertMessage
from pyams_table.interfaces import IColumn
from pyams_utils.adapter import ContextRequestViewAdapter, adapter_config
from pyams_utils.traversing import get_parent
from pyams_viewlet.viewlet import EmptyViewlet, viewlet_config
from pyams_zmi.form import AdminModalEditForm, FormGroupChecker
from pyams_zmi.helper.event import get_json_table_row_refresh_callback
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.form import IModalEditFormButtons
from pyams_zmi.table import ActionColumn


__docformat__ = 'restructuredtext'

from pyams_scheduler import _  # pylint: disable=ungrouped-imports


#
# Task immediate run views
#

@adapter_config(name='run',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class SchedulerTaskRunColumn(ActionColumn):
    """Scheduler task run column"""

    href = 'run.html'
    icon_class = 'far fa-play-circle'
    hint = _("Run task")

    permission = MANAGE_TASKS_PERMISSION

    weight = 40


class ITaskRunButtons(IModalEditFormButtons):
    """Task run buttons"""

    debug = SubmitButton(name='debug',
                         title=_("Run in debug mode"))

    run = SubmitButton(name='run',
                       title=_("Run task"))


@ajax_form_config(name='run.html', context=ITask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class TaskRunEditForm(AdminModalEditForm):
    """Task run edit form"""

    @property
    def title(self):
        """Title getter"""
        return self.context.name

    legend = _("Task execution")
    modal_class = 'modal-xl'

    fields = Fields(Interface)
    buttons = Buttons(ITaskRunButtons).select('debug', 'run', 'close')

    def update_actions(self):
        super().update_actions()
        debug = self.actions.get('debug')
        if debug is not None:
            debug.add_class('btn-info mr-auto')

    @handler(ITaskRunButtons['debug'])
    def handle_debug(self, action):
        """Debug button handler"""
        report = StringIO()
        self.context.run(report)
        self.finished_state.update({
            'action': action,
            'changes': report.getvalue()
        })

    @handler(ITaskRunButtons['run'])
    def handle_apply(self, action):
        """Task run button handler"""
        self.context.launch()
        self.finished_state.update({
            'action': action,
            'changes': self.context
        })


@adapter_config(name='debug',
                required=(ITask, IAdminLayer, TaskRunEditForm),
                provides=IAJAXFormRenderer)
class TaskRunFormDebugActionRenderer(ContextRequestViewAdapter):
    """Task run form 'debug' action renderer"""

    def render(self, changes):
        """AJAX form renderer"""
        if not changes:
            return None
        return {
            'status': 'success',
            'message': self.request.localizer.translate(_("Task has been executed!")),
            'content': {
                'target': '#{}-debug-target'.format(self.view.id),
                'text': self.view.finished_state.get('changes', '-- NO OUTPUT --')
            },
            'closeForm': False
        }


@adapter_config(name='run',
                required=(ITask, IAdminLayer, TaskRunEditForm),
                provides=IAJAXFormRenderer)
class TaskRunFormRunActionRenderer(ContextRequestViewAdapter):
    """Task run form 'run' action renderer"""

    def render(self, changes):
        """AJAX form renderer"""
        if not changes:
            return None
        return {
            'status': 'success',
            'message': self.request.localizer.translate(_("The task has been planned for "
                                                          "immediate execution...<br />"
                                                          "Check task history to get execution "
                                                          "report."))
        }


@viewlet_config(name='task-run.help',
                context=ITask, layer=IAdminLayer, view=TaskRunEditForm,
                manager=IHelpViewletManager, weight=10)
class TaskRunFormHelp(AlertMessage):
    """Task run form help"""

    _message = _("You can run the task in normal mode or in debug mode.\n"
                 "In debug mode, the task is started in current application thread, and you will "
                 "get the output directly in this form.\n"
                 "In normal mode, the task is scheduled as usual, but for immediate execution.\n"
                 "Please note that in both modes, the scheduling mode is not taken into account, "
                 "including when the task is disabled!")


@viewlet_config(name='task-debug.target',
                context=ITask, layer=IAdminLayer, view=TaskRunEditForm,
                manager=IHelpViewletManager, weight=20)
class TaskRunFormDebugTarget(EmptyViewlet):
    """Task run form debug target"""

    def render(self):
        """Viewlet renderer"""
        return '<textarea id="{}-debug-target" ' \
               ' class="alert alert-secondary border-secondary text-monospace ' \
               '        w-100 height-300px p-2 hidden"></textarea>'.format(self.view.id)


#
# Task schedule views
#

@adapter_config(name='schedule',
                required=(IScheduler, IAdminLayer, SchedulerTasksTable),
                provides=IColumn)
class SchedulerTaskScheduleColumn(ActionColumn):
    """Scheduler task schedule column"""

    href = 'schedule.html'
    icon_class = 'fas fa-clock'
    hint = _("Schedule task")

    permission = MANAGE_TASKS_PERMISSION

    weight = 50


@ajax_form_config(name='schedule.html', context=ITask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class TaskScheduleEditForm(AdminModalEditForm):
    """Task schedule edit form"""

    @property
    def title(self):
        """Title getter"""
        return self.context.name

    legend = _("Task schedule properties")
    fields = Fields(Interface)

    def apply_changes(self, data):
        changes = super().apply_changes(data)
        if changes:
            self.context.reset()
        return changes


@adapter_config(required=(ITask, IAdminLayer, TaskScheduleEditForm),
                provides=IAJAXFormRenderer)
class TaskEditFormAJAXRenderer(ContextRequestViewAdapter):
    """Task schedule edit form AJAX renderer"""

    def render(self, changes):
        """AJAX result renderer"""
        if not changes:
            return None
        scheduler = get_parent(self.context, IScheduler)
        return {
            'callbacks': [
                get_json_table_row_refresh_callback(scheduler, self.request,
                                                    SchedulerTasksTable, self.context)
            ]
        }


@adapter_config(name='cron-task-schedule.group',
                required=(ICronTask, IAdminLayer, TaskScheduleEditForm),
                provides=IGroup)
class CronTaskScheduleEditFormGroup(FormGroupChecker):
    """Cron-style task schedule edit form"""

    fields = Fields(ICronTaskScheduling)


@viewlet_config(name='cron-task-schedule.help',
                context=ICronTask, layer=IAdminLayer, view=CronTaskScheduleEditFormGroup,
                manager=IHelpViewletManager, weight=1)
class CronTaskScheduleEdirFormHelp(AlertMessage):
    """Cron-style task schedule edit form help"""

    _message = _("You can enter values like in a \"classical\" crontab: you can set individual "
                 "values, ranges (using a dash as separator), steps (using */x), or multiple "
                 "values (using a comma as separator); steps are used to start a task, for "
                 "example, every five minutes, in the form \"*/5\".\n"
                 "For example: a value of \"3-6,8,10,12,14,16-19\" in the \"hours\" field would "
                 "mean that the task is to be run each hour from 3 to 6, then at 8, 10, 12 and "
                 "14, and finally each hour from 16 to 19; by setting \"*/2\" in the month days "
                 "field, the task would only run one day out of two.\n"
                 "An asterisk means that all possible values are selected (warning when setting "
                 "this value on seconds!!)")


@adapter_config(name='date-task-schedule.group',
                required=(IDateTask, IAdminLayer, TaskScheduleEditForm),
                provides=IGroup)
class DateTaskScheduleEditFormGroup(FormGroupChecker):
    """Date-style task schedule edit form"""

    fields = Fields(IDateTaskScheduling)


@adapter_config(name='loop-task-schedule.group',
                required=(ILoopTask, IAdminLayer, TaskScheduleEditForm),
                provides=IGroup)
class LoopTaskScheduleEditFormGroup(FormGroupChecker):
    """Loop-style task schedule edit form"""

    fields = Fields(ILoopTaskScheduling)
