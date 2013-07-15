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

#class ConeforInputsProcessor(GeoAlgorithm):
#
#    OUTPUT_DIR = 'OUTPUT_DIR'
#    INPUT_LAYER = 'INPUT_LAYER'
#    UNIQUE_ATTRIBUTE = 'UNIQUE_ATTRIBUTE'
#    PROCESS_ATTRIBUTE = 'PROCESS_ATTRIBUTE'
#    PROCESS_AREA = 'PROCESS_AREA'
#    PROCESS_CENTROID = 'PROCESS_CENTROID'
#    PROCESS_EDGE = 'PROCESS_EDGE'
#    DISTANCE_FILES = 'DISTANCE_FILES'
#    LOAD_DISTANCE_FILES = 'LOAD_DISTANCE_FILES'
#
#    def _other_characteristics(self):
#        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
#                          'ID field:', self.INPUT_LAYER,
#                          optional=False))
#        self.addParameter(ParameterTableField(self.PROCESS_ATTRIBUTE,
#                          'Attribute query field:', self.INPUT_LAYER,
#                          optional=True))
#        self.addParameter(ParameterBoolean(self.PROCESS_AREA,
#                          'Process the area query?'))
#        self.addParameter(ParameterBoolean(self.PROCESS_CENTROID,
#                          'Process the centroid distance query?'))
#        self.addParameter(ParameterBoolean(self.PROCESS_EDGE,
#                          'Process the edge distance query?'))
#        self.addParameter(ParameterBoolean(self.DISTANCE_FILES,
#                          'Create distance shapefiles?'))
#        self.addParameter(ParameterBoolean(self.LOAD_DISTANCE_FILES,
#                          'Load distance shapefiles in map canvas?',
#                          default=False))
#        self.addOutput(OutputDirectory(self.OUTPUT_DIR, 'output directory ' \
#                       'where the calculated files will be saved'))
#
#    def defineCharacteristics(self):
#        raise NotImplementedError
#
#    def helpFile(self):
#        return 'qrc:/plugins/conefor_dev/help.html'
#
#    def getCustomParametersDialog(self):
#        # maybe we can use directly the already made GUI...
#        return None
#
#    def checkBeforeOpeningParametersDialog(self):
#        # seems like a nice place to get the usable layers
#        return None
#
#    def processAlgorithm(self, progress):
#
#        # check for the usable layers
#        only_selected = SextanteConfig.getSetting('USE_SELECTED')
#        input_file_path = self.getParameterValue(self.INPUT_LAYER)
#        layer_uri = Sextante.getObject(input_file_path)
#        iface = Sextante.getInterface()
#        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
#        try:
#            the_algorithm = InputsProcessor(project_crs)
#            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
#                            self.update_progress)
#            QObject.connect(the_algorithm, SIGNAL('update_info'), 
#                            partial(self.update_info, progress))
#            the_algorithm.process_layer(
#                Sextante.getObject(input_file_path),
#                self.getParameterValue(self.UNIQUE_ATTRIBUTE),
#                self.getParameterValue(self.PROCESS_AREA),
#                self.getParameterValue(self.PROCESS_ATTRIBUTE),
#                self.getParameterValue(self.PROCESS_CENTROID),
#                self.getParameterValue(self.PROCESS_EDGE),
#                self.getOutputValue(self.OUTPUT_DIR),
#                100,
#                self.getParameterValue(self.DISTANCE_FILES),
#                only_selected,
#                self.getParameterValue(self.LOAD_DISTANCE_FILES)
#            )
#            SextanteResults.addResult('teste',
#                                      '/home/ricardo/Desktop/lixo.txt')
#        except Exception as e:
#            raise GeoAlgorithmExecutionException
#
#    def update_progress(self, progress_obj, value):
#        progress_obj.setProgress(value)
#
#    def update_info(self, progress_obj, info, section=0):
#        progress_obj.setInfo(info)
#
#
#class ConeforInputsPoints(ConeforInputsProcessor):
#
#    def defineCharacteristics(self):
#
#        self.name = 'Prepare point inputs for Conefor'
#        self.group = 'Prepare inputs'
#        self.addParameter(ParameterVector(self.INPUT_LAYER,
#                          'Input point layer', shapetype=0))
#        self._other_characteristics()
#
#
#class ConeforInputsPolygons(ConeforInputsProcessor):
#
#    def defineCharacteristics(self):
#
#        self.name = 'Prepare polygon inputs for Conefor'
#        self.group = 'Prepare inputs'
#        self.addParameter(ParameterVector(self.INPUT_LAYER,
#                          'Input point layer', shapetype=2))
#        self._other_characteristics()


