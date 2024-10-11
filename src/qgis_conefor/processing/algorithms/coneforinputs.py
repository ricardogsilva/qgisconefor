from pathlib import Path
from typing import Optional

import qgis.core
from qgis import processing

from ... import coneforinputsprocessor
from ...schemas import (
    NodeConnectionType,
    QgisConeforSettingsKey,
)
from ...utilities import load_settings_key
from . import base


class ConeforInputsBase(base.Base):
    _autogenerated_node_id_field_name = "conefor_node_id"
    _autogenerated_node_attribute_field_name = "conefor_node_attribute (area)"

    INPUT_NODE_IDENTIFIER_NAME = (
        "node_identifier", "Node identifier (will autogenerate if not set)")
    INPUT_NODE_ATTRIBUTE_NAME = ("node_attribute", "Node attribute (will calculate area if not set)")
    INPUT_NODES_TO_ADD_ATTRIBUTE_NAME = (
        "nodes_to_add_attribute",
        "Which attribute to use for the 'nodes to add' Conefor feature"
    )
    INPUT_DISTANCE_THRESHOLD = ("distance_threshold", "Distance threshold")
    INPUT_OUTPUT_DIRECTORY = ("output_dir", "Output directory for generated Conefor input files")
    OUTPUT_CONEFOR_NODES_FILE_PATH = ("output_path", "Conefor nodes file")
    OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH = ("output_connections_path", "Conefor connections file")
    OUTPUT_GENERATED_CONEFOR_LAYER = ("output_generated_layer", "Layer with Conefor-generated attributes")

    def group(self):
        return self.tr("Prepare input files")

    def groupId(self):
        return "coneforinputs"

    def _validate_node_attributes(
            self,
            source: qgis.core.QgsProcessingFeatureSource,
            node_id_field: Optional[str],
            nodes_to_add_field: Optional[str],
            node_attribute_field: Optional[str] = None,
    ):
        if node_id_field is not None:
            node_id_source_field = [
                f for f in source.fields() if f.name() == node_id_field][0]
            node_id_field_is_valid = (
                coneforinputsprocessor.validate_node_identifier_attribute(
                    source, node_id_source_field
                )
            )
            if not node_id_field_is_valid:
                raise qgis.core.QgsProcessingException(
                    f"Node id field is not valid - if set, the node id field must be "
                    f"an integer column with unique values"
                )
        if node_attribute_field is not None:
            node_attribute_source_field = [
                f for f in source.fields() if f.name() == node_attribute_field][0]
            node_attribute_field_is_valid = coneforinputsprocessor.validate_node_attribute(
                source, node_attribute_source_field)
            if not node_attribute_field_is_valid:
                raise qgis.core.QgsProcessingException(
                    f"Node attribute field is not valid - the node attribute field "
                    f"must be a numeric column"
                )
        if nodes_to_add_field is not None:
            nodes_to_add_source_field = [
                f for f in source.fields() if f.name() == nodes_to_add_field][0]
            nodes_to_add_field_is_valid = (
                coneforinputsprocessor.validate_node_to_add_attribute(
                    source,
                    nodes_to_add_source_field
                )
            )
            if not nodes_to_add_field_is_valid:
                raise qgis.core.QgsProcessingException(
                    f"Nodes to add attribute field is not valid - if set, the "
                    f"'nodes to add' attribute must be a column that has only 0 or 1 "
                    f"values."
                )

    def _generate_node_file_by_attribute(
        self,
        node_id_field: str,
        node_attribute_field: str,
        nodes_to_add_field: Optional[str],
        source: qgis.core.QgsProcessingFeatureSource,
        output_dir: Path,
        feedback: qgis.core.QgsProcessingFeedback,
        start_progress: int,
        progress_step: float,
    ) -> Path:
        return coneforinputsprocessor.generate_node_file_by_attribute(
            node_id_field_name=node_id_field,
            node_attribute_field_name=node_attribute_field,
            nodes_to_add_field_name=nodes_to_add_field,
            feature_iterator_factory=source.getFeatures,
            output_path=(
                    output_dir / f"nodes_{node_attribute_field}_{source.sourceName()}.txt"
            ),
            progress_callback=feedback.setProgress,
            start_progress=start_progress,
            progress_step=progress_step,
            info_callback=feedback.pushInfo,
        )

    def _generate_connection_file_by_centroid_distance(
        self,
        node_id_field: str,
        source: qgis.core.QgsProcessingFeatureSource,
        output_dir: Path,
        distance_threshold: Optional[int],
        feedback: qgis.core.QgsProcessingFeedback,
        progress_step: float,
        start_progress: int = 0,
    ) -> Optional[Path]:
        return (
            coneforinputsprocessor.generate_connection_file_with_centroid_distances(
                node_id_field_name=node_id_field,
                crs=source.sourceCrs(),
                feature_iterator_factory=source.getFeatures,
                num_features=source.featureCount(),
                output_path=(
                        output_dir / f"distances_centroids_{source.sourceName()}.txt"
                ),
                progress_callback=feedback.setProgress,
                start_progress=start_progress,
                progress_step=progress_step,
                info_callback=feedback.pushInfo,
                cancelled_callback=feedback.isCanceled,
                distance_threshold=distance_threshold,
            )
        )


