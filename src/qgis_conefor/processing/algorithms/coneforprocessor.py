import os
from pathlib import Path
import shlex
import subprocess

import qgis.core

from processing.core.ProcessingConfig import ProcessingConfig
from processing.core.ProcessingResults import ProcessingResults
from qgis._core import QgsProcessingParameters

from ... import utilities
from ...schemas import (
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

    INPUT_NODES_FILE_PATH = ("nodes_file_path", "Conefor nodes file path")
    INPUT_CONNECTIONS_FILE_PATH = ("connections_file_path", "Conefor connections file path")
    INPUT_ALL_NODES_CONNECTED = ("all_nodes_connected", "Whether all nodes are connected")
    INPUT_THRESHOLD_DIRECT_LINKS = (
        "threshold_direct_links",
        "Threshold (distance/probability) for connecting nodes (confAdj)"
    )
    INPUT_CREATE_NODE_IMPORTANCES = (
        "create_node_importances", "Process individual node importances")
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


    DISTANCE_PROB = "DISTANCE_PROB"
    PROBABILITY_PROB = "PROBABILITY_PROB"

    WRITE_PROB_DIR = "WRITE_PROB_DIR"
    WRITE_PROB_MAX = "WRITE_PROB_MAX"
    INPUT_OUTPUT_DIRECTORY = (
        "output_directory", "Output directory for generated Conefor analysis files")

    _parameter_order = [
        INPUT_NODES_FILE_PATH[0],
        INPUT_CONNECTIONS_FILE_PATH[0],
        INPUT_NODE_CONNECTION_TYPE,
        INPUT_ALL_NODES_CONNECTED[0],
        # -* option is not used by this plugin
        INPUT_THRESHOLD_DIRECT_LINKS,
        # binary_indices are not selectable in the GUI
        DISTANCE_PROB,
        PROBABILITY_PROB,
        # probability indices are not selectable in the GUI
        INPUT_CREATE_NODE_IMPORTANCES,
        # pcHeur is not implemented, yet
        # -add is not implemented, yet
        INPUT_PROCESS_REMOVAL_IMPORTANCES,
        INPUT_REMOVAL_DISTANCE_THRESHOLD,
        INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES,
        INPUT_IMPROVEMENT_DISTANCE_THRESHOLD,
        # -change is not implemented in this plugin
        # self._precision is not exposed in the GUI
        # -noout is not used by this plugin
        INPUT_WRITE_COMPONENTS_FILE,
        INPUT_WRITE_LINKS_FILE,
        WRITE_PROB_DIR,
        WRITE_PROB_MAX,
        # -landArea is not implemented, yet
        # prefix is not exposed in the GUI
        INPUT_OUTPUT_DIRECTORY[0],
    ]

    def name(self):
        return f"{self.index_code}"

    def displayName(self):
        return f"{self.index_code} ({self.index_name})"

    def _create_parameters(self) -> list[qgis.core.QgsProcessingParameterDefinition]:
        return [
            qgis.core.QgsProcessingParameterFolderDestination(
                name=self.INPUT_OUTPUT_DIRECTORY[0],
                description=self.tr(self.INPUT_OUTPUT_DIRECTORY[1]),
                defaultValue=utilities.load_settings_key(
                    QgisConeforSettingsKey.OUTPUT_DIR, default_to=str(Path.home())
                )
            ),
            qgis.core.QgsProcessingParameterFile(
                name=self.INPUT_NODES_FILE_PATH[0],
                description=self.tr(self.INPUT_NODES_FILE_PATH[1]),
                fileFilter="*.txt",
            ),
            qgis.core.QgsProcessingParameterFile(
                name=self.INPUT_CONNECTIONS_FILE_PATH[0],
                description=self.tr(self.INPUT_CONNECTIONS_FILE_PATH[1]),
                fileFilter="*.txt",
        ),
            qgis.core.QgsProcessingParameterBoolean(
                self.INPUT_ALL_NODES_CONNECTED[0],
                self.tr(self.INPUT_ALL_NODES_CONNECTED[1]),
                defaultValue=True
            ),
        ]

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: qgis.core.QgsProcessingContext,
            feedback: qgis.core.QgsProcessingFeedback
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
        }

    def initAlgorithm(self, configuration = None):
        for param in self._create_parameters():
            self.addParameter(param)

    def _run_the_algorithm(
            self,
            *,
            conefor_path: Path,
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        raise NotImplementedError

    def processAlgorithm(self, parameters, context, feedback):
        conefor_path = Path(
            ProcessingConfig.getSetting(ConeforProcessingSetting.CONEFOR_CLI_PATH))
        conefor_dir = conefor_path.parent
        files_before = list(conefor_dir.iterdir())
        self._run_the_algorithm(
            conefor_path=conefor_path,
            inputs=self.get_runtime_parameters(parameters, context, feedback),
            feedback=feedback
        )
        files_after = list(conefor_dir.iterdir())
        new_files = [
            conefor_dir / f for f in files_after if f not in files_before
        ]
        output_dir = Path(
            self.parameterAsFile(
                parameters,
                self.INPUT_OUTPUT_DIRECTORY[0],
                context
            )
        )
        utilities.store_processing_outputs(output_dir, new_files)
        # for new_file in result_files:
        #     name = os.path.basename(new_file)
        #     ProcessingResults.addResult(name, new_file)
        feedback.setProgress(100)

    def _run_conefor(
            self,
            *,
            feedback: qgis.core.QgsProcessingFeedback,
            conefor_path: Path,
            nodes_path: Path,
            connections_path: Path,
            connection_type,
            all_pairs_connected: bool,
            threshold_direct_links=0,
            binary_indexes: list[str] | None = None,
            decay_distance=0,
            decay_probability=0,
            probability_indexes: list[str] | None = None,
            only_overall: bool = False,
            removal: bool = False,
            removal_threshold=None,
            improvement: bool = False,
            improvement_threshold=None,
            write_component_file: bool = False,
            write_links_file: bool = False,
            write_dispersal_probabilities_file: bool = False,
            write_maximum_probabilities_file: bool = False,
            land_area=None,
            prefix=None
    ) -> bool:
        """Run Conefor and return the output.

        In order to successfuly run the conefor CLI executable, the following
        constraints must be taken into consideration:

            - conefor will only save the output files to disk if it is called
              from the same directory where the executable is located
            - conefor will save output files in the same directory
              as the executable.
        """

        conefor_dir, conefor_file_name = os.path.split(conefor_path)
        command_list = []
        command_list += [
            conefor_path,
            "-nodeFile", str(nodes_path),
            "-conFile", str(connections_path),
            "-t", connection_type,
            "all" if all_pairs_connected else "notall",
        ]
        if any(binary_indexes):
            command_list += ['-confAdj', '%1.3f' % threshold_direct_links]
            if 'BCIIC' in binary_indexes and 'IIC' not in binary_indexes:
                binary_indexes.append('IIC')
            if 'BCIIC' in binary_indexes and 'BC' not in binary_indexes:
                binary_indexes.append('BC')
            command_list.extend(f"-{idx}" for idx in binary_indexes)

        if any(probability_indexes):
            if connection_type == 'dist':
                command_list += [
                    '-confProb', '%1.3f' % decay_distance,
                    '%1.3f' % decay_probability
                ]
            if 'BCPC' in probability_indexes and 'PC' not in probability_indexes:
                probability_indexes.append('PC')
            if 'BCPC' in probability_indexes and 'BC' not in binary_indexes:
                binary_indexes.append('BC')
            command_list.extend(f"-{idx}" for idx in probability_indexes)

        if only_overall:
            command_list.append('onlyoverall')
        if removal:
            command_list.append('-removal')
            if removal_threshold is not None:
                command_list.extend(["maxValue", str(removal_threshold)])
        if improvement:
            command_list.append('-improvement')
            if improvement_threshold is not None:
                command_list.extend(["maxValue", str(improvement_threshold)])
        command_list.append(f'-{self._precision}')
        if write_component_file and 'NC' in binary_indexes:
            command_list.append('-wcomp')
        if write_links_file and any(binary_indexes):
            command_list.append('-wlinks')
        if write_dispersal_probabilities_file and any(probability_indexes):
            command_list.append('-wprobdir')
        if write_maximum_probabilities_file and 'PC' in probability_indexes:
            command_list.append('-wprobmax')
        if land_area is not None:
            command_list += ['-landArea', land_area]
        if prefix is not None:
            command_list += ['-prefix', prefix]
        full_command = " ".join(command_list)
        utilities.log(f"{full_command=}")
        completed_process = subprocess.run(
            shlex.split(full_command),
            cwd=conefor_dir,
            text=True,
            capture_output=True,
        )
        feedback.pushInfo(completed_process.stdout)
        return completed_process.returncode == 0

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

    def _create_parameters(self):
        params = super()._create_parameters()
        params.extend(
            [
                qgis.core.QgsProcessingParameterEnum(
                    name=self.INPUT_NODE_CONNECTION_TYPE[0],
                    description=self.tr(
                        self.INPUT_NODE_CONNECTION_TYPE[1]),
                    options=self._NODE_CONNECTION_TYPE_CHOICES,
                    defaultValue=ConeforNodeConnectionType.DISTANCE.value
                ),
                qgis.core.QgsProcessingParameterNumber(
                    name=self.INPUT_THRESHOLD_DIRECT_LINKS[0],
                    description=self.tr(self.INPUT_THRESHOLD_DIRECT_LINKS[1]),
                    type=qgis.core.QgsProcessingParameterNumber.Double,
                    optional=True,
                    minValue=0,
                ),
                qgis.core.QgsProcessingParameterBoolean(
                    self.INPUT_CREATE_NODE_IMPORTANCES[0],
                    self.tr(self.INPUT_CREATE_NODE_IMPORTANCES[1]),
                    defaultValue=False
                ),
                qgis.core.QgsProcessingParameterBoolean(
                    self.INPUT_WRITE_LINKS_FILE[0],
                    self.tr(self.INPUT_WRITE_LINKS_FILE[1]),
                    defaultValue=False
                ),
                qgis.core.QgsProcessingParameterBoolean(
                    self.INPUT_PROCESS_REMOVAL_IMPORTANCES[0],
                    self.tr(self.INPUT_PROCESS_REMOVAL_IMPORTANCES[1]),
                    defaultValue=False
                ),
                qgis.core.QgsProcessingParameterNumber(
                    name=self.INPUT_REMOVAL_DISTANCE_THRESHOLD[0],
                    description=self.tr(self.INPUT_REMOVAL_DISTANCE_THRESHOLD[1]),
                    type=qgis.core.QgsProcessingParameterNumber.Double,
                    optional=True,
                    minValue=0,
                ),
                qgis.core.QgsProcessingParameterBoolean(
                    self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[0],
                    self.tr(self.INPUT_PROCESS_LINK_IMPROVEMENT_IMPORTANCES[1]),
                    defaultValue=False
                ),
                qgis.core.QgsProcessingParameterNumber(
                    name=self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[0],
                    description=self.tr(self.INPUT_IMPROVEMENT_DISTANCE_THRESHOLD[1]),
                    type=qgis.core.QgsProcessingParameterNumber.Double,
                    optional=True,
                    minValue=0,
                ),
            ]
        )
        return params

    def get_runtime_parameters(
            self,
            parameters: dict,
            context: qgis.core.QgsProcessingContext,
            feedback: qgis.core.QgsProcessingFeedback
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
            self.INPUT_CREATE_NODE_IMPORTANCES[0]: self.parameterAsBoolean(
                parameters, self.INPUT_CREATE_NODE_IMPORTANCES[0], context
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
    index_name = 'Number of Components'
    index_code = 'NC'

    def _create_parameters(self):
        parameters = super()._create_parameters()
        parameters.extend(
            [
                qgis.core.QgsProcessingParameterBoolean(
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
            context: qgis.core.QgsProcessingContext,
            feedback: qgis.core.QgsProcessingFeedback
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
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return self._run_conefor(
            feedback=feedback,
            conefor_path=conefor_path,
            nodes_path=inputs[self.INPUT_NODES_FILE_PATH[0]],
            connections_path=inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
            connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
            all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
            threshold_direct_links=threshold_direct_links,
            binary_indexes=[self.index_code],
            only_overall=inputs[self.INPUT_CREATE_NODE_IMPORTANCES[0]],
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
        )


class ConeforNLProcessor(ConeforBinaryIndexBase):
    index_name = 'Number of Links'
    index_code = 'NL'

    def _run_the_algorithm(
            self,
            *,
            conefor_path,
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return self._run_conefor(
            feedback=feedback,
            conefor_path=conefor_path,
            nodes_path=inputs[self.INPUT_NODES_FILE_PATH[0]],
            connections_path=inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
            connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
            all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
            threshold_direct_links=threshold_direct_links,
            binary_indexes=[self.index_code],
            only_overall=inputs[self.INPUT_CREATE_NODE_IMPORTANCES[0]],
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
        )


class ConeforHProcessor(ConeforBinaryIndexBase):
    index_name = 'Harary'
    index_code = 'H'

    def _run_the_algorithm(
            self,
            *,
            conefor_path,
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return self._run_conefor(
            feedback=feedback,
            conefor_path=conefor_path,
            nodes_path=inputs[self.INPUT_NODES_FILE_PATH[0]],
            connections_path=inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
            connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
            all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
            threshold_direct_links=threshold_direct_links,
            binary_indexes=[self.index_code],
            only_overall=inputs[self.INPUT_CREATE_NODE_IMPORTANCES[0]],
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
        )


class ConeforCCPProcessor(ConeforBinaryIndexBase):
    index_name = 'Class Coincidence Probability'
    index_code = 'CCP'

    def _run_the_algorithm(
            self,
            *,
            conefor_path,
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return self._run_conefor(
            feedback=feedback,
            conefor_path=conefor_path,
            nodes_path=inputs[self.INPUT_NODES_FILE_PATH[0]],
            connections_path=inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
            connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
            all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
            threshold_direct_links=threshold_direct_links,
            binary_indexes=[self.index_code],
            only_overall=inputs[self.INPUT_CREATE_NODE_IMPORTANCES[0]],
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
        )


class ConeforLCPProcessor(ConeforBinaryIndexBase):
    index_name = 'Landscape Coincidence Probability'
    index_code = 'LCP'

    def _run_the_algorithm(
            self,
            *,
            conefor_path,
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return self._run_conefor(
            feedback=feedback,
            conefor_path=conefor_path,
            nodes_path=inputs[self.INPUT_NODES_FILE_PATH[0]],
            connections_path=inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
            connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
            all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
            threshold_direct_links=threshold_direct_links,
            binary_indexes=[self.index_code],
            only_overall=inputs[self.INPUT_CREATE_NODE_IMPORTANCES[0]],
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
        )


class ConeforIICProcessor(ConeforBinaryIndexBase):
    index_name = 'Integral Index of Connectivity'
    index_code = 'IIC'

    def _run_the_algorithm(
            self,
            *,
            conefor_path,
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return self._run_conefor(
            feedback=feedback,
            conefor_path=conefor_path,
            nodes_path=inputs[self.INPUT_NODES_FILE_PATH[0]],
            connections_path=inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
            connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
            all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
            threshold_direct_links=threshold_direct_links,
            binary_indexes=[self.index_code],
            only_overall=inputs[self.INPUT_CREATE_NODE_IMPORTANCES[0]],
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
        )


class ConeforBCProcessor(ConeforBinaryIndexBase):
    index_name = 'Betweeness Centrality (Classic)'
    index_code = 'BC'

    def _run_the_algorithm(
            self,
            *,
            conefor_path,
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return self._run_conefor(
            feedback=feedback,
            conefor_path=conefor_path,
            nodes_path=inputs[self.INPUT_NODES_FILE_PATH[0]],
            connections_path=inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
            connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
            all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
            threshold_direct_links=threshold_direct_links,
            binary_indexes=[self.index_code],
            only_overall=inputs[self.INPUT_CREATE_NODE_IMPORTANCES[0]],
            write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
            prefix="_".join((
                inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                self.index_code,
                threshold_direct_links
            ))
        )


class ConeforBCIICProcessor(ConeforBCProcessor):
    index_name = 'Betweeness Centrality Generalized(IIC)'
    index_code = 'BCIIC'

    def _run_the_algorithm(
            self,
            *,
            conefor_path,
            inputs: dict,
            feedback: qgis.core.QgsProcessingFeedback,
    ):
        threshold_direct_links = inputs[self.INPUT_THRESHOLD_DIRECT_LINKS[0]]
        return self._run_conefor(
            feedback=feedback,
            conefor_path=conefor_path,
            nodes_path=inputs[self.INPUT_NODES_FILE_PATH[0]],
            connections_path=inputs[self.INPUT_CONNECTIONS_FILE_PATH[0]],
            connection_type=inputs[self.INPUT_NODE_CONNECTION_TYPE[0]],
            all_pairs_connected=inputs[self.INPUT_ALL_NODES_CONNECTED[0]],
            threshold_direct_links=threshold_direct_links,
            binary_indexes=["IIC", self.index_code],
            only_overall=inputs[self.INPUT_CREATE_NODE_IMPORTANCES[0]],
            write_links_file=inputs[self.INPUT_WRITE_LINKS_FILE[0]],
            prefix="_".join((
                inputs[self.INPUT_NODES_FILE_PATH[0]].stem,
                self.index_code,
                threshold_direct_links
            ))
        )
#
#
# class ConeforProbabilityIndexBase(ConeforProcessorBase):
#
#     def defineCharacteristics(self):
#         ConeforProcessorBase.defineCharacteristics(self)
#
#     def _create_parameters(self):
#         parameters = ConeforProcessorBase._create_parameters(self)
#         parameters += [
#             ParameterBoolean(self.CREATE_NODE_IMPORTANCES, 'Process ' \
#                              'individual node importances', default=False),
#             ParameterBoolean(self.WRITE_PROB_DIR, 'Write file with direct ' \
#                              'dispersal probabilities for each pair of nodes',
#                              default=False),
#             ParameterBoolean(self.REMOVAL, 'Process link removal importances '
#                              '(-removal)', default=False),
#             ParameterNumber(self.REMOVAL_DISTANCE, 'Maximum threshold for '
#                             'link removal analysis'),
#             ParameterBoolean(self.IMPROVEMENT, 'Process link improvement '
#                              'importances (-improvement)', default=False),
#             ParameterNumber(self.IMPROVEMENT_DISTANCE, 'Maximum threshold '
#                             'for link improvement analysis'),
#         ]
#         return parameters
#
#
# class ConeforFDistanceProcessor(ConeforProbabilityIndexBase):
#     GROUP = 'Probability indices (distance based)'
#     INDEX_NAME = 'Flux'
#     INDEX_CODE = 'F'
#     NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
#     _connection_type = 'dist'
#
#     def defineCharacteristics(self):
#         ConeforProbabilityIndexBase.defineCharacteristics(self)
#         parameters = self._create_parameters()
#         self._add_parameters(parameters)
#
#     def _create_parameters(self):
#         parameters = ConeforProbabilityIndexBase._create_parameters(self)
#         parameters += [
#             ParameterNumber(self.DISTANCE_PROB, 'Distance to match with ' \
#                             'probability (confProb distance)'),
#             ParameterNumber(self.PROBABILITY_PROB, 'Probability to match ' \
#                             'with distance (confProb probability)'),
#         ]
#         return parameters
#
#     def _run_the_algorithm(self, conefor_path, nodes_file_path,
#                            connections_file_path, all_connections,
#                            prefix, progress):
#         distance_prob = self.getParameterValue(self.DISTANCE_PROB)
#         prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
#         write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
#         only_overall = True
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
#         if removal_threshold <= 0:
#             removal_threshold = None
#         improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
#         if improv_threshold <= 0:
#             improv_threshold = None
#         prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
#         returncode, stdout, stderr = self._run_conefor(
#             progress,
#             conefor_path,
#             nodes_file_path,
#             connections_file_path,
#             self._connection_type,
#             all_connections,
#             decay_distance=distance_prob,
#             decay_probability=prob_prob,
#             probability_indexes=[self.INDEX_CODE],
#             only_overall=only_overall,
#             removal=self.getParameterValue(self.REMOVAL),
#             removal_threshold=removal_threshold,
#             improvement=self.getParameterValue(self.IMPROVEMENT),
#             improvement_threshold=improv_threshold,
#             write_dispersal_probabilities_file=write_prob_dir,
#             prefix=prefix
#         )
#         return returncode, stdout, stderr
#
#
# class ConeforFProbabilityProcessor(ConeforProbabilityIndexBase):
#     GROUP = 'Probability indices (probability based)'
#     INDEX_NAME = 'Flux'
#     INDEX_CODE = 'F'
#     NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
#     _connection_type = 'prob'
#
#     def defineCharacteristics(self):
#         ConeforProbabilityIndexBase.defineCharacteristics(self)
#         parameters = self._create_parameters()
#         self._add_parameters(parameters)
#
#     def _run_the_algorithm(self, conefor_path, nodes_file_path,
#                            connections_file_path, all_connections,
#                            prefix, progress):
#         write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
#         only_overall = True
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
#         if removal_threshold <= 0:
#             removal_threshold = None
#         improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
#         if improv_threshold <= 0:
#             improv_threshold = None
#         prefix +='_%s' % self.INDEX_CODE
#         returncode, stdout, stderr = self._run_conefor(
#             progress,
#             conefor_path,
#             nodes_file_path,
#             connections_file_path,
#             self._connection_type,
#             all_connections,
#             probability_indexes=[self.INDEX_CODE],
#             only_overall=only_overall,
#             removal=self.getParameterValue(self.REMOVAL),
#             removal_threshold=removal_threshold,
#             improvement=self.getParameterValue(self.IMPROVEMENT),
#             improvement_threshold=improv_threshold,
#             write_dispersal_probabilities_file=write_prob_dir,
#             prefix=prefix
#         )
#         return returncode, stdout, stderr
#
#
# class ConeforAWFDistanceProcessor(ConeforProbabilityIndexBase):
#     GROUP = 'Probability indices (distance based)'
#     INDEX_NAME = 'Area-weighted Flux'
#     INDEX_CODE = 'AWF'
#     NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
#     _connection_type = 'dist'
#
#     def defineCharacteristics(self):
#         ConeforProbabilityIndexBase.defineCharacteristics(self)
#         parameters = self._create_parameters()
#         self._add_parameters(parameters)
#
#     def _create_parameters(self):
#         parameters = ConeforProbabilityIndexBase._create_parameters(self)
#         parameters += [
#             ParameterNumber(self.DISTANCE_PROB, 'Distance to match with ' \
#                             'probability (confProb distance)'),
#             ParameterNumber(self.PROBABILITY_PROB, 'Probability to match ' \
#                             'with distance (confProb probability)'),
#         ]
#         return parameters
#
#     def _run_the_algorithm(self, conefor_path, nodes_file_path,
#                            connections_file_path, all_connections,
#                            prefix, progress):
#         distance_prob = self.getParameterValue(self.DISTANCE_PROB)
#         prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
#         write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
#         only_overall = True
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
#         if removal_threshold <= 0:
#             removal_threshold = None
#         improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
#         if improv_threshold <= 0:
#             improv_threshold = None
#         prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
#         returncode, stdout, stderr = self._run_conefor(
#             progress,
#             conefor_path,
#             nodes_file_path,
#             connections_file_path,
#             self._connection_type,
#             all_connections,
#             decay_distance=distance_prob,
#             decay_probability=prob_prob,
#             probability_indexes=[self.INDEX_CODE],
#             only_overall=only_overall,
#             removal=self.getParameterValue(self.REMOVAL),
#             removal_threshold=removal_threshold,
#             improvement=self.getParameterValue(self.IMPROVEMENT),
#             improvement_threshold=improv_threshold,
#             write_dispersal_probabilities_file=write_prob_dir,
#             prefix=prefix
#         )
#         return returncode, stdout, stderr
#
#
# class ConeforAWFProbabilityProcessor(ConeforProbabilityIndexBase):
#     GROUP = 'Probability indices (probability based)'
#     INDEX_NAME = 'Area-weighted Flux'
#     INDEX_CODE = 'AWF'
#     NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
#     _connection_type = 'prob'
#
#     def defineCharacteristics(self):
#         ConeforProbabilityIndexBase.defineCharacteristics(self)
#         parameters = self._create_parameters()
#         self._add_parameters(parameters)
#
#     def _run_the_algorithm(self, conefor_path, nodes_file_path,
#                            connections_file_path, all_connections,
#                            prefix, progress):
#         write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
#         only_overall = True
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
#         if removal_threshold <= 0:
#             removal_threshold = None
#         improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
#         if improv_threshold <= 0:
#             improv_threshold = None
#         prefix +='_%s' % self.INDEX_CODE
#         returncode, stdout, stderr = self._run_conefor(
#             progress,
#             conefor_path,
#             nodes_file_path,
#             connections_file_path,
#             self._connection_type,
#             all_connections,
#             probability_indexes=[self.INDEX_CODE],
#             only_overall=only_overall,
#             removal=self.getParameterValue(self.REMOVAL),
#             removal_threshold=removal_threshold,
#             improvement=self.getParameterValue(self.IMPROVEMENT),
#             improvement_threshold=improv_threshold,
#             write_dispersal_probabilities_file=write_prob_dir,
#             prefix=prefix
#         )
#         return returncode, stdout, stderr
#
#
# class ConeforPCDistanceProcessor(ConeforProbabilityIndexBase):
#     GROUP = 'Probability indices (distance based)'
#     INDEX_NAME = 'Probability of Connectivity'
#     INDEX_CODE = 'PC'
#     NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
#     _connection_type = 'dist'
#
#     def defineCharacteristics(self):
#         ConeforProbabilityIndexBase.defineCharacteristics(self)
#         parameters = self._create_parameters()
#         self._add_parameters(parameters)
#
#     def _create_parameters(self):
#         parameters = ConeforProbabilityIndexBase._create_parameters(self)
#         parameters += [
#             ParameterNumber(self.DISTANCE_PROB, 'Distance to match with ' \
#                             'probability (confProb distance)'),
#             ParameterNumber(self.PROBABILITY_PROB, 'Probability to match ' \
#                             'with distance (confProb probability)'),
#             ParameterBoolean(self.WRITE_PROB_MAX, 'Write file with maximum ' \
#                              'product probabilities for each pair of nodes',
#                              default=False),
#         ]
#         return parameters
#
#     def _run_the_algorithm(self, conefor_path, nodes_file_path,
#                            connections_file_path, all_connections,
#                            prefix, progress):
#         distance_prob = self.getParameterValue(self.DISTANCE_PROB)
#         prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
#         write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
#         write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
#         only_overall = True
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
#         if removal_threshold <= 0:
#             removal_threshold = None
#         improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
#         if improv_threshold <= 0:
#             improv_threshold = None
#         prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
#         returncode, stdout, stderr = self._run_conefor(
#             progress,
#             conefor_path,
#             nodes_file_path,
#             connections_file_path,
#             self._connection_type,
#             all_connections,
#             decay_distance=distance_prob,
#             decay_probability=prob_prob,
#             probability_indexes=[self.INDEX_CODE],
#             only_overall=only_overall,
#             removal=self.getParameterValue(self.REMOVAL),
#             removal_threshold=removal_threshold,
#             improvement=self.getParameterValue(self.IMPROVEMENT),
#             improvement_threshold=improv_threshold,
#             write_dispersal_probabilities_file=write_prob_dir,
#             write_maximum_probabilities_file=write_prob_max,
#             prefix=prefix
#         )
#         return returncode, stdout, stderr
#
#
# class ConeforPCProbabilityProcessor(ConeforProbabilityIndexBase):
#     GROUP = 'Probability indices (probability based)'
#     INDEX_NAME = 'Probability of Connectivity'
#     INDEX_CODE = 'PC'
#     NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
#     _connection_type = 'prob'
#
#     def defineCharacteristics(self):
#         ConeforProbabilityIndexBase.defineCharacteristics(self)
#         parameters = self._create_parameters()
#         self._add_parameters(parameters)
#
#     def _create_parameters(self):
#         parameters = ConeforProbabilityIndexBase._create_parameters(self)
#         parameters += [
#             ParameterBoolean(self.WRITE_PROB_MAX, 'Write file with maximum ' \
#                              'product probabilities for each pair of nodes',
#                              default=False),
#         ]
#         return parameters
#
#     def _run_the_algorithm(self, conefor_path, nodes_file_path,
#                            connections_file_path, all_connections,
#                            prefix, progress):
#         write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
#         write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
#         only_overall = True
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
#         if removal_threshold <= 0:
#             removal_threshold = None
#         improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
#         if improv_threshold <= 0:
#             improv_threshold = None
#         prefix +='_%s' % self.INDEX_CODE
#         returncode, stdout, stderr = self._run_conefor(
#             progress,
#             conefor_path,
#             nodes_file_path,
#             connections_file_path,
#             self._connection_type,
#             all_connections,
#             probability_indexes=[self.INDEX_CODE],
#             only_overall=only_overall,
#             removal=self.getParameterValue(self.REMOVAL),
#             removal_threshold=removal_threshold,
#             improvement=self.getParameterValue(self.IMPROVEMENT),
#             improvement_threshold=improv_threshold,
#             write_dispersal_probabilities_file=write_prob_dir,
#             write_maximum_probabilities_file=write_prob_max,
#             prefix=prefix
#         )
#         return returncode, stdout, stderr
#
#
# class ConeforBCPCDistanceProcessor(ConeforProcessorBase):
#     GROUP = 'Probability indices (distance based)'
#     INDEX_NAME = 'Betweeness Centrality Generalized(PC)'
#     INDEX_CODE = 'BCPC'
#     NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
#     _connection_type = 'dist'
#
#     def defineCharacteristics(self):
#         ConeforProcessorBase.defineCharacteristics(self)
#         parameters = self._create_parameters()
#         self._add_parameters(parameters)
#
#     def _create_parameters(self):
#         parameters = ConeforProcessorBase._create_parameters(self)
#         parameters += [
#             ParameterNumber(self.THRESHOLD_DIRECT_LINKS, '(BC) Threshold ' \
#                             '(distance/probability) for connecting nodes ' \
#                             '(confAdj)'),
#             ParameterBoolean(self.WRITE_LINKS_FILE, '(BC) Write links file',
#                              default=False),
#             ParameterBoolean(self.CREATE_NODE_IMPORTANCES, 'Process ' \
#                              'individual node importances', default=False),
#             ParameterNumber(self.DISTANCE_PROB, 'Distance to match with ' \
#                             'probability (confProb distance)'),
#             ParameterNumber(self.PROBABILITY_PROB, 'Probability to match ' \
#                             'with distance (confProb probability)'),
#             ParameterBoolean(self.WRITE_PROB_DIR, 'Write file with direct ' \
#                              'dispersal probabilities for each pair of nodes',
#                              default=False),
#             ParameterBoolean(self.WRITE_PROB_MAX, 'Write file with maximum ' \
#                              'product probabilities for each pair of nodes',
#                              default=False),
#         ]
#         return parameters
#
#     def _run_the_algorithm(self, conefor_path, nodes_file_path,
#                            connections_file_path, all_connections,
#                            prefix, progress):
#         distance_prob = self.getParameterValue(self.DISTANCE_PROB)
#         prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
#         write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
#         write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
#         thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
#         only_overall = True
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
#         returncode, stdout, stderr = self._run_conefor(
#             progress,
#             conefor_path,
#             nodes_file_path,
#             connections_file_path,
#             self._connection_type,
#             all_connections,
#             threshold_direct_links=thresh_d_links,
#             binary_indexes=['BC'],
#             decay_distance=distance_prob,
#             decay_probability=prob_prob,
#             probability_indexes=['PC', self.INDEX_CODE],
#             only_overall=only_overall,
#             write_dispersal_probabilities_file=write_prob_dir,
#             write_maximum_probabilities_file=write_prob_max,
#             prefix=prefix
#         )
#         return returncode, stdout, stderr
#
#
# class ConeforBCPCProbabilityProcessor(ConeforProcessorBase):
#     GROUP = 'Probability indices (probability based)'
#     INDEX_NAME = 'Betweeness Centrality Generalized(PC)'
#     INDEX_CODE = 'BCPC'
#     NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
#     _connection_type = 'prob'
#
#     def defineCharacteristics(self):
#         ConeforProcessorBase.defineCharacteristics(self)
#         parameters = self._create_parameters()
#         self._add_parameters(parameters)
#
#     def _create_parameters(self):
#         parameters = ConeforProcessorBase._create_parameters(self)
#         parameters += [
#             ParameterNumber(self.THRESHOLD_DIRECT_LINKS, '(BC) Threshold ' \
#                             '(distance/probability) for connecting nodes ' \
#                             '(confAdj)'),
#             ParameterBoolean(self.WRITE_LINKS_FILE, '(BC) Write links file',
#                              default=False),
#             ParameterBoolean(self.CREATE_NODE_IMPORTANCES, 'Process ' \
#                              'individual node importances', default=False),
#             ParameterBoolean(self.WRITE_PROB_DIR, 'Write file with direct ' \
#                              'dispersal probabilities for each pair of nodes',
#                              default=False),
#             ParameterBoolean(self.WRITE_PROB_MAX, 'Write file with maximum ' \
#                              'product probabilities for each pair of nodes',
#                              default=False),
#         ]
#         return parameters
#
#     def _run_the_algorithm(self, conefor_path, nodes_file_path,
#                            connections_file_path, all_connections,
#                            prefix, progress):
#         write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
#         write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
#         thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
#         only_overall = True
#         if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
#             only_overall = False
#         prefix +='_%s' % self.INDEX_CODE
#         returncode, stdout, stderr = self._run_conefor(
#             progress,
#             conefor_path,
#             nodes_file_path,
#             connections_file_path,
#             self._connection_type,
#             all_connections,
#             threshold_direct_links=thresh_d_links,
#             binary_indexes=['BC'],
#             probability_indexes=['PC', self.INDEX_CODE],
#             only_overall=only_overall,
#             write_dispersal_probabilities_file=write_prob_dir,
#             write_maximum_probabilities_file=write_prob_max,
#             prefix=prefix
#         )
#         return returncode, stdout, stderr
