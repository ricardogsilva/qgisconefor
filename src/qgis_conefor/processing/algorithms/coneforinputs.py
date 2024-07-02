import os
import functools
from pathlib import Path
from typing import Optional

import qgis.core
from qgis.PyQt import (
    QtCore,
    QtGui,
)

from qgis.utils import iface

from ... import coneforinputsprocessor
from ...coneforinputsprocessor import InputsProcessor
from ...schemas import (
    AUTOGENERATE_NODE_ID_LABEL,
    ICON_RESOURCE_PATH,
    NodeConnectionType,
    QgisConeforSettingsKey,
    ConeforInputParameters,
)
from ...utilities import load_settings_key
from . import base


class ConeforInputsBase(base.Base):
    INPUT_NODE_IDENTIFIER_NAME = (
        "node_identifier", "Node identifier (will autogenerate if not set)")
    INPUT_NODE_ATTRIBUTE_NAME = ("node_attribute", "Node attribute (will calculate area if not set)")
    INPUT_DISTANCE_THRESHOLD = ("distance_threshold", "Distance threshold")
    INPUT_OUTPUT_DIRECTORY = ("output_dir", "Output directory for generated Conefor input files")
    OUTPUT_CONEFOR_NODES_FILE_PATH = ("output_path", "Conefor nodes file")
    OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH = ("output_connections_path", "Conefor connections file")

    def group(self):
        return self.tr("Prepare inputs for Conefor")

    def groupId(self):
        return "coneforinputs"

    def _generate_node_file_by_attribute(
        self,
        node_id_field: Optional[str],
        node_attribute_field: str,
        source: qgis.core.QgsProcessingFeatureSource,
        output_dir: Path,
        feedback: qgis.core.QgsProcessingFeedback,
    ) -> Path:
        return coneforinputsprocessor.generate_node_file_by_attribute(
            node_id_field_name=node_id_field,
            node_attribute_field_name=node_attribute_field,
            feature_iterator_factory=source.getFeatures,
            num_features=source.featureCount(),
            output_path=(
                    output_dir / f"nodes_{node_attribute_field}_{source.sourceName()}.txt"
            ),
            progress_callback=feedback.setProgress,
            info_callback=feedback.pushInfo,
        )

    def _generate_node_file_by_area(
        self,
        node_id_field: Optional[str],
        source: qgis.core.QgsProcessingFeatureSource,
        output_dir: Path,
        feedback: qgis.core.QgsProcessingFeedback,
    ) -> Path:
        return coneforinputsprocessor.generate_node_file_by_area(
            node_id_field_name=node_id_field,
            crs=source.sourceCrs(),
            feature_iterator_factory=source.getFeatures,
            num_features=source.featureCount(),
            output_path=(
                    output_dir / f"nodes_calculated-area_{source.sourceName()}.txt"),
            progress_callback=feedback.setProgress,
            info_callback=feedback.pushInfo,
        )

    def _generate_connection_file_by_centroid_distance(
        self,
        node_id_field: Optional[str],
        source: qgis.core.QgsProcessingFeatureSource,
        output_dir: Path,
        distance_threshold: Optional[int],
        feedback: qgis.core.QgsProcessingFeedback,
    ):
        return (
            coneforinputsprocessor.generate_connection_file_with_centroid_distances(
                node_id_field_name=node_id_field,
                crs=source.sourceCrs(),
                feature_iterator_factory=source.getFeatures,
                num_features=source.featureCount(),
                output_path=(
                        output_dir / f"connections_centroid-distance_{source.sourceName()}.txt"
                ),
                progress_callback=feedback.setProgress,
                info_callback=feedback.pushInfo,
                distance_threshold=distance_threshold,
            )
        )


