"""
A QGIS plugin for writing input files to the Conefor software.
"""

import qgis.core
import qgis.gui

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction


# Initialize Qt resources from file resources.py
from .resources import *  # noqa

from .coneforinputsprocessor import InputsProcessor
from .conefordialog import ConeforDialog
# from .processing.coneforprovider import ProcessingConeforProvider


class QgisConefor:

    _action_title = "Conefor inputs"

    action: QAction

    def __init__(self, iface: qgis.gui.QgisInterface):
        self.iface = iface
        project_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        self.processor = InputsProcessor(project_crs)
        # self.processing_provider = ProcessingConeforProvider()

    def initGui(self):
        processing_registry = qgis.core.QgsApplication.processingRegistry()
        # processing_registry.addProvider(self.processing_provider)
        self.action = QAction(
            QIcon(":/plugins/qgisconefor/icon.png"),
            self._action_title,
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addPluginToVectorMenu(f"&{self._action_title}", self.action)
        self.iface.addVectorToolBarIcon(self.action)

    def unload(self):
        processing_registry = qgis.core.QgsApplication.processingRegistry()
        # processing_registry.removeProvider(self.processing_provider)
        self.iface.removePluginVectorMenu(f"&{self._action_title}", self.action)
        self.iface.removeVectorToolBarIcon(self.action)

    def run(self):
        dialog = ConeforDialog(self)
        result = dialog.exec_()
