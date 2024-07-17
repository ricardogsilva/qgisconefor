from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterFile,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFolderDestination,
)

from processing.core.ProcessingConfig import ProcessingConfig

from ... import utilities
from ...schemas import (
    ConeforRuntimeParameters,
    ConeforNodeConnectionType,
    ConeforProcessingSetting,
    QgisConeforSettingsKey,
)
from . import base


class ConeforProcessorBase(base.Base):

    # links is not supported
    _precision = "double"
    index_code: str = ""
    index_name: str = ""

    INPUT_NODES_FILE_PATH = ("nodes_file_path", "Nodes file path")
    INPUT_CONNECTIONS_FILE_PATH = ("connections_file_path", "Connections file path")
    INPUT_ALL_NODES_CONNECTED = ("all_nodes_connected", "All nodes are connected")
    INPUT_THRESHOLD_DIRECT_LINKS = (
        "threshold_direct_links",
        "Threshold (distance/probability) for connecting nodes (confAdj)"
    )
    INPUT_ONLY_OVERALL_INDEX_VALUES = (
        "only_overall_index_values",
        "Calculate only the overall index values (onlyoverall)"
    )
    INPUT_WRITE_LINKS_FILE = ("write_links_file", "Write links file")
    INPUT_PROCESS_REMOVAL_IMPORTANCES = (
        "process_removal_importances", "Process individual node importances")
    INPUT_REMOVAL_DISTANCE_THRESHOLD = (
        "input_removal_distance_threshold",
        "Maximum threhsold for link removal analysis"
    )
    INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES = (
        "process_link_improvement_importances",
        "Process link improvement importances (-improvement)"
    )
    INPUT_IMPROVEMENT_DISTANCE_THRESHOLD = (
        "improvement_distance_threshold",
        "Maximum threshold for link improvement analysis"
    )
    INPUT_WRITE_COMPONENTS_FILE = (
        "write_components_file",
        "Write components file"
    )
    INPUT_NODE_CONNECTION_TYPE = ("node_connection_type", "node connection type")
    INPUT_CONF_PROB_DISTANCE = ("conf_prob_distance", "distance value used to compute indices when the connection file is a distance file (-confProb distance)")
    INPUT_CONF_PROB_PROBABILITY = ("conf_prob_probability", "probability value used to compute indices when the connection file is a distance file (-confProb distance)")

    INPUT_WRITE_PROB_DIR = ("write_probdir_file", "write direct dispersal probabilities file")
    INPUT_WRITE_PROB_MAX = ("write_probmax_file", "write maximum product probabilities file")
    INPUT_OUTPUT_DIRECTORY = (
        "output_directory", "Output directory for generated Conefor analysis files")

    OUTPUT_COMPONENTS_FILE_PATH = "components_file_path"
    OUTPUT_LINKS_FILE_PATH = "links_file_path"
    OUTPUT_PROBDIR_FILE_PATH = "probdir_file_path"
    OUTPUT_PROBMAX_FILE_PATH = "probmax_file_path"
    OUTPUT_ALL_OVERALL_INDICES_FILE_PATH = "all_overall_indices_file_path"
    OUTPUT_ALL_EC_IIC_FILE_PATH = "all_overall_ec_iic_file_path"
    OUTPUT_ALL_EC_PC_FILE_PATH = "all_overall_ec_pc_file_path"

    def name(self):
        return f"{self.index_code.lower()}"

    def displayName(self):
        return self.index_name

    def _create_parameters(self) -> list[QgsProcessingParameterDefinition]:
        return [
            QgsProcessingParameterFolderDestination(
                name=self.INPUT_OUTPUT_DIRECTORY[0],
                description=self.tr(self.INPUT_OUTPUT_DIRECTORY[1]),
                defaultValue=utilities.load_settings_key(
                    QgisConeforSettingsKey.OUTPUT_DIR, default_to=str(Path.home())
                )
            ),
            QgsProcessingParameterFile(
                name=self.INPUT_NODES_FILE_PATH[0],
                description=self.tr(self.INPUT_NODES_FILE_PATH[1]),
                fileFilter="txt(*.txt)",
            ),
            QgsProcessingParameterFile(
                name=self.INPUT_CONNECTIONS_FILE_PATH[0],
                description=self.tr(self.INPUT_CONNECTIONS_FILE_PATH[1]),
                fileFilter="txt(*.txt)",
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_ALL_NODES_CONNECTED[0],
                self.tr(self.INPUT_ALL_NODES_CONNECTED[1]),
                defaultValue=True
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_ONLY_OVERALL_INDEX_VALUES[0],
                self.tr(self.INPUT_ONLY_OVERALL_INDEX_VALUES[1]),
                defaultValue=False
            ),
        ]

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            self.INPUT_OUTPUT_DIRECTORY[0]: Path(
                self.parameterAsFile(
                    parameters,
                    self.INPUT_OUTPUT_DIRECTORY[0],
                    context
                )
            ),
            self.INPUT_NODES_FILE_PATH[0]: Path(
                self.parameterAsFile(
                    parameters,
                    self.INPUT_NODES_FILE_PATH[0],
                    context
                )
            ),
            self.INPUT_CONNECTIONS_FILE_PATH[0]: Path(
                self.parameterAsFile(
                    parameters,
                    self.INPUT_CONNECTIONS_FILE_PATH[0],
                    context
                )
            ),
            self.INPUT_ALL_NODES_CONNECTED[0]: self.parameterAsBoolean(
                parameters,
                self.INPUT_ALL_NODES_CONNECTED[0],
                context
            ),
            self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]: self.parameterAsBoolean(
                parameters, self.INPUT_ONLY_OVERALL_INDEX_VALUES[0], context),
        }

    def initAlgorithm(self, configuration = None):
        for param in self._create_parameters():
            self.addParameter(param)

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        """Parametrize and run conefor.

        Note that the inputs `conefor_path`, `nodes_path` and `connections_path`
        are all expected to be in the same directory.
        """
        raise NotImplementedError

    def processAlgorithm(self, parameters, context, feedback):
        original_conefor_path = Path(
            ProcessingConfig.getSetting(
                ConeforProcessingSetting.CONEFOR_CLI_PATH.name)
        )
        parsed_inputs = self.get_runtime_parameters(parameters, context, feedback)
        adjusted_paths = _prepare_execution(
            original_conefor_path=original_conefor_path,
            original_nodes_path=parsed_inputs[self.INPUT_NODES_FILE_PATH[0]],
            original_connections_path=parsed_inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
        )
        conefor_path, nodes_path, connections_path = adjusted_paths
        conefor_dir = conefor_path.parent
        feedback.pushInfo(f"About to start execution")
        feedback.pushInfo(f"{conefor_dir=}")
        files_before = list(conefor_dir.iterdir())
        feedback.pushInfo(f"{files_before=}")
        self._run_the_algorithm(
            conefor_path=conefor_path,
            nodes_path=nodes_path,
            connections_path=connections_path,
            inputs=self.get_runtime_parameters(parameters, context, feedback),
            feedback=feedback
        )
        files_after = list(conefor_dir.iterdir())
        feedback.pushInfo(f"{files_after=}")
        new_files = [
            conefor_dir / f for f in files_after if f not in files_before
        ]
        feedback.pushInfo(f"{new_files=}")
        output_dir = Path(
            self.parameterAsFile(
                parameters,
                self.INPUT_OUTPUT_DIRECTORY[0],
                context
            )
        )
        final_files = _store_processing_outputs(output_dir, new_files)
        feedback.pushInfo(f"{final_files=}")
        feedback.setProgress(100)
        return {}

    def canExecute(self) -> tuple[bool, str]:
        conefor_path = Path(
            ProcessingConfig.getSetting(
                ConeforProcessingSetting.CONEFOR_CLI_PATH.name)
        )
        if conefor_path.is_file():
            result = True
            details = ""
        else:
            result = False
            details = self.tr(
                "Could not find the Conefor CLI executable - Check the QGIS settings")
        return result, details


