=======================
PyAMS scheduler package
=======================

.. contents::


What is PyAMS?
==============

PyAMS (Pyramid Application Management Suite) is a small suite of packages written for applications
and content management with the Pyramid framework.

**PyAMS** is actually mainly used to manage web sites through content management applications (CMS,
see PyAMS_content package), but many features are generic and can be used inside any kind of web
application.

All PyAMS documentation is available on `ReadTheDocs <https://pyams.readthedocs.io>`_; source code
is available on `Gitlab <https://gitlab.com/pyams>`_ and pushed to `Github
<https://github.com/py-ams>`_. Doctests are available in the *doctests* source folder.


What is PyAMS scheduler?
========================

PyAMS_scheduler is an extension package for PyAMS which can be used to handle tasks scheduling.
The kind of tasks that can be scheduled are local commands, remote commands started through
SSH, HTTP or HTTPS remote services, REST APIs, SQL commands, files transfers, or custom
commands that can be provided by special extension packages; you can also create pipelines,
where the output of a command can be used as input for the next command.

The tasks definition is stored into the ZODB, as well as the execution history of each task.

The package relies on ZeroMQ for process synchronisation, and APScheduler for tasks scheduling.
