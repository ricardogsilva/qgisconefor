import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from processing.core.Processing import Processing
from processing.core.AlgorithmProvider import AlgorithmProvider
from processing.core.ProcessingConfig import Setting, ProcessingConfig

import processingconeforinputs
import processingconeforprocessor

import resources_rc

class ProcessingConeforProvider(AlgorithmProvider):

    DESCRIPTION = 'Conefor (Habitat patches and landscape connectivity analysis)'
    NAME = 'Conefor'
    CONEFOR_EXECUTABLE_PATH = 'CONEFOR_EXECUTABLE_PATH'

    def getDescription(self):
        return self.DESCRIPTION

    def initializeSettings(self):
        '''
        '''

        AlgorithmProvider.initializeSettings(self)
        ProcessingConfig.addSetting(
            Setting(self.getDescription(),
                    self.CONEFOR_EXECUTABLE_PATH,
                    'Path to the conefor binary',
                    self._get_conefor_path())
                    #valuetype=Setting.FILE
        )

    def unload(self):
        AlgorithmProvider.unload(self)
        ProcessingConfig.removeSetting(self.A_TESTING_SETTING)

    def getName(self):
        return self.NAME

    def getIcon(self):
        return QIcon(':/plugins/qgisconefor/assets/icon.png')

    def _loadAlgorithms(self):
        self.algs = [
            processingconeforinputs.ConeforInputsPointAttribute(),
            processingconeforinputs.ConeforInputsPolygonAttribute(),
            processingconeforinputs.ConeforInputsPolygonArea(),
            processingconeforinputs.ConeforInputsPointCentroid(),
            processingconeforinputs.ConeforInputsPolygonCentroid(),
            processingconeforinputs.ConeforInputsPolygonEdge(),
            processingconeforinputs.ConeforInputsPointCentroidDistance(),
            processingconeforinputs.ConeforInputsPolygonCentroidDistance(),
            processingconeforinputs.ConeforInputsPolygonEdgeDistance(),
            processingconeforprocessor.ConeforNCProcessor(),
            processingconeforprocessor.ConeforNLProcessor(),
            processingconeforprocessor.ConeforHProcessor(),
            processingconeforprocessor.ConeforCCPProcessor(),
            processingconeforprocessor.ConeforLCPProcessor(),
            processingconeforprocessor.ConeforIICProcessor(),
            processingconeforprocessor.ConeforBCProcessor(),
            processingconeforprocessor.ConeforBCIICProcessor(),
            processingconeforprocessor.ConeforFDistanceProcessor(),
            processingconeforprocessor.ConeforFProbabilityProcessor(),
            processingconeforprocessor.ConeforAWFDistanceProcessor(),
            processingconeforprocessor.ConeforAWFProbabilityProcessor(),
            processingconeforprocessor.ConeforPCDistanceProcessor(),
            processingconeforprocessor.ConeforPCProbabilityProcessor(),
            processingconeforprocessor.ConeforBCPCDistanceProcessor(),
            processingconeforprocessor.ConeforBCPCProbabilityProcessor(),
        ]

    def _get_conefor_path(self):
        conefor_path = ProcessingConfig.getSetting(self.CONEFOR_EXECUTABLE_PATH)
        if conefor_path is None:
            conefor_path = ''
        return os.path.abspath(unicode(conefor_path))
