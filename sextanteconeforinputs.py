from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.parameters.ParameterMultipleInput import ParameterMultipleInput

from coneforinputsprocessor import InputsProcessor

class ConeforInputsProcessor(GeoAlgorithm):

    OUTPUT_LAYERS = 'OUTPUT_LAYERS'
    INPUT_LAYERS = 'INPUT_LAYERS'

    def defineCharacteristics(self):

        self.name = 'Prepare inputs for Conefor'
        self.group = 'Conefor'
        self.addParameter()