class ConeforBinaryIndexBase(ConeforProcessorBase):
    _NODE_CONNECTION_TYPE_CHOICES = [
        ConeforNodeConnectionType.DISTANCE.value,
        ConeforNodeConnectionType.PROBABILITY.value,
    ]

    def group(self):
        return self.tr("Binary indices")

    def groupId(self):
        return "binaryindices"

    def _create_parameters(self) -> list[QgsProcessingParameterDefinition]:
        params = super()._create_parameters()
        params.extend(
            [
                QgsProcessingParameterEnum(
                    name=self.INPUT_NODE_CONNECTION_TYPE[0],
                    description=self.tr(
                        self.INPUT_NODE_CONNECTION_TYPE[1]),
                    options=self._NODE_CONNECTION_TYPE_CHOICES,
                    defaultValue=ConeforNodeConnectionType.DISTANCE.value
                ),
                QgsProcessingParameterNumber(
                    name=self.INPUT_THRESHOLD_DIRECT_LINKS[0],
                    description=self.tr(self.INPUT_THRESHOLD_DIRECT_LINKS[1]),
                    type=QgsProcessingParameterNumber.Double,
                    optional=True,
                    minValue=0,
                ),
                QgsProcessingParameterBoolean(
                    self.INPUT_WRITE_LINKS_FILE[0],
                    self.tr(self.INPUT_WRITE_LINKS_FILE[1]),
                    defaultValue=False
                ),
                QgsProcessingParameterBoolean(
                    self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0],
                    self.tr(self.INPUT_PROCESS_REMOVAL_IMPORTANCES[1]),
                    defaultValue=False
                ),
                QgsProcessingParameterNumber(
                    name=self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0],
                    description=self.tr(self.INPUT_REMOVAL_DISTANCE_THRESHOLD[1]),
                    type=QgsProcessingParameterNumber.Double,
                    optional=True,
                    minValue=0,
                ),
                QgsProcessingParameterBoolean(
                    self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0],
                    self.tr(self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[1]),
                    defaultValue=False
                ),
                QgsProcessingParameterNumber(
                    name=self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0],
                    description=self.tr(self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[1]),
                    type=QgsProcessingParameterNumber.Double,
                    optional=True,
                    minValue=0,
                ),
            ]
        )
        return params

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            **super().get_runtime_parameters(parameters, context, feedback),
            self.INPUT_NODE_CONNECTION_TYPE[0]: ConeforNodeConnectionType(
                self._NODE_CONNECTION_TYPE_CHOICES[
                    self.parameterAsEnum(
                        parameters, self.INPUT_NODE_CONNECTION_TYPE[0], context
                    )
                ]
            ),
            self.INPUT_THRESHOLD_DIRECT_LINKS[0]: self.parameterAsDouble(
                parameters, self.INPUT_THRESHOLD_DIRECT_LINKS[0], context
            ),
            self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]: self.parameterAsBoolean(
                parameters, self.INPUT_ONLY_OVERALL_INDEX_VALUES[0], context
            ),
            self.INPUT_WRITE_LINKS_FILE[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_LINKS_FILE[0], context
            ),
            self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]: self.parameterAsBoolean(
                parameters, self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0], context
            ),
            self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]: self.parameterAsDouble(
                parameters, self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0], context
            ),
            self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]: self.parameterAsBoolean(
                parameters, self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0], context
            ),
            self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]: self.parameterAsDouble(
                parameters, self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0], context
            )
        }


