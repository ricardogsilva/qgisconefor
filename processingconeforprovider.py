import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from processing.core.Processing import Processing
from processing.core.AlgorithmProvider import AlgorithmProvider
from processing.core.ProcessingConfig import Setting, ProcessingConfig
from processing.modeler.ModelerAlgorithm import ModelerAlgorithm
from processing.modeler.WrongModelException import WrongModelException
#from processing.core.ProcessingLog import ProcessingLog

import processingconeforinputs
import processingconeforprocessor

import resources_rc

class ProcessingConeforProvider(AlgorithmProvider):

    DESCRIPTION = 'Conefor (Habitat patches and landscape connectivity analysis)'
    NAME = 'Conefor'
    CONEFOR_EXECUTABLE_PATH = 'CONEFOR_EXECUTABLE_PATH'
    RUN_THROUGH_WINE = 'RUN_THROUGH_WINE'

    def getDescription(self):
        return self.DESCRIPTION

    def initializeSettings(self):
        '''
        '''

        AlgorithmProvider.initializeSettings(self)
        ProcessingConfig.addSetting(
            Setting(self.getDescription(),
                    self.CONEFOR_EXECUTABLE_PATH,
                    'Path to conefor.exe',
                    self._get_conefor_path())
        )

    def unload(self):
        AlgorithmProvider.unload(self)
        ProcessingConfig.removeSetting(self.A_TESTING_SETTING)

    def getName(self):
        return self.NAME

    def getIcon(self):
        return QIcon(':/plugins/conefor_dev/icon.png')

    #def _load_models(self):
    #    #modeler_provider = Processing.getProviderFromName('modeler')
    #    modeler_provider = Processing.modeler
    #    # this code has been adapted from QGIS
    #    # processing.modeler.ModelerAlgorithmProvider.py
    #    module_path = os.path.abspath(processingconeforprocessor.__file__)
    #    plugin_dir = os.path.dirname(module_path)
    #    models_dir = os.path.join(plugin_dir, 'models')
    #    for model_file in os.listdir(models_dir):
    #        if model_file.endswith('.model'):
    #            alg = ModelerAlgorithm()
    #            full_path = os.path.join(models_dir, model_file)
    #            alg.openModel(full_path)
    #            if alg.name.strip() != '':
    #                modeler_provider.algs.append(alg)
    #    #print('modeler_provider algs: %s' % [a.name for a in modeler_provider.algs])

    def _loadAlgorithms(self):
        self.algs = [
            processingconeforinputs.ConeforInputsPointAttribute(),
            processingconeforinputs.ConeforInputsPolygonAttribute(),
            processingconeforinputs.ConeforInputsPointArea(),
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
        #self._load_models()

    def _get_conefor_path(self):
        conefor_path = ProcessingConfig.getSetting(self.CONEFOR_EXECUTABLE_PATH)
        if conefor_path is None:
            conefor_path = ''
        return os.path.abspath(unicode(conefor_path))