class ConeforInputsBase(GeoAlgorithm):
    SHAPE_TYPE = None # reimplemented in child classes
    GROUP = None # reimplemented in child classes
    INPUT_LAYER = 'INPUT_LAYER'
    UNIQUE_ATTRIBUTE = 'UNIQUE_ATTRIBUTE'
    PROCESS_ATTRIBUTE = 'PROCESS_ATTRIBUTE'
    PROCESS_AREA = 'PROCESS_AREA'
    PROCESS_EDGE = 'PROCESS_EDGE'
    PROCESS_CENTROID = 'PROCESS_CENTROID'
    OUTPUT_ATTRIBUTE_FILE = 'OUTPUT_ATTRIBUTE_FILE'
    OUTPUT_AREA_FILE = 'OUTPUT_AREA_FILE'
    OUTPUT_CENTROID_FILE = 'OUTPUT_CENTROID_FILE'
    OUTPUT_EDGE_FILE = 'OUTPUT_EDGE_FILE'
    OUTPUT_CENTROID_SHAPE = 'OUTPUT_CENTROID_SHAPE'
    OUTPUT_EDGE_SHAPE = 'OUTPUT_EDGE_SHAPE'
    OUTPUT_DIR = 'OUTPUT_DIR'

    def getIcon(self):
        return QIcon(':/plugins/conefor_dev/icon.png')

    def helpFile(self):
        return 'qrc:/plugins/conefor_dev/help.html'

    def update_progress(self, progress_obj, value):
        progress_obj.setProgress(value)

    def update_info(self, progress_obj, info, section=0):
        progress_obj.setInfo(info)