class ConeforNCProcessor(ConeforBinaryIndexBase):
    index_name = "NC (Number of Components)"
    index_code = "NC"

    def _create_parameters(self):
        parameters = super()._create_parameters()
        parameters.extend(
            [
                QgsProcessingParameterBoolean(
                    self.INPUT_WRITE_COMPONENTS_FILE[0],
                    self.tr(self.INPUT_WRITE_COMPONENTS_FILE[1]),
                    defaultValue=False
                ),
            ]
        )
        return parameters

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            **super().get_runtime_parameters(parameters, context, feedback),
            self.INPUT_WRITE_COMPONENTS_FILE[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_COMPONENTS_FILE[0], context
            )
        }
    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=threshold_direct_links,
                binary_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_component_file=inputs[self.INPUT_WRITE_COMPONENTS_FILE[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                    self.index_code,
                    threshold_direct_links
                ))
            ),
            feedback=feedback,
        )


class ConeforNLProcessor(ConeforBinaryIndexBase):
    index_name = "NL (Number of Links)"
    index_code = "NL"

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=threshold_direct_links,
                binary_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_component_file=inputs[self.INPUT_WRITE_COMPONENTS_FILE[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                    self.index_code,
                    threshold_direct_links
                ))
            ),
            feedback=feedback
        )


