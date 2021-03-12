=======================
PyAMS scheduler package
=======================

Introduction
------------

This package is composed of a set of utility functions, usable into any Pyramid application.

    >>> from pyramid.testing import setUp, tearDown
    >>> config = setUp(hook_zca=True)

    >>> from cornice import includeme as include_cornice
    >>> include_cornice(config)
    >>> from pyams_utils import includeme as include_utils
    >>> include_utils(config)
    >>> from pyams_site import includeme as include_site
    >>> include_site(config)
    >>> from pyams_security import includeme as include_security
    >>> include_security(config)
    >>> from pyams_skin import includeme as include_skin
    >>> include_skin(config)
    >>> from pyams_zmi import includeme as include_zmi
    >>> include_zmi(config)
    >>> from pyams_form import includeme as include_form
    >>> include_form(config)
    >>> from pyams_zmq import includeme as include_zmq
    >>> include_zmq(config)
    >>> from pyams_scheduler import includeme as include_scheduler
    >>> include_scheduler(config)


    >>> tearDown()
