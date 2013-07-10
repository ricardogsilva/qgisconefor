from sextante.core.AlgorithmProvider import AlgorithmProvider
from sextante.core.SextanteConfig import Setting, SextanteConfig
from sextante.core.SextanteLog import SextanteLog

from sextanteconeforinputs import ConeforInputsPolygons, ConeforInputsPoints
#from sextanteconefor import ConeforProcessor

class SextanteConeforProvider(AlgorithmProvider):

    _name = 'Conefor'
    A_TESTING_SETTING = 'My_testing_setting'

    def __init__(self):
        AlgorithmProvider.__init__(self)
        self.algList = [
            ConeforInputsPolygons(),
            ConeforInputsPoints(),
        ]
        for alg in self.algList:
            alg.provider = self

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
        return AlgorithmProvider.getIcon(self)

    def loadAlgorithms(self):
        self.algs = self.algList