class ConeforInputsPoint(ConeforInputsBase):
    INPUT_POINT_LAYER = ("vector_layer", "Point layer",)
    INPUT_NODE_ATTRIBUTE_NAME = ("node_attribute", "Node attribute")

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
                optional=False,
            )
        )
        self.addParameter(
            qgis.core.QgsProcessingParameterField(
                name=self.INPUT_NODES_TO_ADD_ATTRIBUTE_NAME[0],
                description=self.tr(self.INPUT_NODES_TO_ADD_ATTRIBUTE_NAME[1]),
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
        node_attribute_field_name = self.parameterAsFields(
            parameters,
            self.INPUT_NODE_ATTRIBUTE_NAME[0],
            context
        )[0]
        raw_nodes_to_add_field_name = self.parameterAsString(
            parameters, self.INPUT_NODES_TO_ADD_ATTRIBUTE_NAME[0], context
        )
        if raw_nodes_to_add_field_name == "":
            nodes_to_add_field_name = None
        else:
            nodes_to_add_field_name = raw_nodes_to_add_field_name

        feedback.pushInfo(f"{source=}")
        feedback.pushInfo(f"{node_id_field_name=}")
        feedback.pushInfo(f"{node_attribute_field_name=}")
        feedback.pushInfo(f"{nodes_to_add_field_name=}")
        feedback.pushInfo(f"{connections_distance_threshold=}")
        feedback.pushInfo(f"{output_dir=}")

        result = {
            self.OUTPUT_CONEFOR_NODES_FILE_PATH[0]: None,
            self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[0]: None,
            self.OUTPUT_GENERATED_CONEFOR_LAYER[0]: None,
        }

        if source.featureCount() > 0:
            if node_id_field_name is None:  # will be generating a new layer
                feedback.pushInfo(
                    "No node identifier specified - adding a new field to a copy of "
                    "the layer"
                )
                final_layer_path = self._generate_layer_with_node_id(
                    parameters, feedback, context)
                layer_with_node_id = qgis.core.QgsProcessingUtils.mapLayerFromString(
                    final_layer_path, context)
                source = qgis.core.QgsProcessingFeatureSource(
                    layer_with_node_id,
                    context,
                    ownsOriginalSource=False,
                )
                node_id_field_name = self._autogenerated_node_id_field_name

                result[self.OUTPUT_GENERATED_CONEFOR_LAYER[0]] = final_layer_path
                relevant_details = context.layerToLoadOnCompletionDetails(final_layer_path)
                relevant_details.name = f"{source.sourceName()}_conefor_generated"
                context.setLayersToLoadOnCompletion({final_layer_path: relevant_details})

            self._validate_node_attributes(
                source,
                node_id_field=node_id_field_name,
                nodes_to_add_field=nodes_to_add_field_name,
                node_attribute_field=node_attribute_field_name,
            )

            num_features_to_process = source.featureCount()
            node_file_lines = num_features_to_process
            connection_file_lines = num_features_to_process * (num_features_to_process - 1) // 2
            remaining_progress = 100
            progress_step = remaining_progress / (node_file_lines + connection_file_lines)
            node_file_progress_portion = progress_step * node_file_lines

            node_file_output_path = (
                self._generate_node_file_by_attribute(
                    node_id_field_name,
                    node_attribute_field_name,
                    nodes_to_add_field_name,
                    source,
                    output_dir,
                    feedback,
                    start_progress=remaining_progress,
                    progress_step=progress_step,
                )
            )
            remaining_progress -= node_file_progress_portion
            result[self.OUTPUT_CONEFOR_NODES_FILE_PATH[0]] = node_file_output_path
            connections_file_output_path = self._generate_connection_file_by_centroid_distance(
                node_id_field_name,
                source,
                output_dir,
                connections_distance_threshold,
                feedback,
                start_progress=(100 - remaining_progress),
                progress_step=progress_step,
            )
            result[self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[0]] = connections_file_output_path
        else:
            feedback.pushInfo("The selected source has no features to process")
        feedback.setProgress(100)
        return result

    def _generate_layer_with_node_id(
            self,
            parameters,
            feedback,
            context
    ):
        # check docs on this processing algorithm here:
        # https://docs.qgis.org/testing/en/docs/user_manual/processing_algs/qgis/vectortable.html#qgisaddautoincrementalfield
        layer_with_node_id = processing.run(
            "native:addautoincrementalfield",
            {
                "INPUT": parameters[self.INPUT_POINT_LAYER[0]],
                "FIELD_NAME": self._autogenerated_node_id_field_name,
                "START": 1,
                "OUTPUT": qgis.core.QgsProcessingOutputLayerDefinition(
                    "memory:",
                    qgis.core.QgsProject.instance()
                )
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )["OUTPUT"]
        return layer_with_node_id


class ConeforInputsPolygon(ConeforInputsBase):
    INPUT_POLYGON_LAYER = ("vector_layer", "Polygon layer",)
    INPUT_NODE_CONNECTION_DISTANCE_METHOD = ("node_connection", "Node connection distance method")
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
            qgis.core.QgsProcessingParameterField(
                name=self.INPUT_NODES_TO_ADD_ATTRIBUTE_NAME[0],
                description=self.tr(self.INPUT_NODES_TO_ADD_ATTRIBUTE_NAME[1]),
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
        self.addOutput(
            qgis.core.QgsProcessingOutputVectorLayer(
                name=self.OUTPUT_GENERATED_CONEFOR_LAYER[0],
                description=self.OUTPUT_GENERATED_CONEFOR_LAYER[1],
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
        feedback.pushInfo(f"{connections_distance_method.value=} ")
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
        node_attribute_field_name = (
            node_attribute_field_names[0]
            if len(node_attribute_field_names) > 0 else None
        )
        raw_nodes_to_add_field_name = self.parameterAsString(
            parameters, self.INPUT_NODES_TO_ADD_ATTRIBUTE_NAME[0], context
        )
        if raw_nodes_to_add_field_name == "":
            nodes_to_add_field_name = None
        else:
            nodes_to_add_field_name = raw_nodes_to_add_field_name

        feedback.pushInfo(f"{source=}")
        feedback.pushInfo(f"{node_id_field_name=}")
        feedback.pushInfo(f"{nodes_to_add_field_name=}")
        feedback.pushInfo(f"{connections_distance_method=}")
        feedback.pushInfo(f"{connections_distance_threshold=}")
        feedback.pushInfo(f"{output_dir=}")

        result = {
            self.OUTPUT_CONEFOR_NODES_FILE_PATH[0]: None,
            self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[0]: None,
            self.OUTPUT_GENERATED_CONEFOR_LAYER[0]: None,
        }
        if source.featureCount() > 0:
            if not all((node_id_field_name, node_attribute_field_name)):  # will be generating a new layer
                final_layer_path = None
                if node_id_field_name is None:
                    feedback.pushInfo(
                        "No node identifier specified - adding a new field to a copy of "
                        "the layer"
                    )
                    final_layer_path = self._generate_layer_with_node_id(
                        parameters, feedback, context)
                    layer_with_node_id = qgis.core.QgsProcessingUtils.mapLayerFromString(
                        final_layer_path, context)
                    source = qgis.core.QgsProcessingFeatureSource(
                        layer_with_node_id,
                        context,
                        ownsOriginalSource=False,
                    )
                    node_id_field_name = self._autogenerated_node_id_field_name

                if node_attribute_field_name is None:  # being asked to use the area as the attribute
                    feedback.pushInfo(
                        "Using features' area as the node attribute - adding to a "
                        "copy of the layer"
                    )
                    final_layer_path = self._generate_layer_with_area_as_node_attribute(
                        source, feedback, context)
                    node_attribute_field_name = self._autogenerated_node_attribute_field_name
                    layer_with_node_id_and_area = qgis.core.QgsProcessingUtils.mapLayerFromString(
                        final_layer_path, context)
                    source = qgis.core.QgsProcessingFeatureSource(
                        layer_with_node_id_and_area,
                        context,
                        ownsOriginalSource=False,
                    )
                result[self.OUTPUT_GENERATED_CONEFOR_LAYER[0]] = final_layer_path
                # we do not want QGIS to try to automatically load the intermediate
                # layers, which will happen when calling this algorithm from the
                # Processing toolbox - as such, we tell the context to only load the
                # final layer
                relevant_details = context.layerToLoadOnCompletionDetails(final_layer_path)
                relevant_details.name = f"{source.sourceName()}_conefor_generated"
                context.setLayersToLoadOnCompletion({final_layer_path: relevant_details})


            self._validate_node_attributes(
                source,
                node_id_field=node_id_field_name,
                nodes_to_add_field=nodes_to_add_field_name,
                node_attribute_field=node_attribute_field_name,
            )
            num_features_to_process = source.featureCount()
            node_file_lines = num_features_to_process
            connection_file_lines = num_features_to_process * (num_features_to_process - 1) // 2
            remaining_progress = 100
            progress_step = remaining_progress / (node_file_lines + connection_file_lines)
            node_file_progress_portion = progress_step * node_file_lines
            node_file_output_path = (
                self._generate_node_file_by_attribute(
                    node_id_field_name,
                    node_attribute_field_name,
                    nodes_to_add_field_name,
                    source,
                    output_dir,
                    feedback,
                    start_progress=remaining_progress,
                    progress_step=progress_step,
                )
            )
            remaining_progress -= node_file_progress_portion
            result[self.OUTPUT_CONEFOR_NODES_FILE_PATH[0]] = node_file_output_path
            if connections_distance_method == NodeConnectionType.EDGE_DISTANCE:
                connections_file_output_path = self._generate_connection_file_by_edge_distance(
                    node_id_field_name,
                    source,
                    output_dir,
                    connections_distance_threshold,
                    feedback,
                    start_progress=(100 - remaining_progress),
                    progress_step=progress_step,
                )
            elif connections_distance_method == NodeConnectionType.CENTROID_DISTANCE:
                connections_file_output_path = self._generate_connection_file_by_centroid_distance(
                    node_id_field_name,
                    source,
                    output_dir,
                    connections_distance_threshold,
                    feedback,
                    start_progress=(100 - remaining_progress),
                    progress_step=progress_step,
                )
            else:
                raise NotImplementedError
            result[self.OUTPUT_CONEFOR_CONNECTIONS_FILE_PATH[0]] = connections_file_output_path
        else:
            feedback.pushInfo("The selected source has no features to process")
        feedback.setProgress(100)
        return result

    def _generate_connection_file_by_edge_distance(
        self,
        node_id_field: Optional[str],
        source: qgis.core.QgsProcessingFeatureSource,
        output_dir: Path,
        distance_threshold: Optional[int],
        feedback: qgis.core.QgsProcessingFeedback,
        start_progress: float,
        progress_step: float,
    ) -> Optional[Path]:
        return (
            coneforinputsprocessor.generate_connection_file_with_edge_distances(
                node_id_field_name=node_id_field,
                crs=source.sourceCrs(),
                feature_iterator_factory=source.getFeatures,
                num_features=source.featureCount(),
                output_path=output_dir / f"distances_edges_{source.sourceName()}.txt",
                progress_callback=feedback.setProgress,
                start_progress=int(start_progress),
                progress_step=progress_step,
                info_callback=feedback.pushInfo,
                cancelled_callback=feedback.isCanceled,
                distance_threshold=distance_threshold
            )
        )

    def _generate_layer_with_node_id(
            self,
            parameters,
            feedback,
            context
    ):
        # check docs on this processing algorithm here:
        # https://docs.qgis.org/testing/en/docs/user_manual/processing_algs/qgis/vectortable.html#qgisaddautoincrementalfield
        layer_with_node_id = processing.run(
            "native:addautoincrementalfield",
            {
                "INPUT": parameters[self.INPUT_POLYGON_LAYER[0]],
                "FIELD_NAME": self._autogenerated_node_id_field_name,
                "START": 1,
                "OUTPUT": qgis.core.QgsProcessingOutputLayerDefinition(
                    "memory:",
                    qgis.core.QgsProject.instance()
                )
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )["OUTPUT"]
        return layer_with_node_id

    def _generate_layer_with_area_as_node_attribute(
            self,
            source: qgis.core.QgsProcessingFeatureSource,
            feedback: qgis.core.QgsProcessingFeedback,
            context: qgis.core.QgsProcessingContext
    ):
        # check docs on this processing algorithm here:
        # https://docs.qgis.org/testing/en/docs/user_manual/processing_algs/qgis/vectorgeometry.html#qgisexportaddgeometrycolumns
        layer_with_geom_properties_added = processing.run(
            "qgis:exportaddgeometrycolumns",
            {
                "INPUT": source.sourceName(),
                "CALC_METHOD": 2,  # ELLIPSOIDAL
                "OUTPUT": qgis.core.QgsProcessingOutputLayerDefinition(
                    "memory:",
                    qgis.core.QgsProject.instance()
                )
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )["OUTPUT"]
        layer_without_perimeter_attribute = processing.run(
            "native:deletecolumn",
            {
                "INPUT": layer_with_geom_properties_added,
                "COLUMN": "perimeter",
                "OUTPUT": qgis.core.QgsProcessingOutputLayerDefinition(
                    "memory:",
                    qgis.core.QgsProject.instance()
                )
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )["OUTPUT"]
        layer_with_renamed_area_attribute = processing.run(
            "native:renametablefield",
            {
                "INPUT": layer_without_perimeter_attribute,
                "FIELD": "area",
                "NEW_NAME": self._autogenerated_node_attribute_field_name,
                "OUTPUT": qgis.core.QgsProcessingOutputLayerDefinition(
                    "memory:",
                    qgis.core.QgsProject.instance()
                )
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )["OUTPUT"]
        return layer_with_renamed_area_attribute