class ConeforHProcessor(ConeforBinaryIndexBase):
    index_name = "H (Harary)"
    index_code = "H"

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=threshold_direct_links,
                binary_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_component_file=inputs[self.INPUT_WRITE_COMPONENTS_FILE[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                    self.index_code,
                    threshold_direct_links
                ))
            ),
            feedback=feedback,
        )


class ConeforCCPProcessor(ConeforBinaryIndexBase):
    index_name = "CCP (Class Coincidence Probability)"
    index_code = "CCP"

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=threshold_direct_links,
                binary_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_component_file=inputs[self.INPUT_WRITE_COMPONENTS_FILE[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                    self.index_code,
                    threshold_direct_links
                ))

            ),
            feedback=feedback
        )


class ConeforLCPProcessor(ConeforBinaryIndexBase):
    index_name = "LCP (Landscape Coincidence Probability)"
    index_code = "LCP"

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=threshold_direct_links,
                binary_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_component_file=inputs[self.INPUT_WRITE_COMPONENTS_FILE[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                    self.index_code,
                    threshold_direct_links
                ))
            ),
            feedback=feedback
        )


class ConeforIICProcessor(ConeforBinaryIndexBase):
    index_name = "IIC (Integral Index of Connectivity)"
    index_code = "IIC"

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=threshold_direct_links,
                binary_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_component_file=inputs[self.INPUT_WRITE_COMPONENTS_FILE[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                    self.index_code,
                    threshold_direct_links
                ))

            ),
            feedback=feedback
        )


class ConeforBCProcessor(ConeforBinaryIndexBase):
    index_name = "BC (Betweeness Centrality Classic)"
    index_code = "BC"

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=threshold_direct_links,
                binary_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                    self.index_code,
                    str(threshold_direct_links)
                ))

            ),
            feedback=feedback,
        )


class ConeforBCIICProcessor(ConeforBCProcessor):
    index_name = "BCIIC (Betweeness Centrality Generalized IIC)"
    index_code = "BCIIC"

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=threshold_direct_links,
                binary_indexes=["IIC", self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                    self.index_code,
                    threshold_direct_links
                ))

            ),
            feedback=feedback,
        )


class ConeforProbabilityIndexBase(ConeforProcessorBase):

    def group(self):
        return self.tr("Probabilistic indices")

    def groupId(self):
        return "probabilityindices"

    def _create_parameters(self) -> list[QgsProcessingParameterDefinition]:
        params = super()._create_parameters()
        params.extend([
            QgsProcessingParameterBoolean(
                self.INPUT_WRITE_PROB_DIR[0],
                self.tr(self.INPUT_WRITE_PROB_DIR[1]),
                defaultValue=False
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0],
                self.tr(self.INPUT_PROCESS_REMOVAL_IMPORTANCES[1]),
                defaultValue=False
            ),
            QgsProcessingParameterNumber(
                name=self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0],
                description=self.tr(self.INPUT_REMOVAL_DISTANCE_THRESHOLD[1]),
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0,
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0],
                self.tr(self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[1]),
                defaultValue=False
            ),
            QgsProcessingParameterNumber(
                name=self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0],
                description=self.tr(self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[1]),
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0,
            ),

        ])
        return params

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            **super().get_runtime_parameters(parameters, context, feedback),
            self.INPUT_WRITE_PROB_DIR[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_PROB_DIR[0], context
            ),
            self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]: self.parameterAsBoolean(
                parameters, self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0], context
            ),
            self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]: self.parameterAsDouble(
                parameters, self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0], context
            ),
            self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]: self.parameterAsBoolean(
                parameters, self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0], context
            ),
            self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]: self.parameterAsDouble(
                parameters, self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0], context
            ),
        }