class ConeforInputsAttribute(ConeforInputsBase):

    def defineCharacteristics(self):
        self.name = 'Prepare inputs - Attribute query [%s]' % self.GROUP
        self.group = self.GROUP
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addParameter(ParameterTableField(self.PROCESS_ATTRIBUTE,
                          'Attribute query field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputFile(self.OUTPUT_ATTRIBUTE_FILE, 'output file' \
                       'for saving attribute node query'))

    def processAlgorithm(self, progress):

        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        layer_uri = Sextante.getObject(input_file_path)
        iface = Sextante.getInterface()
        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
        try:
            the_algorithm = InputsProcessor(project_crs)
            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
                            self.update_progress)
            QObject.connect(the_algorithm, SIGNAL('update_info'), 
                            partial(self.update_info, progress))
            the_algorithm.process_layer(
                layer=Sextante.getObject(input_file_path),
                id_attribute=self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                area=False,
                attribute=self.getParameterValue(self.PROCESS_ATTRIBUTE),
                centroid=False,
                edge=False,
                output_dir=self.getOutputValue(self.OUTPUT_DIR),
                progress_step=100,
                centroid_distance_file_name=None,
                edge_distance_file_name=None,
                only_selected_features=only_selected,
                load_distance_files_to_canvas=False
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsArea(ConeforInputsBase):

    def defineCharacteristics(self):
        self.name = 'Prepare inputs - Area query [%s]' % self.GROUP
        self.group = self.GROUP
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputFile(self.OUTPUT_AREA_FILE, 'output file' \
                       'for saving area node query'))

    def processAlgorithm(self, progress):
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        layer_uri = Sextante.getObject(input_file_path)
        iface = Sextante.getInterface()
        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
        try:
            the_algorithm = InputsProcessor(project_crs)
            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
                            self.update_progress)
            QObject.connect(the_algorithm, SIGNAL('update_info'), 
                            partial(self.update_info, progress))
            the_algorithm.process_layer(
                layer=Sextante.getObject(input_file_path),
                id_attribute=self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                area=True,
                attribute=None,
                centroid=False,
                edge=False,
                output_dir=self.getOutputValue(self.OUTPUT_DIR),
                progress_step=100,
                centroid_distance_file_name=None,
                edge_distance_file_name=None,
                only_selected_features=only_selected,
                load_distance_files_to_canvas=False
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsCentroid(ConeforInputsBase):

    def defineCharacteristics(self):
        self.name = 'Prepare inputs - Centroid query [%s]' % self.GROUP
        self.group = self.GROUP
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputFile(self.OUTPUT_CENTROID_FILE, 'output file' \
                       'for saving centroid distance query'))

    def processAlgorithm(self, progress):
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        layer_uri = Sextante.getObject(input_file_path)
        iface = Sextante.getInterface()
        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
        try:
            the_algorithm = InputsProcessor(project_crs)
            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
                            self.update_progress)
            QObject.connect(the_algorithm, SIGNAL('update_info'), 
                            partial(self.update_info, progress))
            the_algorithm.process_layer(
                layer=Sextante.getObject(input_file_path),
                id_attribute=self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                area=False,
                attribute=None,
                centroid=True,
                edge=False,
                output_dir=self.getOutputValue(self.OUTPUT_DIR),
                progress_step=100,
                centroid_distance_file_name=None,
                edge_distance_file_name=None,
                only_selected_features=only_selected,
                load_distance_files_to_canvas=False
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsEdge(ConeforInputsBase):

    OUTPUT_EDGE_FILE = 'OUTPUT_EDGE_FILE'

    def defineCharacteristics(self):
        self.name = 'Prepare inputs - Edge query [%s]' % self.GROUP
        self.group = self.GROUP
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputFile(self.OUTPUT_EDGE_FILE, 'output file' \
                       'for saving edge distance query'))

    def processAlgorithm(self, progress):
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        layer_uri = Sextante.getObject(input_file_path)
        iface = Sextante.getInterface()
        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
        try:
            the_algorithm = InputsProcessor(project_crs)
            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
                            self.update_progress)
            QObject.connect(the_algorithm, SIGNAL('update_info'), 
                            partial(self.update_info, progress))
            the_algorithm.process_layer(
                layer=Sextante.getObject(input_file_path),
                id_attribute=self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                area=False,
                attribute=None,
                centroid=False,
                edge=True,
                output_dir=self.getOutputValue(self.OUTPUT_DIR),
                progress_step=100,
                centroid_distance_file_name=None,
                edge_distance_file_name=None,
                only_selected_features=only_selected,
                load_distance_files_to_canvas=False
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsCentroidDistance(ConeforInputsBase):

    def defineCharacteristics(self):
        self.name = 'Misc - Centroid distance vector [%s]' % self.GROUP
        self.group = self.GROUP
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputVector(self.OUTPUT_CENTROID_SHAPE, 'output ' \
                       'shapefile where the calculated distances will be ' \
                       'saved'))

    def processAlgorithm(self, progress):
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        dir_, name = os.path.split(self.getOutputValue(
                                   self.OUTPUT_CENTROID_SHAPE))
        layer_uri = Sextante.getObject(input_file_path)
        iface = Sextante.getInterface()
        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
        try:
            the_algorithm = InputsProcessor(project_crs)
            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
                            self.update_progress)
            QObject.connect(the_algorithm, SIGNAL('update_info'), 
                            partial(self.update_info, progress))
            the_algorithm.process_layer(
                layer=Sextante.getObject(input_file_path),
                id_attribute=self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                area=False,
                attribute=None,
                centroid=True,
                edge=False,
                output_dir=dir_,
                progress_step=100,
                centroid_distance_file_name=name,
                edge_distance_file_name=None,
                only_selected_features=only_selected,
                load_distance_files_to_canvas=False,
                save_text_files=False
            )
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsEdgeDistance(ConeforInputsBase):

    def defineCharacteristics(self):
        self.name = 'Misc - Edge distance vector [%s]' % self.GROUP
        self.group = self.GROUP
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputVector(self.OUTPUT_EDGE_SHAPE, 'output ' \
                       'shapefile where the calculated distances will be ' \
                       'saved'))

    def processAlgorithm(self, progress):
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        dir_, name = os.path.split(self.getOutputValue(self.OUTPUT_EDGE_SHAPE))
        layer_uri = Sextante.getObject(input_file_path)
        iface = Sextante.getInterface()
        project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
        try:
            the_algorithm = InputsProcessor(project_crs)
            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
                            self.update_progress)
            QObject.connect(the_algorithm, SIGNAL('update_info'), 
                            partial(self.update_info, progress))
            the_algorithm.process_layer(
                layer=Sextante.getObject(input_file_path),
                id_attribute=self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                area=False,
                attribute=None,
                centroid=False,
                edge=True,
                output_dir=dir_,
                progress_step=100,
                centroid_distance_file_name=None,
                edge_distance_file_name=name,
                only_selected_features=only_selected,
                load_distance_files_to_canvas=False,
                save_text_files=False
            )
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsPointAttribute(ConeforInputsAttribute):
    SHAPE_TYPE = 0
    GROUP = 'Points'

class ConeforInputsPolygonAttribute(ConeforInputsAttribute):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'

class ConeforInputsPointArea(ConeforInputsArea):
    SHAPE_TYPE = 0
    GROUP = 'Points'

class ConeforInputsPolygonArea(ConeforInputsArea):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'

class ConeforInputsPointCentroid(ConeforInputsCentroid):
    SHAPE_TYPE = 0
    GROUP = 'Points'

class ConeforInputsPolygonCentroid(ConeforInputsCentroid):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'

class ConeforInputsPointEdge(ConeforInputsEdge):
    SHAPE_TYPE = 0
    GROUP = 'Points'

class ConeforInputsPolygonEdge(ConeforInputsEdge):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'

class ConeforInputsPointCentroidDistance(ConeforInputsCentroidDistance):
    SHAPE_TYPE = 0
    GROUP = 'Points'

class ConeforInputsPolygonCentroidDistance(ConeforInputsCentroidDistance):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'

class ConeforInputsPointEdgeDistance(ConeforInputsEdgeDistance):
    SHAPE_TYPE = 0
    GROUP = 'Points'

class ConeforInputsPolygonEdgeDistance(ConeforInputsEdgeDistance):
    SHAPE_TYPE = 2
    GROUP = 'Polygons'
