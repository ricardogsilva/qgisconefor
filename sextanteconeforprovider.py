from PyQt4.QtCore import *
from PyQt4.QtGui import *

from sextante.core.AlgorithmProvider import AlgorithmProvider
from sextante.core.SextanteConfig import Setting, SextanteConfig
from sextante.core.SextanteLog import SextanteLog

from sextanteconeforinputs import ConeforInputsPolygons, ConeforInputsPoints, \
    ConeforInputsPolygonAttribute, \
    ConeforInputsPolygonArea, \
    ConeforInputsPolygonCentroid, \
    ConeforInputsPolygonEdge, \
    ConeforInputsPolygonCentroidDistance, \
    ConeforInputsPolygonEdgeDistance
#from sextanteconefor import ConeforProcessor

import resources_rc

class SextanteConeforProvider(AlgorithmProvider):

    _name = 'Conefor'
    A_TESTING_SETTING = 'My_testing_setting'

    def __init__(self):
        AlgorithmProvider.__init__(self)
        self.createAlgsList()

    def getDescription(self):
        return 'Conefor (Habitat patches and landscape connectivity analysis)'

    def initializeSettings(self):
        '''
        '''

        AlgorithmProvider.initializeSettings(self)
        SextanteConfig.addSetting(
            Setting(self._name,
                    self.A_TESTING_SETTING,
                    'Some text',
                    'And more text')
        )

    def unload(self):
        AlgorithmProvider.unload(self)
        SextanteConfig.removeSetting(self.A_TESTING_SETTING)

    def getName(self):
        return self._name

    def getIcon(self):
        return QIcon(':/plugins/conefor_dev/icon.png')
        #return AlgorithmProvider.getIcon(self)

    def createAlgsList(self):
        self.preloaded_algs = [
            ConeforInputsPolygons(),
            ConeforInputsPoints(),
            ConeforInputsPolygonAttribute(),
            ConeforInputsPolygonArea(),
            ConeforInputsPolygonCentroid(),
            ConeforInputsPolygonEdge(),
            ConeforInputsPolygonCentroidDistance(),
            ConeforInputsPolygonEdgeDistance(),
        ]
        for alg in self.preloaded_algs:
            alg.provider = self

    def loadAlgorithms(self):
        self.algs = self.preloaded_algs
