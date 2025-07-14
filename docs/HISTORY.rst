Changelog
=========

2.7.0
-----
 - added pipeline task to chain tasks together
 - updated execution reports format to Markdown text
 - small interfaces refactoring to avoid recursive imports

2.6.2
-----
 - added sort order data attribute to jobs table

2.6.1
-----
 - added commit on external tasks run to activate transactional chat messages
 - updated history table sort

2.6.0
-----
 - added task attribute to separate ZODB-based tasks (using classic transactions attempts) from other "external"
   tasks (using attempts only to store execution reports)
 - code cleanup...

2.5.0
-----
 - allow storage of task execution report as attachment

2.4.9
-----
 - updated Gitlab-CI
 - added support for Python 3.12

2.4.8
-----
 - added new exception handler to catch invalid tasks triggers which can break scheduler process startup

2.4.7
-----
 - avoid exception after task execution when chat is disabled

2.4.6
-----
 - added source task as chat message user attribute to correctly get message targets

2.4.5
-----
 - updated ZMI menus and views permissions for guests better access

2.4.4
-----
 - updated REST API caller task exceptions handler
 - updated ZMI permissions

2.4.3
-----
 - moved PyAMS_utils finder helper to new module

2.4.2
-----
 - updated clone column hint
 - added warning message in folder clone form

2.4.1
-----
 - updated history item path in notifications

2.4.0
-----
 - added folder properties edit form
 - refactored task getters
 - updated folder clone form to correctly handle folders with inner folders and tasks

2.3.0
-----
 - added task container interface, and task folder component

2.2.0
-----
 - added property to REST API caller task to set a custom SSL CA bundle

2.1.0
-----
 - added support for modal targets to notifications
 - updated task label in tasks table view

2.0.1
-----
 - updated modal forms title

2.0.0
-----
 - upgraded to Pyramid 2.0

1.11.0
------
 - added support for API keys authentication in REST tasks
 - added support for custom HTTP headers in REST tasks

1.10.2
------
 - added check for broken tasks on application start
 - added support for scheduler configuration from Pyramid settings file
 - added support for Python 3.11

1.10.1
------
 - added content-type property to REST service client task

1.10.0
------
 - allow usage of dynamic text formatters into scheduler HTTP client tasks

1.9.1
-----
 - use new PyAMS_security constant

1.9.0
-----
 - added new status to be used on task execution failure
 - added new task status class mapping

1.8.0
-----
 - added exception class to handle task execution errors
 - updated notification status on task execution error

1.7.1
-----
 - updated JWT tokens handler in REST API client task

1.7.0
-----
 - added properties to REST API client task to set login and password attributes of
   JWT authentication service

1.6.7
-----
 - updated Gitlab-CI for Python 3.10

1.6.6
-----
 - added support for Python 3.10
 - PyAMS_security interfaces refactoring
 - use new ZMI attribute switcher column in task notifications

1.6.5
-----
 - check job next run time when getting list of scheduled jobs
 - added ping message handler to check process communication

1.6.4
-----
 - use constants to define tasks schedule modes
 - use new generic ZMI columns classes in notifications management view

1.6.3
-----
 - translation update

1.6.2
-----
 - updated new request base URL when running a task to be able to generate correct
   absolute URLs

1.6.1
-----
 - added check for correct host configuration before sending notifications

1.6.0
-----
 - added support for *PyAMS_chat* package to send notifications after task execution

1.5.0
-----
 - replaced after-commit hooks with new PyAMS_utils transaction manager
 - added option to display scheduler access menu in site home

1.4.3
-----
 - updated history item view form CSS class

1.4.2
-----
 - version mismatch

1.4.1
-----
 - added return link to site utilities view from scheduler tasks view

1.4.0
-----
 - added scheduler label adapter
 - updated add and edit forms title
 - updated package include scan

1.3.3
-----
 - updated menus order in management interface
 - replace ITableElementName interface with IObjectLabel

1.3.2
-----
 - reset task internal ID after cloning
 - corrected check on request registry when removing task

1.3.1
-----
 - added and updated task add and edit forms AJAX renderer
 - Pylint updates

1.3.0
-----
 - updated tasks notifications management, to be able to add new notifications modes
   easily
 - moved all task related interfaces to pyams_scheduler.interfaces.task module

1.2.1
-----
 - corrected timezone error in task history check
 - added missing "context" argument to permission check
 - small updates in tasks management forms

1.2.0
-----
 - removed support for Python < 3.7
 - updated synchronizer exceptions
 - updated FTP synchronizer handler

1.1.1
-----
 - updated scheduler generations updater order

1.1.0
-----
 - added task copy hook
 - added action to duplicate an existing task

1.0.1
-----
 - updated Gitlab-CI configuration
 - removed Travis-CI configuration

1.0.0
-----
 - initial release
