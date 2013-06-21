from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.core.Sextante import Sextante
from sextante.parameters.ParameterVector import ParameterVector
from sextante.parameters.ParameterBoolean import ParameterBoolean
from sextante.outputs.OutputFile import OutputFile

from coneforinputsprocessor import InputsProcessor

class ConeforInputsProcessor(GeoAlgorithm):

    OUTPUT_AREA_PATH = 'OUTPUT_AREA_PATH'
    INPUT_LAYER = 'INPUT_LAYER'
    PROCESS_AREA = 'PROCESS_AREA'
    PROCESS_ATTRIBUTE = 'PROCESS_ATTRIBUTE'
    PROCESS_CENTROID = 'PROCESS_CENTROID'
    PROCESS_EDGE = 'PROCESS_EDGE'

    def defineCharacteristics(self):

        self.name = 'Prepare inputs for Conefor'
        self.group = 'Conefor'
        polygon = ParameterVector(self.INPUT_LAYER, 'Input polygon layer',
                                  shapetype=2)
        process_area = ParameterBoolean(self.PROCESS_AREA, 'Process the ' \
                                        'area query?')
        process_attribute = ParameterBoolean(self.PROCESS_ATTRIBUTE,
                                             'Process the attribute query?')
        process_centroid = ParameterBoolean(self.PROCESS_CENTROID,
                                            'Process the centroid distance ' \
                                            'query?')
        process_edge = ParameterBoolean(self.PROCESS_EDGE, 'Process the ' \
                                        'edge distance query?')
        self.addParameter(polygon)
        self.addParameter(process_area)
        self.addParameter(process_attribute)
        self.addParameter(process_centroid)
        self.addParameter(process_edge)
        output_area = OutputFile(self.OUTPUT_AREA_PATH, 'output file where ' \
                                 'the area calculation will be stored',
                                 hidden=True)
        self.addOutput(output_area)

    def getCustomParametersDialog(self):
        # maybe we can use directly the already made GUI...
        return None

    def checkBeforeOpeningParametersDialog(self):
        # seems like a nice place to get the usable layers
        return None

    def processAlgorithm(self, progress):
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        output = self.getOutputValue(self.OUTPUT_AREA_PATH)
        vector_layer = Sextante.getObject(input_file_path)
