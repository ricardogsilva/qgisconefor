'''
This file initializes the plugin, making it known to QGIS.
'''

#def name():
#    return 'Conefor Inputs'
#
#def description():
#    return 'Conefor tool for generating txt files of calculations and attributes'
#
#def version():
#    return 'Version 0.2'
#
#def qgisMinimumVersion():
#    return '1.9'
#
#def authorName():
#    return 'Ricardo Garcia Silva'
#
def classFactory(iface):
    from coneforinputs import ConeforProcessor
    return ConeforProcessor(iface)
