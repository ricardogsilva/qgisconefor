from sextante.core.SextanteLog import SextanteLog
from sextante.core.SextanteConfig import SextanteConfig
from sextante.core.QGisLayers import QGisLayers
from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.core.GeoAlgorithmExecutionException import \
        GeoAlgorithmExecutionException
from sextante.core.Sextante import Sextante
from sextante.parameters.ParameterVector import ParameterVector
from sextante.parameters.ParameterBoolean import ParameterBoolean
from sextante.parameters.ParameterTableField import ParameterTableField
from sextante.outputs.OutputDirectory import OutputDirectory
log = SextanteLog.addToLog

from coneforinputsprocessor import InputsProcessor

class ConeforInputsProcessor(GeoAlgorithm):

    OUTPUT_DIR = 'OUTPUT_DIR'
    INPUT_LAYER = 'INPUT_LAYER'
    UNIQUE_ATTRIBUTE = 'UNIQUE_ATTRIBUTE'
    PROCESS_ATTRIBUTE = 'PROCESS_ATTRIBUTE'
    PROCESS_AREA = 'PROCESS_AREA'
    PROCESS_CENTROID = 'PROCESS_CENTROID'
    PROCESS_EDGE = 'PROCESS_EDGE'
    DISTANCE_FILES = 'DISTANCE_FILES'

    def _other_characteristics(self):
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addParameter(ParameterTableField(self.PROCESS_ATTRIBUTE,
                          'Attribute query field:', self.INPUT_LAYER,
                          optional=True))
        self.addParameter(ParameterBoolean(self.PROCESS_AREA,
                          'Process the area query?'))
        self.addParameter(ParameterBoolean(self.PROCESS_CENTROID,
                          'Process the centroid distance query?'))
        self.addParameter(ParameterBoolean(self.PROCESS_EDGE,
                          'Process the edge distance query?'))
        self.addParameter(ParameterBoolean(self.DISTANCE_FILES,
                          'Create distance shapefiles?'))
        self.addOutput(OutputDirectory(self.OUTPUT_DIR, 'output directory ' \
                       'where the calculated files will be saved'))

    def defineCharacteristics(self):
        raise NotImplementedError

    def helpFile(self):
        return 'qrc:/plugins/conefor_dev/help.html'

    def getCustomParametersDialog(self):
        # maybe we can use directly the already made GUI...
        return None

    def checkBeforeOpeningParametersDialog(self):
        # seems like a nice place to get the usable layers
        return None

    def processAlgorithm(self, progress):

        # check for the usable layers
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        layer_uri = Sextante.getObject(input_file_path)
        iface = Sextante.getInterface()
        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
        try:
            the_algorithm = InputsProcessor(project_crs)
            the_algorithm.process_layer(
                Sextante.getObject(input_file_path),
                self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                self.getParameterValue(self.PROCESS_AREA),
                self.getParameterValue(self.PROCESS_ATTRIBUTE),
                self.getParameterValue(self.PROCESS_CENTROID),
                self.getParameterValue(self.PROCESS_EDGE),
                self.getOutputValue(self.OUTPUT_DIR),
                100,
                self.getParameterValue(self.DISTANCE_FILES),
                only_selected
            )
        except Exception as e:
            raise GeoAlgorithmExecutionException

class ConeforInputsPoints(ConeforInputsProcessor):

    def defineCharacteristics(self):

        self.name = 'Prepare point inputs for Conefor'
        self.group = 'Conefor'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=0))
        self._other_characteristics()


class ConeforInputsPolygons(ConeforInputsProcessor):

    def defineCharacteristics(self):

        self.name = 'Prepare polygon inputs for Conefor'
        self.group = 'Conefor'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=2))
        self._other_characteristics()
