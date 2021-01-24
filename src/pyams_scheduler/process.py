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

"""PyAMS_scheduler.process module

This module defines the main scheduler base classes, to handle scheduler process and main
tasks management threads.
"""

__docformat__ = 'restructuredtext'

import logging
from datetime import datetime
from threading import Thread

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from pyramid.config import Configurator
from pyramid.threadlocal import manager
from zope.interface import implementer

from pyams_scheduler.interfaces import ISchedulerProcess, ITask, SCHEDULER_NAME
from pyams_scheduler.trigger import ImmediateTaskTrigger
from pyams_site.interfaces import PYAMS_APPLICATION_DEFAULT_NAME, PYAMS_APPLICATION_SETTINGS_KEY
from pyams_utils.zodb import ZODBConnection
from pyams_zmq.handler import ZMQMessageHandler
from pyams_zmq.process import ZMQProcess


LOGGER = logging.getLogger('PyAMS (scheduler)')


class BaseTaskThread(Thread):
    """Base task management thread class"""

    def __init__(self, process, settings):
        Thread.__init__(self)
        self.process = process
        if ITask.providedBy(settings):
            scheduler = settings.__parent__
            self.settings = {
                'zodb_name': scheduler.zodb_name,
                'task_name': settings.__name__,
                'job_id': settings.internal_id
            }
        else:
            self.settings = settings

    def run(self):
        """Thread start method

        Subclasses may override this method, but must call this super()
        method to correctly initialize ZCA hook in the thread.
        """
        registry = self.process.registry
        manager.push({'registry': registry, 'request': None})
        config = Configurator(registry=registry)
        config.hook_zca()

    def _get_connection(self):
        """ZODB connection getter"""
        return ZODBConnection(name=self.settings.get('zodb_name'))


class TaskResettingThread(BaseTaskThread):
    """Task resetting thread

    Task reset is run in another thread, so that:
    - other transactions applied on updated tasks are visible
    - ØMQ request returns immediately to calling process
    """

    def run(self):
        super().run()
        LOGGER.debug("Starting task resetting thread...")
        settings = self.settings
        job_id = settings.get('job_id')
        if job_id is None:
            return
        job_id = str(job_id)
        LOGGER.debug("Loading ZODB connection...")
        with self._get_connection() as root:
            LOGGER.debug("Loaded ZODB root {0!r}".format(root))
            try:
                registry = self.process.registry
                application_name = registry.settings.get(PYAMS_APPLICATION_SETTINGS_KEY,
                                                         PYAMS_APPLICATION_DEFAULT_NAME)
                application = root.get(application_name)
                LOGGER.debug("Loaded application {0!r}".format(application))
                sm = application.getSiteManager()  # pylint: disable=invalid-name
                scheduler_util = sm.get(SCHEDULER_NAME)
                LOGGER.debug("Loaded scheduler utility {0!r}".format(scheduler_util))
                scheduler = self.process.scheduler
                LOGGER.debug("Removing job '{0}'".format(job_id))
                job = scheduler.get_job(job_id)
                if job is not None:
                    LOGGER.debug("Loaded job {0!r} ({0.id!r})".format(job))
                    scheduler.remove_job(job.id)
                LOGGER.debug("Loading scheduler task '{0}'".format(
                    settings.get('task_name').lower()))
                task = scheduler_util.get(settings.get('task_name').lower())
                LOGGER.debug("Loaded scheduler task {0!r}".format(task))
                if (task is not None) and task.is_runnable():
                    trigger = task.get_trigger()
                    LOGGER.debug("Getting task trigger {0!r}".format(trigger))
                    LOGGER.debug("Adding new job to scheduler {0!r}".format(scheduler))
                    scheduler.add_job(task, trigger,
                                      id=str(task.internal_id),
                                      name=task.name,
                                      kwargs={
                                          'zodb_name': scheduler_util.zodb_name,
                                          'registry': registry
                                      })
                    LOGGER.debug("Added job")
            except:  # pylint: disable=bare-except
                LOGGER.exception("An exception occurred:")