class ProbabilityIndexDistanceBase(ConeforProbabilityIndexBase):
    _connection_type = ConeforNodeConnectionType.DISTANCE

    def group(self):
        return self.tr("Probabilistic indices (distance based)")

    def groupId(self):
        return "probabilityindicesdistance"

    def _create_parameters(self) -> list[QgsProcessingParameterDefinition]:
        params = super()._create_parameters()
        params.extend([
            QgsProcessingParameterNumber(
                self.INPUT_CONF_PROB_DISTANCE[0],
                self.tr(self.INPUT_CONF_PROB_DISTANCE[1]),
                type=QgsProcessingParameterNumber.Double,
            ),
            QgsProcessingParameterNumber(
                self.INPUT_CONF_PROB_PROBABILITY[0],
                self.tr(self.INPUT_CONF_PROB_PROBABILITY[1]),
                type=QgsProcessingParameterNumber.Double,
            ),
        ])
        return params

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            **super().get_runtime_parameters(parameters, context, feedback),
            self.INPUT_CONF_PROB_DISTANCE[0]: self.parameterAsDouble(
                parameters, self.INPUT_CONF_PROB_DISTANCE[0], context
            ),
            self.INPUT_CONF_PROB_PROBABILITY[0]: self.parameterAsDouble(
                parameters, self.INPUT_CONF_PROB_PROBABILITY[0], context
            ),
        }

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback
    ):
        decay_distance = inputs[self.INPUT_CONF_PROB_DISTANCE[0]]
        decay_probability = inputs[self.INPUT_CONF_PROB_PROBABILITY[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=self._connection_type,
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                decay_distance=decay_distance,
                decay_probability=decay_probability,
                probability_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_dispersal_probabilities_file=inputs[self.INPUT_WRITE_PROB_DIR[0]],
                prefix="_".join((
                    self.INPUT_NODES_FILE_PATH[0].stem,
                    self.index_code,
                    decay_distance,
                    decay_probability
                ))
            ),
            feedback=feedback
        )


class ConeforFDistanceProcessor(ProbabilityIndexDistanceBase):
    index_name = "F (Flux - distance-based)"
    index_code = "Fdist"


class ConeforAWFDistanceProcessor(ProbabilityIndexDistanceBase):
    index_name = "AWF (Area-weighted Flux - distance-based)"
    index_code = "AWFdist"


class ConeforPCDistanceProcessor(ProbabilityIndexDistanceBase):
    index_name = "PC (Probability of Connectivity - distance-based)"
    index_code = "PCdist"

    def _create_parameters(self) -> list[QgsProcessingParameterDefinition]:
        params = super()._create_parameters()
        params.extend([
            QgsProcessingParameterBoolean(
                self.INPUT_WRITE_PROB_MAX[0],
                self.tr(self.INPUT_WRITE_PROB_MAX[1]),
                defaultValue=False
            )

        ])
        return params

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            **super().get_runtime_parameters(parameters, context, feedback),
            self.INPUT_WRITE_PROB_MAX[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_PROB_MAX[0], context
            ),
        }

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback
    ):
        decay_distance = inputs[self.INPUT_CONF_PROB_DISTANCE[0]]
        decay_probability = inputs[self.INPUT_CONF_PROB_PROBABILITY[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=self._connection_type,
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                decay_distance=decay_distance,
                decay_probability=decay_probability,
                probability_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_dispersal_probabilities_file=inputs[self.INPUT_WRITE_PROB_DIR[0]],
                write_maximum_probabilities_file=inputs[self.INPUT_WRITE_PROB_MAX[0]],
                prefix="_".join((
                    self.INPUT_NODES_FILE_PATH[0].stem,
                    self.index_code,
                    decay_distance,
                    decay_probability
                ))
            ),
            feedback=feedback
        )


