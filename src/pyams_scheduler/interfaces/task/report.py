# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

from zope.interface import Attribute, Interface

__docformat__ = 'restructuredtext'


class IReport(Interface):
    """Report interface"""

    report = Attribute('Internal report stream')
    renderer = Attribute('Report text renderer')
    
    def add_padding(self):
        """Add padding to report"""
        
    def remove_padding(self):
        """Remove padding from report"""
        
    def tell(self):
        """Return report stream position"""
        
    def seek(self, position):
        """Move stream to given position"""
        
    def truncate(self):
        """Truncate report stream"""
        
    def write(self, value, prefix='', suffix=''):
        """Write the given value to report"""
        
    def writeln(self, value, prefix='', suffix=''):
        """Write the given value to report, followed by a line break"""
        
    def write_code(self, value):
        """Write the given value to report, enclosed in ```"""
    
    def write_exception(self, *exc_info):
        """Write exception traceback to report, enclosed in ```"""
        
    def getvalue(self):
        """Get report content as HTML"""

    def close(self):
        """Close the report stream"""


class ITaskResultReportInfo(Interface):
    """Pipeline report info interface"""
    
    mimetype = Attribute("Report MIME type")
    filename = Attribute("Report filename")
    content = Attribute("Report content")
