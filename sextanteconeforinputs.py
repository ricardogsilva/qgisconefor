import os
from functools import partial

from PyQt4.QtCore import QObject, SIGNAL

from sextante.core.SextanteLog import SextanteLog
from sextante.core.SextanteConfig import SextanteConfig
from sextante.core.QGisLayers import QGisLayers
from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.core.GeoAlgorithmExecutionException import \
        GeoAlgorithmExecutionException
from sextante.core.Sextante import Sextante
from sextante.core.SextanteResults import SextanteResults
from sextante.parameters.ParameterVector import ParameterVector
from sextante.parameters.ParameterBoolean import ParameterBoolean
from sextante.parameters.ParameterTableField import ParameterTableField
from sextante.outputs.OutputDirectory import OutputDirectory
from sextante.outputs.OutputVector import OutputVector
from sextante.outputs.OutputFile import OutputFile

from coneforinputsprocessor import InputsProcessor

class ConeforInputsBase(GeoAlgorithm):
    NAME = ''
    GROUP = ''
    INPUT_LAYER = 'INPUT_LAYER'
    UNIQUE_ATTRIBUTE = 'UNIQUE_ATTRIBUTE'
    PROCESS_ATTRIBUTE = 'PROCESS_ATTRIBUTE'
    PROCESS_AREA = 'PROCESS_AREA'
    PROCESS_EDGE = 'PROCESS_EDGE'
    PROCESS_CENTROID = 'PROCESS_CENTROID'
    OUTPUT_FILE = 'OUTPUT_FILE'

    def defineCharacteristics(self):
        self.name = self.NAME
        self.group = self.GROUP
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))

    def processAlgorithm(self, progress):
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        layer = Sextante.getObject(input_file_path)
        unique_attribute = self.getParameterValue(self.UNIQUE_ATTRIBUTE)
        iface = Sextante.getInterface()
        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
        try:
            the_algorithm = InputsProcessor(project_crs)
            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
                            self.update_progress)
            QObject.connect(the_algorithm, SIGNAL('update_info'), 
                            partial(self.update_info, progress))
            self._run_the_algorithm(the_algorithm, only_selected, layer) 
            #SextanteResults.addResult('teste',
            #                          '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException

    def helpFile(self):
        return 'qrc:/plugins/conefor_dev/help.html'

    def update_progress(self, progress_obj, value):
        progress_obj.setProgress(value)

    def update_info(self, progress_obj, info, section=0):
        progress_obj.setInfo(info)

    def _run_the_algorithm(self, algorithm_processor, use_selected, layer,
                           unique_attribute):
        # to be reimplemented in children classes
        raise NotImplementedError


class ConeforInputsPoint(ConeforInputsBase):
    SHAPE_TYPE = 0
    GROUP = 'Points'


class ConeforInputsPolygon(ConeforInputsBase):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'


class ConeforInputsPolygonAttribute(ConeforInputsPolygon):
    NAME = 'Prepare inputs - Attribute query'

    def defineCharacteristics(self):
        ConeforInputsPolygon.defineCharacteristics(self)
        self.addParameter(ParameterTableField(self.PROCESS_ATTRIBUTE,
                          'Attribute query field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
                       'attribute query file'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, attribute_file_name = os.path.split(out_path)
        process_attribute = self.getParameterValue(self.PROCESS_ATTRIBUTE)
        the_algorithm.process_layer(layer, unique_attribute, output_dir,
                                    progress_step=100,
                                    attribute=process_attribute,
                                    only_selected_features=only_selected,
                                    load_distance_files_to_canvas=False)


class ConeforInputsPolygonArea(ConeforInputsPolygon):
    NAME = 'Prepare inputs - Area query'

    def defineCharacteristics(self):
        ConeforInputsPolygon.defineCharacteristics(self)
        self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
                       'area query file'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, area_file_name = os.path.split(out_path)
        the_algorithm.process_layer(layer, unique_attribute, output_dir,
                                    progress_step=100,
                                    area_file_name=area_file_name,
                                    only_selected_features=only_selected,
                                    load_distance_files_to_canvas=False)

class ConeforInputsPolygonCentroid(ConeforInputsPolygon):
    NAME = 'Prepare inputs - Centroid query'

    def defineCharacteristics(self):
        ConeforInputsPolygon.defineCharacteristics(self)
        self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
                       'centroid query file'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, centroid_file_name = os.path.split(out_path)
        the_algorithm.process_layer(layer, unique_attribute, output_dir,
                                    progress_step=100,
                                    centroid_file_name=centroid_file_name,
                                    only_selected_features=only_selected,
                                    load_distance_files_to_canvas=False)


class ConeforInputsPolygonEdge(ConeforInputsPolygon):
    NAME = 'Prepare inputs - Edge query'

    def defineCharacteristics(self):
        ConeforInputsPolygon.defineCharacteristics(self)
        self.addOutput(OutputFile(self.OUTPUT_FILE, 'output edge ' \
                       'distances file'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, edge_file_name = os.path.split(out_path)
        the_algorithm.process_layer(layer, unique_attribute, output_dir,
                                    progress_step=100,
                                    edge_file_name=edge_file_name,
                                    only_selected_features=only_selected,
                                    load_distance_files_to_canvas=False)


class ConeforInputsPolygonCentroidDistance(ConeforInputsPolygon):
    NAME = 'Misc - Centroid distance vector'

    def defineCharacteristics(self):
        self.addOutput(OutputVector(self.OUTPUT_FILE, 'output ' \
                       'shapefile where the calculated distances will be ' \
                       'saved'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, shape_name = os.path.split(out_path)
        the_algorithm.process_layer(layer, unique_attribute, output_dir,
                                    progress_step=100,
                                    centroid_distance_file_name=shape_name,
                                    only_selected_features=only_selected,
                                    load_distance_files_to_canvas=False)


class ConeforInputsPolygonEdgeDistance(ConeforInputsPolygon):
    NAME = 'Misc - Edge distance vector'

    def defineCharacteristics(self):
        self.addOutput(OutputVector(self.OUTPUT_FILE, 'output ' \
                       'shapefile where the calculated distances will be ' \
                       'saved'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, shape_name = os.path.split(out_path)
        the_algorithm.process_layer(layer, unique_attribute, output_dir,
                                    progress_step=100,
                                    edge_distance_file_name=shape_name,
                                    only_selected_features=only_selected,
                                    load_distance_files_to_canvas=False)