class ConeforBCPCDistanceProcessor(ProbabilityIndexDistanceBase):
    index_name = "BCPC (Betweeness Centrality Generalized PC - distance-based)"
    index_code = "BCPCdist"

    def _create_parameters(self) -> list[QgsProcessingParameterDefinition]:
        params = super()._create_parameters()
        params.extend([
            QgsProcessingParameterNumber(
                self.INPUT_THRESHOLD_DIRECT_LINKS[0],
                self.tr(self.INPUT_THRESHOLD_DIRECT_LINKS[1]),
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_WRITE_LINKS_FILE[0],
                self.tr(self.INPUT_WRITE_LINKS_FILE[1]),
                defaultValue=False
            ),
            params.extend([
                QgsProcessingParameterBoolean(
                    self.INPUT_WRITE_PROB_MAX[0],
                    self.tr(self.INPUT_WRITE_PROB_MAX[1]),
                    defaultValue=False
                )

            ])

        ])
        return params

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            **super().get_runtime_parameters(parameters, context, feedback),
            self.INPUT_THRESHOLD_DIRECT_LINKS[0]: self.parameterAsDouble(
                parameters, self.INPUT_THRESHOLD_DIRECT_LINKS[0], context
            ),
            self.INPUT_WRITE_LINKS_FILE[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_LINKS_FILE[0], context
            ),
            self.INPUT_WRITE_PROB_MAX[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_PROB_MAX[0], context
            ),
        }

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback
    ):
        decay_distance = inputs[self.INPUT_CONF_PROB_DISTANCE[0]]
        decay_probability = inputs[self.INPUT_CONF_PROB_PROBABILITY[0]]
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=self._connection_type,
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]],
                binary_indexes=["BC"],
                decay_distance=decay_distance,
                decay_probability=decay_probability,
                probability_indexes=["PC", self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                write_dispersal_probabilities_file=inputs[self.INPUT_WRITE_PROB_DIR[0]],
                write_maximum_probabilities_file=inputs[self.INPUT_WRITE_PROB_MAX[0]],
                prefix="_".join((
                    self.INPUT_NODES_FILE_PATH[0].stem,
                    self.index_code,
                    decay_distance,
                    decay_probability
                ))
            ),
            feedback=feedback
        )


class ProbabilityIndexProbabilityBase(ConeforProbabilityIndexBase):
    _connection_type = ConeforNodeConnectionType.PROBABILITY

    def group(self):
        return self.tr("Probabilistic indices (probability based)")

    def groupId(self):
        return "probabilityindicesprobability"


class ConeforFProbabilityProcessor(ProbabilityIndexProbabilityBase):
    index_name = 'F (Flux - probability-based)'
    index_code = 'Fprob'


class ConeforAWFProbabilityProcessor(ProbabilityIndexProbabilityBase):
    index_name = 'AWF (Area-weighted Flux - probability-based)'
    index_code = 'AWFprob'


class ConeforPCProbabilityProcessor(ProbabilityIndexProbabilityBase):
    index_name = 'PC (Probability of Connectivity - probability-based)'
    index_code = 'PCprob'

    def _create_parameters(self) -> list[QgsProcessingParameterDefinition]:
        params = super()._create_parameters()
        params.extend([
            QgsProcessingParameterBoolean(
                self.INPUT_WRITE_PROB_MAX[0],
                self.tr(self.INPUT_WRITE_PROB_MAX[1]),
                defaultValue=False
            )
        ])
        return params

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            **super().get_runtime_parameters(parameters, context, feedback),
            self.INPUT_WRITE_PROB_MAX[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_PROB_MAX[0], context
            ),
        }

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback
    ):
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=self._connection_type,
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                probability_indexes=[self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                removal=inputs[self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0]],
                removal_threshold=inputs[self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0]],
                improvement=inputs[self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0]],
                improvement_threshold=inputs[self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0]],
                write_dispersal_probabilities_file=inputs[self.INPUT_WRITE_PROB_DIR[0]],
                write_maximum_probabilities_file=inputs[self.INPUT_WRITE_PROB_MAX[0]],
                prefix="_".join((
                    self.INPUT_NODES_FILE_PATH[0].stem,
                    self.index_code,
                ))
            ),
            feedback=feedback
        )