class TaskRemoverThread(BaseTaskThread):
    """Task remover thread"""

    def run(self):
        super().run()
        LOGGER.debug("Starting task remover thread...")
        settings = self.settings
        job_id = settings.get('job_id')
        if job_id is None:
            return
        job_id = str(job_id)
        LOGGER.debug("Loading ZODB connection...")
        with self._get_connection() as root:
            LOGGER.debug("Loaded ZODB root {0!r}".format(root))
            try:
                registry = self.process.registry
                application_name = registry.settings.get(PYAMS_APPLICATION_SETTINGS_KEY,
                                                         PYAMS_APPLICATION_DEFAULT_NAME)
                application = root.get(application_name)
                LOGGER.debug("Loaded application {0!r}".format(application))
                sm = application.getSiteManager()  # pylint: disable=invalid-name
                scheduler_util = sm.get(SCHEDULER_NAME)
                LOGGER.debug("Loaded scheduler utility {0!r}".format(scheduler_util))
                scheduler = self.process.scheduler
                LOGGER.debug("Removing job '{0}'".format(job_id))
                job = scheduler.get_job(job_id)
                if job is not None:
                    LOGGER.debug("Loaded job {0!r} ({0.id!r})".format(job))
                    scheduler.remove_job(job.id)
                LOGGER.debug("Removed job")
            except:  # pylint: disable=bare-except
                LOGGER.exception("An exception occurred:")


class TaskRunnerThread(BaseTaskThread):
    """Task immediate runner thread"""

    def run(self):
        super().run()
        LOGGER.debug("Starting task runner thread...")
        settings = self.settings
        job_id = settings.get('job_id')
        if job_id is None:
            return
        LOGGER.debug("Loading ZODB connection...")
        with self._get_connection() as root:
            LOGGER.debug("Loaded ZODB root {0!r}".format(root))
            try:
                registry = self.process.registry
                application_name = registry.settings.get(PYAMS_APPLICATION_SETTINGS_KEY,
                                                         PYAMS_APPLICATION_DEFAULT_NAME)
                application = root.get(application_name)
                LOGGER.debug("Loaded application {0!r}".format(application))
                sm = application.getSiteManager()  # pylint: disable=invalid-name
                scheduler_util = sm.get(SCHEDULER_NAME)
                LOGGER.debug("Loaded scheduler utility {0!r}".format(scheduler_util))
                scheduler = self.process.scheduler
                LOGGER.debug("Loading scheduler task '{0}'".format(
                    settings.get('task_name').lower()))
                task = scheduler_util.get(settings.get('task_name').lower())
                LOGGER.debug("Loaded scheduler task {0!r}".format(task))
                if task is not None:
                    trigger = ImmediateTaskTrigger()
                    LOGGER.debug("Getting task trigger {0!r}".format(trigger))
                    LOGGER.debug("Adding new job to scheduler {0!r}".format(scheduler))
                    scheduler.add_job(task, trigger,
                                      id='{0.internal_id}::{1}'.format(
                                          task, datetime.utcnow().isoformat()),
                                      name=task.name,
                                      kwargs={
                                          'zodb_name': scheduler_util.zodb_name,
                                          'registry': self.process.registry,
                                          'run_immediate': True
                                      })
                    LOGGER.debug("Added job")
            except:  # pylint: disable=bare-except
                LOGGER.exception("An exception occurred:")


class SchedulerHandler:
    """Scheduler handler"""

    process = None

    def test(self, settings):  # pylint: disable=unused-argument
        """Scheduler handler test"""
        messages = [
            'OK - Tasks scheduler ready to handle requests.',
            '{0} currently running jobs'.format(len(self.process.scheduler.get_jobs()))
        ]
        return [200, '\n'.join(messages)]

    def get_jobs(self, settings):  # pylint: disable=unused-argument
        """Getter of currently running jobs"""
        scheduler = self.process.scheduler
        return [200, [{
            'id': job.id,
            'name': job.name,
            'trigger': '{0!s}'.format(job.trigger),
            'next_run': job.next_run_time.timestamp()
        } for job in scheduler.get_jobs()]]

    def reset_task(self, settings):
        """Reset task with given properties"""
        TaskResettingThread(self.process, settings).start()
        return [200, 'OK']

    def remove_task(self, settings):
        """Remove task with given properties"""
        TaskRemoverThread(self.process, settings).start()
        return [200, 'OK']

    def run_task(self, settings):
        """Run task with given properties"""
        TaskRunnerThread(self.process, settings).start()
        return [200, 'OK']


class SchedulerMessageHandler(ZMQMessageHandler):
    """ØMQ scheduler messages handler"""

    handler = SchedulerHandler


@implementer(ISchedulerProcess)
class SchedulerProcess(ZMQProcess):
    """ØMQ tasks scheduler process"""

    def __init__(self, zmq_address, handler, auth, clients, registry):
        # pylint: disable=too-many-arguments
        super().__init__(zmq_address, handler, auth, clients, registry)
        self.scheduler = BackgroundScheduler()
        self.jobstore = MemoryJobStore()

    def run(self):
        if self.scheduler is not None:
            self.scheduler.add_jobstore(self.jobstore, 'default')
            self.scheduler.start()
        ZMQProcess.run(self)
