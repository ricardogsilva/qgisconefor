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


class ConeforProcessor(object):

    _plugin_name = 'Conefor inputs'

    def __init__(self, iface):
        self.iface = iface
        self.registry = QgsMapLayerRegistry.instance()
        project_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        self.processor = InputsProcessor(project_crs)
        self.processing_provider = ProcessingConeforProvider()

    def initGui(self):
        Processing.addProvider(self.processing_provider, updateList=True)
        self.action = QAction(QIcon(':plugins/qgisconefor/assets/icon.png'),
                              self._plugin_name, self.iface.mainWindow())
        QObject.connect(self.action, SIGNAL('triggered()'), self.run)
        self.iface.addPluginToVectorMenu('&%s' % self._plugin_name,
                                         self.action)
        self.iface.addVectorToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginVectorMenu('&Conefor inputs', self.action)
        self.iface.removeVectorToolBarIcon(self.action)
        Processing.removeProvider(self.processing_provider)

    def run(self):
        dialog = ConeforDialog(self)
        result = dialog.exec_()
