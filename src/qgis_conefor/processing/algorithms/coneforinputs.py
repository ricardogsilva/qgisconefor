from pathlib import Path
from typing import Optional

import qgis.core

from ... import coneforinputsprocessor
from ...schemas import (
    NodeConnectionType,
    QgisConeforSettingsKey,
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
        return self.tr("Prepare input files")

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
            end_progress=50,
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
            end_progress=50,
            info_callback=feedback.pushInfo,
        )

    def _generate_connection_file_by_centroid_distance(
        self,
        node_id_field: Optional[str],
        source: qgis.core.QgsProcessingFeatureSource,
        output_dir: Path,
        distance_threshold: Optional[int],
        feedback: qgis.core.QgsProcessingFeedback,
    ) -> Optional[Path]:
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
                start_progress=50,
                info_callback=feedback.pushInfo,
                cancelled_callback=feedback.isCanceled,
                distance_threshold=distance_threshold,
            )
        )


class ConeforInputsPoint(ConeforInputsBase):
    INPUT_POINT_LAYER = ("vector_layer", "Point layer",)

    def name(self):
        return "inputsfrompoint"

    def displayName(self):
        return "Generate input files from point layer"

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

        if source.featureCount() > 0:
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
            node_file_output_path = None
            connections_file_output_path = None
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
        return "Generate input files from polygon layer"

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
        feedback.pushInfo(f"{self.parameterAsEnum(parameters, self.INPUT_NODE_CONNECTION_DISTANCE_METHOD[0], context)=} ")
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

        if source.featureCount() > 0:
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
            node_file_output_path = None
            connections_file_output_path = None
            feedback.pushInfo("The selected source has no features to process")
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
    ) -> Optional[Path]:
        return (
            coneforinputsprocessor.generate_connection_file_with_edge_distances(
                node_id_field_name=node_id_field,
                crs=source.sourceCrs(),
                feature_iterator_factory=source.getFeatures,
                num_features=source.featureCount(),
                output_path=output_dir / f"connections_edge-distance_{source.sourceName()}.txt",
                progress_callback=feedback.setProgress,
                start_progress=50,
                info_callback=feedback.pushInfo,
                cancelled_callback=feedback.isCanceled,
                distance_threshold=distance_threshold
            )
        )
