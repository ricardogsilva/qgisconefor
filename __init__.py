'''
This file initializes the plugin, making it known to QGIS.
'''

def classFactory(iface):
    from qgisconefor import ConeforProcessor
    return ConeforProcessor(iface)
