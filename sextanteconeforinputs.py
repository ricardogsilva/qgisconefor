import os
from functools import partial

from PyQt4.QtCore import QObject, SIGNAL
from PyQt4.QtGui import QIcon

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
from sextante.outputs.OutputVector import OutputVector
from sextante.outputs.OutputFile import OutputFile
#from sextante.outputs.OutputDirectory import OutputDirectory

from coneforinputsprocessor import InputsProcessor

class ConeforInputsBase(GeoAlgorithm):

    # to be reimplemented in child classes
    NAME = None
    SHAPE_TYPE = None
    GROUP = None

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
                            partial(self.update_progress, progress,
                            the_algorithm))

            QObject.connect(the_algorithm, SIGNAL('update_info'),
                            partial(self.update_info, progress))
            self._run_the_algorithm(the_algorithm, only_selected, layer,
                                    unique_attribute)
            #SextanteResults.addResult('teste',
            #                          '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException(e.message)

    def getIcon(self):
        return QIcon(':/plugins/conefor_dev/icon.png')

    def helpFile(self):
        return 'qrc:/plugins/conefor_dev/help.html'

    def update_progress(self, progress_obj, processor):
        progress_obj.setPercentage(processor.global_progress)

    def update_info(self, progress_obj, info, section=0):
        progress_obj.setInfo(info)

    def _run_the_algorithm(self, algorithm_processor, use_selected, layer,
                           unique_attribute):
        # to be reimplemented in child classes
        raise NotImplementedError


class ConeforInputsAttribute(ConeforInputsBase):

    def defineCharacteristics(self):
        ConeforInputsBase.defineCharacteristics(self)
        self.addParameter(ParameterTableField(self.PROCESS_ATTRIBUTE,
                          'Attribute query field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
                       'attribute query file'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):
        out_path = self.getOutputValue(self.OUTPUT_FILE)
        process_attribute = self.getParameterValue(self.PROCESS_ATTRIBUTE)
        output_dir, attribute_file_name = os.path.split(out_path)
        processor.process_layer(layer, unique_attribute, output_dir,
                                progress_step=100, attribute=process_attribute,
                                attribute_file_name=attribute_file_name,
                                only_selected_features=use_selected,
                                load_distance_files_to_canvas=False)


class ConeforInputsArea(ConeforInputsBase):

    def defineCharacteristics(self):
        ConeforInputsBase.defineCharacteristics(self)
        self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
                       'area query file'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):
        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, area_file_name = os.path.split(out_path)
        print('aqui')
        processor.process_layer(layer, unique_attribute, output_dir,
                                progress_step=100,
                                area_file_name=area_file_name,
                                only_selected_features=use_selected,
                                load_distance_files_to_canvas=False)


class ConeforInputsCentroid(ConeforInputsBase):

    def defineCharacteristics(self):
        ConeforInputsBase.defineCharacteristics(self)
        self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
                       'centroid query file'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):
        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, centroid_file_name = os.path.split(out_path)
        processor.process_layer(layer, unique_attribute, output_dir,
                                progress_step=100,
                                centroid_file_name=centroid_file_name,
                                only_selected_features=use_selected,
                                load_distance_files_to_canvas=False)


class ConeforInputsEdge(ConeforInputsBase):

    def defineCharacteristics(self):
        ConeforInputsBase.defineCharacteristics(self)
        self.addOutput(OutputFile(self.OUTPUT_FILE, 'output edge ' \
                       'distances file'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, edge_file_name = os.path.split(out_path)
        processor.process_layer(layer, unique_attribute, output_dir,
                                progress_step=100,
                                edge_file_name=edge_file_name,
                                only_selected_features=use_selected,
                                load_distance_files_to_canvas=False)


class ConeforInputsCentroidDistance(ConeforInputsBase):

    def defineCharacteristics(self):
        ConeforInputsBase.defineCharacteristics(self)
        self.addOutput(OutputVector(self.OUTPUT_FILE, 'output ' \
                       'shapefile where the calculated distances will be ' \
                       'saved'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, shape_name = os.path.split(out_path)
        processor.process_layer(layer, unique_attribute, output_dir,
                                progress_step=100,
                                centroid_distance_file_name=shape_name,
                                only_selected_features=use_selected,
                                load_distance_files_to_canvas=False)


class ConeforInputsEdgeDistance(ConeforInputsBase):

    def defineCharacteristics(self):
        ConeforInputsBase.defineCharacteristics(self)
        self.addOutput(OutputVector(self.OUTPUT_FILE, 'output ' \
                       'shapefile where the calculated distances will be ' \
                       'saved'))

    def _run_the_algorithm(self, processor, use_selected, layer,
                           unique_attribute):

        out_path = self.getOutputValue(self.OUTPUT_FILE)
        output_dir, shape_name = os.path.split(out_path)
        processor.process_layer(layer, unique_attribute, output_dir,
                                progress_step=100,
                                edge_distance_file_name=shape_name,
                                only_selected_features=use_selected,
                                load_distance_files_to_canvas=False)


class ConeforInputsPointAttribute(ConeforInputsAttribute):
    SHAPE_TYPE = 0
    GROUP = 'Points'
    NAME = 'Prepare inputs - Attribute query [%s]' % GROUP

class ConeforInputsPolygonAttribute(ConeforInputsAttribute):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'
    NAME = 'Prepare inputs - Attribute query [%s]' % GROUP

class ConeforInputsPointArea(ConeforInputsArea):
    SHAPE_TYPE = 0
    GROUP = 'Points'
    NAME = 'Prepare inputs - Area query [%s]' % GROUP

class ConeforInputsPolygonArea(ConeforInputsArea):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'
    NAME = 'Prepare inputs - Area query [%s]' % GROUP

class ConeforInputsPointCentroid(ConeforInputsCentroid):
    SHAPE_TYPE = 0
    GROUP = 'Points'
    NAME = 'Prepare inputs - Centroid query [%s]' % GROUP

class ConeforInputsPolygonCentroid(ConeforInputsCentroid):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'
    NAME = 'Prepare inputs - Centroid query [%s]' % GROUP

class ConeforInputsPointEdge(ConeforInputsEdge):
    SHAPE_TYPE = 0
    GROUP = 'Points'
    NAME = 'Prepare inputs - Edge query [%s]' % GROUP

class ConeforInputsPolygonEdge(ConeforInputsEdge):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'
    NAME = 'Prepare inputs - Edge query [%s]' % GROUP

class ConeforInputsPointCentroidDistance(ConeforInputsCentroidDistance):
    SHAPE_TYPE = 0
    GROUP = 'Points'
    NAME = 'Misc - Centroid distance vector [%s]' % GROUP

class ConeforInputsPolygonCentroidDistance(ConeforInputsCentroidDistance):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'
    NAME = 'Misc - Centroid distance vector [%s]' % GROUP

class ConeforInputsPointEdgeDistance(ConeforInputsEdgeDistance):
    SHAPE_TYPE = 0
    GROUP = 'Points'
    NAME = 'Misc - Edge distance vector [%s]' % GROUP

class ConeforInputsPolygonEdgeDistance(ConeforInputsEdgeDistance):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'
    NAME = 'Misc - Edge distance vector [%s]' % GROUP