class ConeforBCPCProbabilityProcessor(ProbabilityIndexProbabilityBase):
    index_name = 'BCPC (Betweeness Centrality Generalized PC - probability-based)'
    index_code = 'BCPCprob'

    def _create_parameters(self) -> list[QgsProcessingParameterDefinition]:
        params = super()._create_parameters()
        params.extend([
            QgsProcessingParameterNumber(
                name=self.INPUT_THRESHOLD_DIRECT_LINKS[0],
                description=self.tr(self.INPUT_THRESHOLD_DIRECT_LINKS[1]),
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0,
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_WRITE_LINKS_FILE[0],
                self.tr(self.INPUT_WRITE_LINKS_FILE[1]),
                defaultValue=False
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_ONLY_OVERALL_INDEX_VALUES[0],
                self.tr(self.INPUT_ONLY_OVERALL_INDEX_VALUES[1]),
                defaultValue=False
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_WRITE_PROB_DIR[0],
                self.tr(self.INPUT_WRITE_PROB_DIR[1]),
                defaultValue=False
            ),
            QgsProcessingParameterBoolean(
                self.INPUT_WRITE_PROB_MAX[0],
                self.tr(self.INPUT_WRITE_PROB_MAX[1]),
                defaultValue=False
            )
        ])
        return params

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: QgsProcessingContext,
            feedback: QgsProcessingFeedback
    ) -> dict:
        return {
            **super().get_runtime_parameters(parameters, context, feedback),
            self.INPUT_THRESHOLD_DIRECT_LINKS[0]: self.parameterAsDouble(
                parameters, self.INPUT_THRESHOLD_DIRECT_LINKS[0], context
            ),
            self.INPUT_WRITE_LINKS_FILE[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_LINKS_FILE[0], context
            ),
            self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]: self.parameterAsBoolean(
                parameters, self.INPUT_ONLY_OVERALL_INDEX_VALUES[0], context),
            self.INPUT_WRITE_PROB_DIR[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_PROB_DIR[0], context
            ),
            self.INPUT_WRITE_PROB_MAX[0]: self.parameterAsBoolean(
                parameters, self.INPUT_WRITE_PROB_MAX[0], context
            ),
        }

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            inputs: dict,
            feedback: QgsProcessingFeedback
    ):
        return _run_conefor(
            params=ConeforRuntimeParameters(
                conefor_path=conefor_path,
                nodes_path=nodes_path,
                connections_path=connections_path,
                connection_type=self._connection_type,
                all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
                threshold_direct_links=inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]],
                binary_indexes=["BC"],
                probability_indexes=["PC", self.index_code],
                only_overall=inputs[self.INPUT_ONLY_OVERALL_INDEX_VALUES[0]],
                write_dispersal_probabilities_file=inputs[self.INPUT_WRITE_PROB_DIR[0]],
                write_maximum_probabilities_file=inputs[self.INPUT_WRITE_PROB_MAX[0]],
                write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
                prefix="_".join((
                    self.INPUT_NODES_FILE_PATH[0].stem,
                    self.index_code,
                ))
            ),
            feedback=feedback
        )


def _prepare_execution(
        *,
        original_conefor_path: Path,
        original_nodes_path: Path,
        original_connections_path: Path,
) -> tuple[Path, Path, Path]:
    """Copy the input paths into a temporary directory.

    Conefor requires inputs and itself to be on the same directory.
    """

    execution_directory = Path(tempfile.mkdtemp(prefix="qgisconefor_"))
    new_conefor_path = execution_directory / original_conefor_path.name
    shutil.copy(original_conefor_path, new_conefor_path)
    new_nodes_path = execution_directory / original_nodes_path.name
    shutil.copy(original_nodes_path, new_nodes_path)
    new_connections_path = execution_directory / original_connections_path.name
    shutil.copy(original_connections_path, new_connections_path)
    return new_conefor_path, new_nodes_path, new_connections_path


