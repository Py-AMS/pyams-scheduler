#
# Copyright (c) 2015-2019 Thierry Florac <tflorac AT ulthar.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

"""
This module contains PyAMS scheduler package
"""
import os
from setuptools import setup, find_packages


DOCS = os.path.join(os.path.dirname(__file__),
                    'docs')

README = os.path.join(DOCS, 'README.txt')
HISTORY = os.path.join(DOCS, 'HISTORY.txt')

version = '1.3.2'
long_description = open(README).read() + '\n\n' + open(HISTORY).read()

tests_require = [
    'pyams_zmi',
    'pyramid_zcml',
    'zope.exceptions'
]

setup(name='pyams_scheduler',
      version=version,
      description="PyAMS tasks scheduler",
      long_description=long_description,
      classifiers=[
          "License :: OSI Approved :: Zope Public License",
          "Development Status :: 4 - Beta",
          "Programming Language :: Python",
          "Framework :: Pyramid",
          "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      keywords='Pyramid PyAMS',
      author='Thierry Florac',
      author_email='tflorac@ulthar.net',
      url='https://pyams.readthedocs.io',
      license='ZPL',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=[],
      include_package_data=True,
      package_data={'': ['*.zcml', '*.txt', '*.pt', '*.pot', '*.po', '*.mo',
                         '*.png', '*.gif', '*.jpeg', '*.jpg', '*.css', '*.js']},
      zip_safe=False,
      # uncomment this to be able to run tests with setup.py
      test_suite="pyams_scheduler.tests.test_utilsdocs.test_suite",
      tests_require=tests_require,
      extras_require=dict(test=tests_require),
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'apscheduler',
          'chardet',
          'paramiko',
          'persistent',
          'pyams_layer',
          'pyams_mail',
          'pyams_security',
          'pyams_site',
          'pyams_utils',
          'pyams_zmq',
          'pyramid',
          'pyramid_mailer',
          'requests',
          'transaction',
          'zope.annotation',
          'zope.component',
          'zope.componentvocabulary',
          'zope.container',
          'zope.interface',
          'zope.intid',
          'zope.lifecycleevent',
          'zope.location',
          'zope.schema',
          'zope.traversing'
      ],
      entry_points={
          'zodbupdate': [
              'renames = pyams_scheduler.generations:RENAMED_CLASSES'
          ]
      })