class ConeforInputsPoint(ConeforInputsBase):
    INPUT_POINT_LAYER = ("vector_layer", "Point layer",)

    def name(self):
        return "inputsfrompoint"

    def displayName(self):
        return "Generate Conefor inputs from point layer"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            qgis.core.QgsProcessingParameterFeatureSource(
                name=self.INPUT_POINT_LAYER[0],
                description=self.tr(self.INPUT_POINT_LAYER[1]),
                types=[
                    qgis.core.QgsProcessing.TypeVectorPoint,
                ]
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterField(
                name=self.INPUT_NODE_IDENTIFIER_NAME[0],
                description=self.tr(self.INPUT_NODE_IDENTIFIER_NAME[1]),
                parentLayerParameterName=self.INPUT_POINT_LAYER[0],
                type=qgis.core.QgsProcessingParameterField.Numeric,
                optional=True,
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterField(
                name=self.INPUT_NODE_ATTRIBUTE_NAME[0],
                description=self.tr(self.INPUT_NODE_ATTRIBUTE_NAME[1]),
                parentLayerParameterName=self.INPUT_POINT_LAYER[0],
                type=qgis.core.QgsProcessingParameterField.Numeric,
                optional=True,
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterNumber(
                name=self.INPUT_DISTANCE_THRESHOLD[0],
                description=self.tr(self.INPUT_DISTANCE_THRESHOLD[1]),
                type=qgis.core.QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterFolderDestination(
                name=self.INPUT_OUTPUT_DIRECTORY[0],
                description=self.tr(self.INPUT_OUTPUT_DIRECTORY[1]),
                defaultValue=load_settings_key(
                    QgisConeforSettingsKey.OUTPUT_DIR, default_to=str(Path.home()))
            )
        )
        self.addOutput(
            qgis.core.QgsProcessingOutputFile(
                name=self.OUTPUT_CONEFOR_NODES_FILE_PATH[0],
                description=self.OUTPUT_CONEFOR_NODES_FILE_PATH[1],
            )
        )
        self.addOutput(
            qgis.core.QgsProcessingOutputFile(
                name=self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[0],
                description=self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[1],
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(
            parameters,
            self.INPUT_POINT_LAYER[0],
            context
        )
        raw_node_id_field_name = (
            self.parameterAsString(
                parameters, self.INPUT_NODE_IDENTIFIER_NAME[0], context)
        )
        if raw_node_id_field_name == "":
            node_id_field_name = None
        else:
            node_id_field_name = raw_node_id_field_name
        raw_distance_threshold = self.parameterAsString(
            parameters, self.INPUT_DISTANCE_THRESHOLD[0], context)
        if raw_distance_threshold == "":
            connections_distance_threshold = None
        else:
            connections_distance_threshold = int(raw_distance_threshold)
        output_dir = Path(
            self.parameterAsFile(
                parameters,
                self.INPUT_OUTPUT_DIRECTORY[0],
                context
            )
        )
        node_attribute_field_names = self.parameterAsFields(
            parameters,
            self.INPUT_NODE_ATTRIBUTE_NAME[0],
            context
        )

        feedback.pushInfo(f"{source=}")
        feedback.pushInfo(f"{node_id_field_name=}")
        feedback.pushInfo(f"{connections_distance_threshold=}")
        feedback.pushInfo(f"{output_dir=}")

        try:
            if len(node_attribute_field_names) == 0:  # use area as the attribute
                node_file_output_path = self._generate_node_file_by_area(
                    node_id_field_name, source, output_dir, feedback)
            else:
                feedback.pushInfo(f"{node_attribute_field_names[0]=}")
                node_file_output_path = (
                    self._generate_node_file_by_attribute(
                        node_id_field_name, node_attribute_field_names[0], source,
                        output_dir, feedback,
                    )
                )
            connections_file_output_path = self._generate_connection_file_by_centroid_distance(
                node_id_field_name, source, output_dir, connections_distance_threshold, feedback)
        except Exception as err:
            raise qgis.core.QgsProcessingException(str(err))
        else:
            return {
                self.OUTPUT_CONEFOR_NODES_FILE_PATH[0]: node_file_output_path,
                self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[0]: connections_file_output_path
            }


class ConeforInputsPolygon(ConeforInputsBase):
    INPUT_POLYGON_LAYER = ("vector_layer", "Polygon layer",)
    # INPUT_NODE_IDENTIFIER_NAME = (
    #     "node_identifier", "Node identifier (will autogenerate if not set)")
    # INPUT_NODE_ATTRIBUTE_NAME = ("node_attribute", "Node attribute (will calculate area if not set)")
    INPUT_NODE_CONNECTION_DISTANCE_METHOD = ("node_connection", "Node connection distance method")
    # INPUT_DISTANCE_THRESHOLD = ("distance_threshold", "Distance threshold")
    # INPUT_OUTPUT_DIRECTORY = ("output_dir", "Output directory for generated Conefor input files")
    # OUTPUT_CONEFOR_NODES_FILE_PATH = ("output_path", "Conefor nodes file")
    # OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH = ("output_connections_path", "Conefor connections file")
    _NODE_DISTANCE_CHOICES = [
        NodeConnectionType.EDGE_DISTANCE.value,
        NodeConnectionType.CENTROID_DISTANCE.value,
    ]

    def name(self):
        return "inputsfrompolygon"

    def displayName(self):
        return "Generate Conefor inputs from polygon layer"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            qgis.core.QgsProcessingParameterFeatureSource(
                name=self.INPUT_POLYGON_LAYER[0],
                description=self.tr(self.INPUT_POLYGON_LAYER[1]),
                types=[
                    qgis.core.QgsProcessing.TypeVectorPolygon,
                ]
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterField(
                name=self.INPUT_NODE_IDENTIFIER_NAME[0],
                description=self.tr(self.INPUT_NODE_IDENTIFIER_NAME[1]),
                parentLayerParameterName=self.INPUT_POLYGON_LAYER[0],
                type=qgis.core.QgsProcessingParameterField.Numeric,
                optional=True,
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterField(
                name=self.INPUT_NODE_ATTRIBUTE_NAME[0],
                description=self.tr(self.INPUT_NODE_ATTRIBUTE_NAME[1]),
                parentLayerParameterName=self.INPUT_POLYGON_LAYER[0],
                type=qgis.core.QgsProcessingParameterField.Numeric,
                optional=True,
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterEnum(
                name=self.INPUT_NODE_CONNECTION_DISTANCE_METHOD[0],
                description=self.tr(
                    self.INPUT_NODE_CONNECTION_DISTANCE_METHOD[1]),
                options=self._NODE_DISTANCE_CHOICES,
                defaultValue=NodeConnectionType.EDGE_DISTANCE.value
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterNumber(
                name=self.INPUT_DISTANCE_THRESHOLD[0],
                description=self.tr(self.INPUT_DISTANCE_THRESHOLD[1]),
                type=qgis.core.QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterFolderDestination(
                name=self.INPUT_OUTPUT_DIRECTORY[0],
                description=self.tr(self.INPUT_OUTPUT_DIRECTORY[1]),
                defaultValue=load_settings_key(
                    QgisConeforSettingsKey.OUTPUT_DIR, default_to=str(Path.home()))
            )
        )
        self.addOutput(
            qgis.core.QgsProcessingOutputFile(
                name=self.OUTPUT_CONEFOR_NODES_FILE_PATH[0],
                description=self.OUTPUT_CONEFOR_NODES_FILE_PATH[1],
            )
        )
        self.addOutput(
            qgis.core.QgsProcessingOutputFile(
                name=self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[0],
                description=self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[1],
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(
            parameters,
            self.INPUT_POLYGON_LAYER[0],
            context
        )
        raw_node_id_field_name = (
            self.parameterAsString(
                parameters, self.INPUT_NODE_IDENTIFIER_NAME[0], context)
        )
        if raw_node_id_field_name == "":
            node_id_field_name = None
        else:
            node_id_field_name = raw_node_id_field_name
        connections_distance_method = NodeConnectionType(
            self._NODE_DISTANCE_CHOICES[
                self.parameterAsEnum(
                    parameters, self.INPUT_NODE_CONNECTION_DISTANCE_METHOD[0], context
                )
            ]
        )
        raw_distance_threshold = self.parameterAsString(
            parameters, self.INPUT_DISTANCE_THRESHOLD[0], context)
        if raw_distance_threshold == "":
            connections_distance_threshold = None
        else:
            connections_distance_threshold = int(raw_distance_threshold)
        output_dir = Path(
            self.parameterAsFile(
                parameters,
                self.INPUT_OUTPUT_DIRECTORY[0],
                context
            )
        )
        node_attribute_field_names = self.parameterAsFields(
            parameters,
            self.INPUT_NODE_ATTRIBUTE_NAME[0],
            context
        )

        feedback.pushInfo(f"{source=}")
        feedback.pushInfo(f"{node_id_field_name=}")
        feedback.pushInfo(f"{connections_distance_method=}")
        feedback.pushInfo(f"{connections_distance_threshold=}")
        feedback.pushInfo(f"{output_dir=}")

        try:
            if len(node_attribute_field_names) == 0:  # use area as the attribute
                node_file_output_path = self._generate_node_file_by_area(
                    node_id_field_name, source, output_dir, feedback)
            else:
                feedback.pushInfo(f"{node_attribute_field_names[0]=}")
                node_file_output_path = (
                    self._generate_node_file_by_attribute(
                        node_id_field_name, node_attribute_field_names[0], source,
                        output_dir, feedback,
                    )
                )
            if connections_distance_method == NodeConnectionType.EDGE_DISTANCE:
                connections_file_output_path = self._generate_connection_file_by_edge_distance(
                    node_id_field_name, source, output_dir, connections_distance_threshold, feedback)
            elif connections_distance_method == NodeConnectionType.CENTROID_DISTANCE:
                connections_file_output_path = self._generate_connection_file_by_centroid_distance(
                    node_id_field_name, source, output_dir, connections_distance_threshold, feedback)
            else:
                raise NotImplementedError
        except Exception as err:
            raise qgis.core.QgsProcessingException(str(err))
        else:
            return {
                self.OUTPUT_CONEFOR_NODES_FILE_PATH[0]: node_file_output_path,
                self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[0]: connections_file_output_path
            }

    def _generate_connection_file_by_edge_distance(
        self,
        node_id_field: Optional[str],
        source: qgis.core.QgsProcessingFeatureSource,
        output_dir: Path,
        distance_threshold: Optional[int],
        feedback: qgis.core.QgsProcessingFeedback,
    ):
        return (
            coneforinputsprocessor.generate_connection_file_with_edge_distances(
                node_id_field_name=node_id_field,
                crs=source.sourceCrs(),
                feature_iterator_factory=source.getFeatures,
                num_features=source.featureCount(),
                output_path=output_dir / f"connections_edge-distance_{source.sourceName()}.txt",
                progress_callback=feedback.setProgress,
                info_callback=feedback.pushInfo,
                distance_threshold=distance_threshold
            )
        )

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