def _run_conefor(
        params: ConeforRuntimeParameters,
        feedback: QgsProcessingFeedback
) -> bool:
    command_list = [
        str(params.conefor_path),
        "-nodeFile", str(params.nodes_path),
        "-conFile", str(params.connections_path),
        "-t", params.connection_type.value,
        "all" if params.all_pairs_connected else "notall",
    ]
    bin_indexes = params.binary_indexes[:] if params.binary_indexes else []
    prob_indexes = params.probability_indexes[:] if params.probability_indexes else []

    if any(bin_indexes):
        if "BCIIC" in bin_indexes and "IIC" not in bin_indexes:
            bin_indexes.append("IIC")
        if "BCIIC" in bin_indexes and "BC" not in bin_indexes:
            bin_indexes.append("BC")
    if any(prob_indexes):
        if "BCPC" in prob_indexes and "PC" not in prob_indexes:
            prob_indexes.append("PC")
        if "BCPC" in prob_indexes and "BC" not in bin_indexes:
            bin_indexes.append("BC")

    if any(bin_indexes):
        command_list += ["-confAdj", "%1.3f" % params.threshold_direct_links]
        command_list.extend(f"-{idx}" for idx in bin_indexes)
    if any(prob_indexes):
        if params.connection_type == ConeforNodeConnectionType.DISTANCE:
            command_list += [
                "-confProb",
                "%1.3f" % params.decay_distance,
                "%1.3f" % params.decay_probability
            ]
        command_list.extend(f"-{idx}" for idx in prob_indexes)

    if params.only_overall:
        command_list.append('onlyoverall')
    if params.removal:
        command_list.append('-removal')
        if params.removal_threshold is not None:
            command_list.extend(["maxValue", str(params.removal_threshold)])
    if params.improvement:
        command_list.append('-improvement')
        if params.improvement_threshold is not None:
            command_list.extend(["maxValue", str(params.improvement_threshold)])
    if params.write_component_file and 'NC' in bin_indexes:
        command_list.append('-wcomp')
    if params.write_links_file and any(bin_indexes):
        command_list.append('-wlinks')
    if params.write_dispersal_probabilities_file and any(prob_indexes):
        command_list.append('-wprobdir')
    if params.write_maximum_probabilities_file and 'PC' in prob_indexes:
        command_list.append('-wprobmax')
    if params.land_area is not None:
        command_list += ['-landArea', params.land_area]
    prefix = "_".join(("results", params.prefix or "")).lstrip("_")
    command_list += ['-prefix', prefix]
    full_command = " ".join(command_list)
    feedback.pushInfo(f"{full_command=}")
    completed_process = subprocess.run(
        shlex.split(full_command),
        cwd=params.conefor_path.parent,
        text=True,
        capture_output=True,
    )
    feedback.pushInfo(completed_process.stdout)
    return completed_process.returncode == 0


def _store_processing_outputs(
        intended_output_dir: Path,
        outputs: list[Path],
) -> list[Path]:
    stored = []
    for output in outputs:
        if output.name in (
                "results_all_overall_indices.txt",
                "results_all_EC(IIC).txt",
                "results_all_EC(PC).txt"
        ):
            stored.append(
                _store_output_in_target_directory(
                    intended_output_dir, output, append_if_exists=True)
            )
        else:
            stored.append(
                _store_output_in_target_directory(
                    intended_output_dir, output
                )
            )
    return stored


def _store_output_in_target_directory(
        intended_output_dir: Path,
        output: Path,
        append_if_exists: bool = False
) -> Path:
    contents = output.read_text()
    target = intended_output_dir / output.name
    if target.exists():
        if append_if_exists:
            with target.open(mode="a") as fh:
                fh.write(contents)
        else:
            shutil.copy(output, target)
    else:
        shutil.copy(output, target)
    return target
