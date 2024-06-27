import os
from functools import partial

import qgis.core
from qgis.PyQt import (
    QtCore,
    QtGui,
)

from qgis.utils import iface

from ...coneforinputsprocessor import InputsProcessor
from ...schemas import ICON_RESOURCE_PATH


class Base(qgis.core.QgsProcessingAlgorithm):

    def group(self):
        return None

    def groupId(self):
        return None

    def tr(self, string: str):
        return QtCore.QCoreApplication.translate("Processing", string)

    def icon(self):
        return QtGui.QIcon(ICON_RESOURCE_PATH)


class ConeforInputsBase(Base):
    INPUT_VECTOR_LAYER = "Vector layer"
    INPUT_UNIQUE_ATTRIBUTE_NAME = "Node identifier"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            qgis.core.QgsProcessingParameterFeatureSource(
                name=self.INPUT_VECTOR_LAYER,
                description=self.tr("Input layer"),
                types=[
                    qgis.core.QgsProcessing.TypeVectorPoint,
                    qgis.core.QgsProcessing.TypeVectorPolygon,
                ]
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterField(
                name=self.INPUT_UNIQUE_ATTRIBUTE_NAME,
                description=self.tr(
                    "Unique attribute that can be used to identify each feature"),
                parentLayerParameterName=self.INPUT_VECTOR_LAYER,
                type=qgis.core.QgsProcessingParameterField.Numeric,
            )
        )


class ConeforInputsAttribute(ConeforInputsBase):

    def name(self):
        return "attribute"

    def displayName(self):
        return self.tr("Generate inputs with an attribute query")

    def shortHelpString(self):
        return self.tr("Generates the Conefor input files")

    def createInstance(self):
        return ConeforInputsAttribute()

    def initAlgorithm(self, configuration=None):
        super().initAlgorithm()



