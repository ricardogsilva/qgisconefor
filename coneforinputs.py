#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
A QGIS plugin for writing input files to the Conefor software.
'''

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from coneforinputsprocessor import InputsProcessor
from conefordialog import ConeforDialog

from processing.core.Processing import Processing
from processingconeforprovider import ProcessingConeforProvider


class NoFeaturesToProcessError(Exception):
    pass


class ConeforProcessor(object):

    _plugin_name = 'Conefor inputs'

    def __init__(self, iface):
        self.iface = iface
        self.registry = QgsMapLayerRegistry.instance()
        project_crs = self.iface.mapCanvas().mapRenderer().destinationCrs()
        self.processor = InputsProcessor(project_crs)
        self.processing_provider = ProcessingConeforProvider()

    def initGui(self):
        Processing.addProvider(self.processing_provider)
        self.action = QAction(QIcon(':plugins/conefor_dev/icon.png'), 
                              self._plugin_name, self.iface.mainWindow())
        QObject.connect(self.action, SIGNAL('triggered()'), self.run)
        self.iface.addPluginToVectorMenu('&Conefor inputs', self.action)

    def unload(self):
        self.iface.removePluginVectorMenu('&Conefor inputs', self.action)
        Processing.removeProvider(self.processing_provider)

    def run(self):
        dialog = ConeforDialog(self)
        result = dialog.exec_()
