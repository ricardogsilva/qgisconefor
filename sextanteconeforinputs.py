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
    INPUT_LAYER = 'INPUT_LAYER'
    UNIQUE_ATTRIBUTE = 'UNIQUE_ATTRIBUTE'
    PROCESS_ATTRIBUTE = 'PROCESS_ATTRIBUTE'
    PROCESS_AREA = 'PROCESS_AREA'
    PROCESS_EDGE = 'PROCESS_EDGE'
    PROCESS_CENTROID = 'PROCESS_CENTROID'
    OUTPUT_CENTROID = 'OUTPUT_CENTROID'
    OUTPUT_DIR = 'OUTPUT_DIR'

    def helpFile(self):
        return 'qrc:/plugins/conefor_dev/help.html'

    def update_progress(self, progress_obj, value):
        progress_obj.setProgress(value)

    def update_info(self, progress_obj, info, section=0):
        progress_obj.setInfo(info)


class ConeforInputsPoint(ConeforInputsBase):
    SHAPE_TYPE = 0


class ConeforInputsPolygon(ConeforInputsBase):
    SHAPE_TYPE = 2


class ConeforInputsProcessor(GeoAlgorithm):

    OUTPUT_DIR = 'OUTPUT_DIR'
    INPUT_LAYER = 'INPUT_LAYER'
    UNIQUE_ATTRIBUTE = 'UNIQUE_ATTRIBUTE'
    PROCESS_ATTRIBUTE = 'PROCESS_ATTRIBUTE'
    PROCESS_AREA = 'PROCESS_AREA'
    PROCESS_CENTROID = 'PROCESS_CENTROID'
    PROCESS_EDGE = 'PROCESS_EDGE'
    DISTANCE_FILES = 'DISTANCE_FILES'
    LOAD_DISTANCE_FILES = 'LOAD_DISTANCE_FILES'

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
        self.addParameter(ParameterBoolean(self.LOAD_DISTANCE_FILES,
                          'Load distance shapefiles in map canvas?',
                          default=False))
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
            QObject.connect(the_algorithm, SIGNAL('progress_changed'), 
                            self.update_progress)
            QObject.connect(the_algorithm, SIGNAL('update_info'), 
                            partial(self.update_info, progress))
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
                only_selected,
                self.getParameterValue(self.LOAD_DISTANCE_FILES)
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException

    def update_progress(self, progress_obj, value):
        progress_obj.setProgress(value)

    def update_info(self, progress_obj, info, section=0):
        progress_obj.setInfo(info)


class ConeforInputsPoints(ConeforInputsProcessor):

    def defineCharacteristics(self):

        self.name = 'Prepare point inputs for Conefor'
        self.group = 'Prepare inputs'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=0))
        self._other_characteristics()


class ConeforInputsPolygons(ConeforInputsProcessor):

    def defineCharacteristics(self):

        self.name = 'Prepare polygon inputs for Conefor'
        self.group = 'Prepare inputs'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=2))
        self._other_characteristics()


class ConeforInputsPolygonAttribute(ConeforInputsPolygon):

    def defineCharacteristics(self):
        self.name = 'Prepare inputs - Attribute query'
        self.group = 'Polygons'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=2))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addParameter(ParameterTableField(self.PROCESS_ATTRIBUTE,
                          'Attribute query field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputDirectory(self.OUTPUT_DIR, 'output directory ' \
                       'where the calculated files will be saved'))

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
                Sextante.getObject(input_file_path),
                self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                False,
                self.getParameterValue(self.PROCESS_ATTRIBUTE),
                False,
                False,
                self.getOutputValue(self.OUTPUT_DIR),
                100,
                False,
                only_selected,
                False
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsPolygonArea(ConeforInputsPolygon):

    def defineCharacteristics(self):
        self.name = 'Prepare inputs - Area query'
        self.group = 'Polygons'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=2))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputDirectory(self.OUTPUT_DIR, 'output directory ' \
                       'where the calculated files will be saved'))

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
                Sextante.getObject(input_file_path),
                self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                True,
                None,
                False,
                False,
                self.getOutputValue(self.OUTPUT_DIR),
                100,
                False,
                only_selected,
                False
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsPolygonCentroid(ConeforInputsPolygon):

    def defineCharacteristics(self):
        self.name = 'Prepare inputs - Centroid query'
        self.group = 'Polygons'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=2))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputDirectory(self.OUTPUT_DIR, 'output directory ' \
                       'where the calculated files will be saved'))

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
                Sextante.getObject(input_file_path),
                self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                False,
                None,
                True,
                False,
                self.getOutputValue(self.OUTPUT_DIR),
                100,
                False,
                only_selected,
                False
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException


class ConeforInputsPolygonEdge(ConeforInputsPolygon):

    OUTPUT_EDGE_FILE = 'OUTPUT_EDGE_FILE'

    def defineCharacteristics(self):
        self.name = 'Prepare inputs - Edge query'
        self.group = 'Polygons'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=2))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputDirectory(self.OUTPUT_DIR, 'output directory ' \
                       'where the calculated files will be saved'))
        self.addOutput(OutputFile(self.OUTPUT_EDGE_FILE, 'output edge ' \
                       'distances file'))

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
                Sextante.getObject(input_file_path),
                self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                False,
                None,
                False,
                True,
                self.getOutputValue(self.OUTPUT_DIR),
                100,
                None,
                None,
                only_selected,
            )
            SextanteResults.addResult('teste',
                                      '/home/ricardo/Desktop/lixo.txt')
        except Exception as e:
            raise GeoAlgorithmExecutionException

class ConeforInputsPolygonCentroidDistance(ConeforInputsPolygon):

    def defineCharacteristics(self):
        self.name = 'Misc - Centroid distance vector'
        self.group = 'Polygons'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputVector(self.OUTPUT_CENTROID, 'output ' \
                       'shapefile where the calculated distances will be ' \
                       'saved'))

    def processAlgorithm(self, progress):
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        dir_, name = os.path.split(self.getOutputValue(self.OUTPUT_CENTROID))
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
                Sextante.getObject(input_file_path),
                self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                False,
                None,
                True,
                False,
                dir_,
                100,
                name,
                None,
                only_selected,
                False,
                False
            )
        except Exception as e:
            raise GeoAlgorithmExecutionException

class ConeforInputsPolygonEdgeDistance(ConeforInputsPolygon):

    def defineCharacteristics(self):
        self.name = 'Misc - Edge distance vector'
        self.group = 'Polygons'
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                          'Input point layer', shapetype=self.SHAPE_TYPE))
        self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
                          'ID field:', self.INPUT_LAYER,
                          optional=False))
        self.addOutput(OutputVector(self.OUTPUT_CENTROID, 'output ' \
                       'shapefile where the calculated distances will be ' \
                       'saved'))

    def processAlgorithm(self, progress):
        only_selected = SextanteConfig.getSetting('USE_SELECTED')
        input_file_path = self.getParameterValue(self.INPUT_LAYER)
        dir_, name = os.path.split(self.getOutputValue(self.OUTPUT_CENTROID))
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
                Sextante.getObject(input_file_path),
                self.getParameterValue(self.UNIQUE_ATTRIBUTE),
                False,
                None,
                False,
                True,
                dir_,
                100,
                None,
                name,
                only_selected,
                False,
                False
            )
        except Exception as e:
            raise GeoAlgorithmExecutionException