# class ConeforInputsBase(GeoAlgorithm):
#
#     # to be reimplemented in child classes
#     NAME = None
#     SHAPE_TYPE = None
#     GROUP = None
#
#     INPUT_LAYER = 'INPUT_LAYER'
#     UNIQUE_ATTRIBUTE = 'UNIQUE_ATTRIBUTE'
#     PROCESS_ATTRIBUTE = 'PROCESS_ATTRIBUTE'
#     PROCESS_AREA = 'PROCESS_AREA'
#     PROCESS_EDGE = 'PROCESS_EDGE'
#     PROCESS_CENTROID = 'PROCESS_CENTROID'
#     OUTPUT_FILE = 'OUTPUT_FILE'
#
#     def defineCharacteristics(self):
#         self.name = self.NAME
#         self.group = self.GROUP
#         self.addParameter(ParameterVector(self.INPUT_LAYER,
#                           'Input layer', shapetype=self.SHAPE_TYPE))
#         self.addParameter(ParameterTableField(self.UNIQUE_ATTRIBUTE,
#                           'ID field:', self.INPUT_LAYER,
#                           datatype=0, optional=False))
#
#     def processAlgorithm(self, progress):
#         only_selected = ProcessingConfig.getSetting(
#             ProcessingConfig.USE_SELECTED)
#         input_file_path = self.getParameterValue(self.INPUT_LAYER)
#         layer = Processing.getObject(input_file_path)
#         unique_attribute = self.getParameterValue(self.UNIQUE_ATTRIBUTE)
#         project_crs = iface.mapCanvas().mapRenderer().destinationCrs()
#         try:
#             the_algorithm = InputsProcessor(project_crs)
#
#             QObject.connect(the_algorithm, SIGNAL('progress_changed'),
#                             partial(self.update_progress, progress,
#                             the_algorithm))
#
#             QObject.connect(the_algorithm, SIGNAL('update_info'),
#                             partial(self.update_info, progress))
#             self._run_the_algorithm(the_algorithm, only_selected, layer,
#                                     unique_attribute)
#         except Exception as e:
#             raise GeoAlgorithmExecutionException(e.message)
#
#     def getIcon(self):
#         return QIcon(':/plugins/qgisconefor/assets/icon.png')
#
#     def help(self):
#         return False, 'http://hub.qgis.org/projects/qgisconefor'
#
#     def update_progress(self, progress_obj, processor):
#         progress_obj.setPercentage(processor.global_progress)
#
#     def update_info(self, progress_obj, info, section=0):
#         progress_obj.setInfo(info)
#
#     def _run_the_algorithm(self, algorithm_processor, use_selected, layer,
#                            unique_attribute):
#         # to be reimplemented in child classes
#         raise NotImplementedError
#
#
# class ConeforInputsAttribute(ConeforInputsBase):
#
#     def defineCharacteristics(self):
#         Base.defineCharacteristics(self)
#         self.addParameter(ParameterTableField(self.PROCESS_ATTRIBUTE,
#                           'Attribute query field:', self.INPUT_LAYER,
#                           datatype=0, optional=False))
#         self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
#                        'attribute query file'))
#
#     def _run_the_algorithm(self, processor, use_selected, layer,
#                            unique_attribute):
#         out_path = self.getOutputValue(self.OUTPUT_FILE)
#         process_attribute = self.getParameterValue(self.PROCESS_ATTRIBUTE)
#         output_dir, attribute_file_name = os.path.split(out_path)
#         processor.process_layer(layer, unique_attribute, output_dir,
#                                 progress_step=100, attribute=process_attribute,
#                                 attribute_file_name=attribute_file_name,
#                                 only_selected_features=use_selected)
#
#
# class ConeforInputsArea(ConeforInputsBase):
#
#     def defineCharacteristics(self):
#         Base.defineCharacteristics(self)
#         self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
#                        'area query file'))
#
#     def _run_the_algorithm(self, processor, use_selected, layer,
#                            unique_attribute):
#         out_path = self.getOutputValue(self.OUTPUT_FILE)
#         output_dir, area_file_name = os.path.split(out_path)
#         print('aqui')
#         processor.process_layer(layer, unique_attribute, output_dir,
#                                 progress_step=100,
#                                 area_file_name=area_file_name,
#                                 only_selected_features=use_selected)
#
#
# class ConeforInputsCentroid(ConeforInputsBase):
#
#     def defineCharacteristics(self):
#         Base.defineCharacteristics(self)
#         self.addOutput(OutputFile(self.OUTPUT_FILE, 'output ' \
#                        'centroid query file'))
#
#     def _run_the_algorithm(self, processor, use_selected, layer,
#                            unique_attribute):
#         out_path = self.getOutputValue(self.OUTPUT_FILE)
#         output_dir, centroid_file_name = os.path.split(out_path)
#         processor.process_layer(layer, unique_attribute, output_dir,
#                                 progress_step=100,
#                                 centroid_file_name=centroid_file_name,
#                                 only_selected_features=use_selected)
#
#
# class ConeforInputsEdge(ConeforInputsBase):
#
#     def defineCharacteristics(self):
#         Base.defineCharacteristics(self)
#         self.addOutput(OutputFile(self.OUTPUT_FILE, 'output edge ' \
#                        'distances file'))
#
#     def _run_the_algorithm(self, processor, use_selected, layer,
#                            unique_attribute):
#
#         out_path = self.getOutputValue(self.OUTPUT_FILE)
#         output_dir, edge_file_name = os.path.split(out_path)
#         processor.process_layer(layer, unique_attribute, output_dir,
#                                 progress_step=100,
#                                 edge_file_name=edge_file_name,
#                                 only_selected_features=use_selected)
#
#
# class ConeforInputsCentroidDistance(ConeforInputsBase):
#
#     def defineCharacteristics(self):
#         Base.defineCharacteristics(self)
#         self.addOutput(OutputVector(self.OUTPUT_FILE, 'output ' \
#                        'shapefile where the calculated distances will be ' \
#                        'saved'))
#
#     def _run_the_algorithm(self, processor, use_selected, layer,
#                            unique_attribute):
#
#         out_path = self.getOutputValue(self.OUTPUT_FILE)
#         output_dir, shape_name = os.path.split(out_path)
#         processor.process_layer(layer, unique_attribute, output_dir,
#                                 progress_step=100,
#                                 centroid_distance_file_name=shape_name,
#                                 only_selected_features=use_selected)
#
#
# class ConeforInputsEdgeDistance(ConeforInputsBase):
#
#     def defineCharacteristics(self):
#         Base.defineCharacteristics(self)
#         self.addOutput(OutputVector(self.OUTPUT_FILE, 'output ' \
#                        'shapefile where the calculated distances will be ' \
#                        'saved'))
#
#     def _run_the_algorithm(self, processor, use_selected, layer,
#                            unique_attribute):
#
#         out_path = self.getOutputValue(self.OUTPUT_FILE)
#         output_dir, shape_name = os.path.split(out_path)
#         processor.process_layer(layer, unique_attribute, output_dir,
#                                 progress_step=100,
#                                 edge_distance_file_name=shape_name,
#                                 only_selected_features=use_selected)
#
#
# class ConeforInputsPointAttribute(ConeforInputsAttribute):
#     SHAPE_TYPE = 0
#     GROUP = 'Prepare point inputs'
#     NAME = 'Attribute query [%s]' % GROUP
#
# class ConeforInputsPolygonAttribute(ConeforInputsAttribute):
#     SHAPE_TYPE = 2
#     GROUP = 'Prepare polygon inputs'
#     NAME = 'Attribute query [%s]' % GROUP
#
# class ConeforInputsPolygonArea(ConeforInputsArea):
#     SHAPE_TYPE = 2
#     GROUP = 'Prepare polygon inputs'
#     NAME = 'Area query [%s]' % GROUP
#
# class ConeforInputsPointCentroid(ConeforInputsCentroid):
#     SHAPE_TYPE = 0
#     GROUP = 'Prepare point inputs'
#     NAME = 'Centroid query [%s]' % GROUP
#
# class ConeforInputsPolygonCentroid(ConeforInputsCentroid):
#     SHAPE_TYPE = 2
#     GROUP = 'Prepare polygon inputs'
#     NAME = 'Centroid query [%s]' % GROUP
#
# class ConeforInputsPointEdge(ConeforInputsEdge):
#     SHAPE_TYPE = 0
#     GROUP = 'Prepare point inputs'
#     NAME = 'Edge query [%s]' % GROUP
#
# class ConeforInputsPolygonEdge(ConeforInputsEdge):
#     SHAPE_TYPE = 2
#     GROUP = 'Prepare polygon inputs'
#     NAME = 'Edge query [%s]' % GROUP
#
# class ConeforInputsPointCentroidDistance(ConeforInputsCentroidDistance):
#     SHAPE_TYPE = 0
#     GROUP = 'Miscelaneous'
#     NAME = 'Point distance vector [%s]' % GROUP
#
# class ConeforInputsPolygonCentroidDistance(ConeforInputsCentroidDistance):
#     SHAPE_TYPE = 2
#     GROUP = 'Miscelaneous'
#     NAME = 'Centroid distance vector [%s]' % GROUP
#
# class ConeforInputsPolygonEdgeDistance(ConeforInputsEdgeDistance):
#     SHAPE_TYPE = 2
#     GROUP = 'Miscelaneous'
#     NAME = 'Edge distance vector [%s]' % GROUP
