import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from sextante.core.AlgorithmProvider import AlgorithmProvider
from sextante.core.SextanteConfig import Setting, SextanteConfig
from sextante.core.SextanteLog import SextanteLog

from sextanteconeforinputs import \
    ConeforInputsPointAttribute, \
    ConeforInputsPolygonAttribute, \
    ConeforInputsPointArea, \
    ConeforInputsPolygonArea, \
    ConeforInputsPointCentroid, \
    ConeforInputsPolygonCentroid, \
    ConeforInputsPointEdge, \
    ConeforInputsPolygonEdge, \
    ConeforInputsPointCentroidDistance, \
    ConeforInputsPolygonCentroidDistance, \
    ConeforInputsPointEdgeDistance, \
    ConeforInputsPolygonEdgeDistance
from sextanteconeforprocessor import \
    ConeforBinaryIndicesProcessor

import resources_rc

class SextanteConeforProvider(AlgorithmProvider):

    DESCRIPTION = 'Conefor (Habitat patches and landscape connectivity analysis)'
    NAME = 'Conefor'
    CONEFOR_EXECUTABLE_PATH = 'CONEFOR_EXECUTABLE_PATH'
    RUN_THROUGH_WINE = 'RUN_THROUGH_WINE'

    def __init__(self):
        AlgorithmProvider.__init__(self)
        self.createAlgsList()

    def getDescription(self):
        return self.DESCRIPTION

    def initializeSettings(self):
        '''
        '''

        AlgorithmProvider.initializeSettings(self)
        SextanteConfig.addSetting(
            Setting(self.getDescription(),
                    self.CONEFOR_EXECUTABLE_PATH,
                    'Path to conefor.exe',
                    self._get_conefor_path())
        )

    def unload(self):
        AlgorithmProvider.unload(self)
        SextanteConfig.removeSetting(self.A_TESTING_SETTING)

    def getName(self):
        return self.NAME

    def getIcon(self):
        return QIcon(':/plugins/conefor_dev/icon.png')

    def createAlgsList(self):
        self.preloaded_algs = [
            ConeforInputsPointAttribute(),
            ConeforInputsPolygonAttribute(),
            ConeforInputsPointArea(),
            ConeforInputsPolygonArea(),
            ConeforInputsPointCentroid(),
            ConeforInputsPolygonCentroid(),
            ConeforInputsPointEdge(),
            ConeforInputsPolygonEdge(),
            ConeforInputsPointCentroidDistance(),
            ConeforInputsPolygonCentroidDistance(),
            ConeforInputsPointEdgeDistance(),
            ConeforInputsPolygonEdgeDistance(),
            ConeforBinaryIndicesProcessor(),
        ]
        for alg in self.preloaded_algs:
            alg.provider = self

    def loadAlgorithms(self):
        self.algs = self.preloaded_algs

    def _get_conefor_path(self):
        conefor_path = SextanteConfig.getSetting(self.CONEFOR_EXECUTABLE_PATH)
        if conefor_path is None:
            conefor_path = ''
        return os.path.abspath(unicode(conefor_path))
