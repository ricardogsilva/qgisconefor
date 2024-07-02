import os
import shutil
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT

import qgis.core
from qgis.PyQt import QtGui

from processing.core.ProcessingConfig import ProcessingConfig
from processing.core.ProcessingResults import ProcessingResults

from ... import utilities
from ...schemas import (
    ConeforProcessingSetting,
    ICON_RESOURCE_PATH,
    QgisConeforSettingsKey,
)
from . import base

class ConeforProcessorBase(base.Base):
    """Base class for Conefor processing (don't instantiate it directly)."""

    _connection_types = ["dist", "prob"]  # links is not supported atm
    _precision = "double"

    NAME = ""
    GROUP = ""

    INPUT_NODES_FILE_PATH = ("nodes_file_path", "Conefor nodes file path")
    INPUT_CONNECTIONS_FILE_PATH = ("connections_file_path", "Conefor connections file path")
    INPUT_CONNECTION_TYPE = "INPUT_CONNECTION_TYPE"
    INPUT_NUMBER_OF_CONNECTIONS = ("number_of_connections", "Whether all nodes are connected")
    THRESHOLD_DIRECT_LINKS = "THRESHOLD_DIRECT_LINKS"
    DISTANCE_PROB = "DISTANCE_PROB"
    PROBABILITY_PROB = "PROBABILITY_PROB"
    CREATE_NODE_IMPORTANCES = "CREATE_NODE_IMPORTANCES"
    REMOVAL = "REMOVAL"
    REMOVAL_DISTANCE = "REMOVAL_DISTANCE"
    IMPROVEMENT = "IMPROVEMENT"
    IMPROVEMENT_DISTANCE = "IMPROVEMENT_DISTANCE"
    WRITE_COMPONENT_FILE = "WRITE_COMPONENT_FILE"
    WRITE_LINKS_FILE = "WRITE_LINKS_FILE"
    WRITE_PROB_DIR = "WRITE_PROB_DIR"
    WRITE_PROB_MAX = "WRITE_PROB_MAX"
    INPUT_OUTPUT_DIRECTORY = (
        "output_directory", "Output directory for generated Conefor analysis files")

    _parameter_order = [
        INPUT_NODES_FILE_PATH[0],
        INPUT_CONNECTIONS_FILE_PATH[0],
        INPUT_CONNECTION_TYPE,
        INPUT_NUMBER_OF_CONNECTIONS[0],
        # -* option is not used by this plugin
        THRESHOLD_DIRECT_LINKS,
        # binary_indices are not selectable in the GUI
        DISTANCE_PROB,
        PROBABILITY_PROB,
        # probability indices are not selectable in the GUI
        CREATE_NODE_IMPORTANCES,
        # pcHeur is not implemented, yet
        # -add is not implemented, yet
        REMOVAL,
        REMOVAL_DISTANCE,
        IMPROVEMENT,
        IMPROVEMENT_DISTANCE,
        # -change is not implemented in this plugin
        # self._precision is not exposed in the GUI
        # -noout is not used by this plugin
        WRITE_COMPONENT_FILE,
        WRITE_LINKS_FILE,
        WRITE_PROB_DIR,
        WRITE_PROB_MAX,
        # -landArea is not implemented, yet
        # prefix is not exposed in the GUI
        INPUT_OUTPUT_DIRECTORY[0],
    ]

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
                extension=".txt"
            ),
            qgis.core.QgsProcessingParameterFile(
                name=self.INPUT_CONNECTIONS_FILE_PATH[0],
                description=self.tr(self.INPUT_CONNECTIONS_FILE_PATH[1]),
                extension=".txt"
            ),
            qgis.core.QgsProcessingParameterBoolean(
                self.INPUT_NUMBER_OF_CONNECTIONS[0],
                self.tr(self.INPUT_NUMBER_OF_CONNECTIONS[1]),
                defaultValue=True
            ),
        ]

    def checkBeforeOpeningParametersDialog(self):
        return self._problems_to_run()

    def processAlgorithm(self, progress):
        problems = self._problems_to_run()
        if problems is None:
            conefor_path = Path(
                ProcessingConfig.getSetting(ConeforProcessingSetting.CONEFOR_CLI_PATH))
            conefor_dir = conefor_path.parent
            before = os.listdir(conefor_dir)
            nodes = self.getParameterValue(self.INPUT_NODES_FILE_PATH[0])
            connections = self.getParameterValue(self.INPUT_CONNECTIONS_FILE_PATH[0])
            all_conn = self.getParameterValue(self.INPUT_NUMBER_OF_CONNECTIONS[0])
            prefix = os.path.splitext(os.path.basename(nodes))[0]
            rc, stdout, stderr = self._run_the_algorithm(
                conefor_path,
                nodes,
                connections,
                all_conn,
                prefix,
                progress
            )
            after = os.listdir(conefor_dir)
            new_files = [os.path.join(conefor_dir, f) for f in after if \
                            f not in before]
            output_dir = self.getParameterValue(self.INPUT_OUTPUT_DIRECTORY)
            result_files = self._merge_results(output_dir, new_files)
            for new_file in result_files:
                name = os.path.basename(new_file)
                ProcessingResults.addResult(name, new_file)
            progress.setPercentage(100)
        else:
            raise qgis.core.QgsProcessingException(problems)

    def icon(self):
        return QtGui.QIcon(ICON_RESOURCE_PATH)

    def help(self):
        return False, 'http://hub.qgis.org/projects/qgisconefor'

    def _add_parameters(self, parameters):
        index_params = []
        for p in parameters:
            try:
                index = self._parameter_order.index(p.name)
                index_params.append((index, p))
            except ValueError:
                pass
        ordered_params = sorted(index_params, key=lambda tup: tup[0])
        for order, param in ordered_params:
            self.addParameter(param)

    def _merge_results(self, intended_output_dir, new_output_files):
        overall_results_file_name = 'results_all_overall_indices.txt'
        ec_iic_results_file_name = 'results_all_EC(IIC).txt'
        ec_pc_results_file_name = 'results_all_EC(PC).txt'
        new_results = []
        for f in new_output_files:
            f_name = os.path.basename(f)
            if f_name == overall_results_file_name:
                new_p = self._merge_overall_results(intended_output_dir, f)
                new_results.append(new_p)
            elif f_name in (ec_iic_results_file_name, ec_pc_results_file_name):
                new_p = self._merge_special_files_results(intended_output_dir,
                                                          f)
                new_results.append(new_p)
            else:
                new_p = self._merge_other_results(intended_output_dir, f)
                new_results.append(new_p)
        return new_results

    def _merge_overall_results(self, intended_output_dir, file_path):
        f_name = os.path.basename(file_path)
        if f_name in os.listdir(intended_output_dir):
            #print('the file is already present in %s' % intended_output_dir)
            #print('Appending %s to previous existing overal results file ' \
            #      'in %s ...' % (f_name, intended_output_dir))
            f_contents = utilities.extract_contents(file_path)
            #print('removing original %s ...' % f_name)
            os.remove(file_path)
            with open(os.path.join(intended_output_dir, f_name), 'a') as fh:
                for line in f_contents:
                    fh.write(line)
        else:
            # The BC index generates an empty file and in that case
            # we do not move it over
            num_lines = 0
            with open(file_path) as fh:
                for line in fh:
                    num_lines += 1
            if num_lines == 0:
                #print('the file is empty. Removing...')
                os.remove(file_path)
            else:
                #print('Moving %s to %s ...' % (f_name, intended_output_dir))
                shutil.move(file_path, intended_output_dir)
        return os.path.join(intended_output_dir, f_name)

    def _merge_special_files_results(self, intended_output_dir, file_path):
        f_name = os.path.basename(file_path)
        if f_name in os.listdir(intended_output_dir):
            #print('the file is already present in %s' % intended_output_dir)
            #print('Appending %s to previous existing overal results file ' \
            #      'in %s ...' % (f_name, intended_output_dir))
            f_contents = utilities.extract_contents(file_path)
            #print('removing original %s ...' % f_name)
            os.remove(file_path)
            with open(os.path.join(intended_output_dir, f_name), 'a') as fh:
                for line in f_contents:
                    fh.write(line)
        else:
            #print('Moving %s to %s ...' % (f_name, intended_output_dir))
            shutil.move(file_path, intended_output_dir)
        return os.path.join(intended_output_dir, f_name)

    def _merge_other_results(self, intended_output_dir, file_path):
        f_name = os.path.basename(file_path)
        #print('Moving %s to %s ...' % (f_name, intended_output_dir))
        if os.path.isfile(os.path.join(intended_output_dir, f_name)):
            #print('%s is already present in %s. Deleting it before moving ' \
            #      'the new file...' % (f_name, intended_output_dir))
            os.remove(os.path.join(intended_output_dir, f_name))
        shutil.move(file_path, intended_output_dir)
        return os.path.join(intended_output_dir, f_name)

    def _run_conefor(
        self,
        progress,
        conefor_path: Path,
        nodes_file_path,
        connections_file_path,
        connection_type,
        all_pairs_connected,
        threshold_direct_links=0,
        binary_indexes=[],
        decay_distance=0,
        decay_probability=0,
        probability_indexes=[],
        only_overall=False,
        removal=False,
        removal_threshold=None,
        improvement=False,
        improvement_threshold=None,
        write_component_file=False,
        write_links_file=False,
        write_dispersal_probabilities_file=False,
        write_maximum_probabilities_file=False,
        land_area=None,
        prefix=None
    ):
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
            '-nodeFile', nodes_file_path,
            '-conFile', connections_file_path,
            '-t', connection_type,
        ]
        if all_pairs_connected:
            command_list.append('all')
        else:
            command_list.append('notall')
        if any(binary_indexes):
            command_list += ['-confAdj', '%1.3f' % threshold_direct_links]
            if 'BCIIC' in binary_indexes and 'IIC' not in binary_indexes:
                binary_indexes.append('IIC')
            if 'BCIIC' in binary_indexes and 'BC' not in binary_indexes:
                binary_indexes.append('BC')
            for index in binary_indexes:
                command_list.append('-%s' % index)
        if any(probability_indexes):
            if connection_type == 'dist':
                command_list += ['-confProb', '%1.3f' % decay_distance, 
                                '%1.3f' % decay_probability]
            elif connection_type == 'prob':
                pass
            if 'BCPC' in probability_indexes and \
                    'PC' not in probability_indexes:
                probability_indexes.append('PC')
            if 'BCPC' in probability_indexes and \
                    'BC' not in binary_indexes:
                binary_indexes.append('BC')
            for index in probability_indexes:
                command_list.append('-%s' % index)
        if only_overall:
            command_list.append('onlyoverall')
        if removal:
            command_list.append('-removal')
            if removal_threshold is not None:
                command_list += ['maxValue', '%s' % removal_threshold]
        if improvement:
            command_list.append('-improvement')
            if improvement_threshold is not None:
                command_list += ['maxValue', '%s' % improvement_threshold]
        command_list.append('-%s' % self._precision)
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
        utilities.log(" ".join(command_list))
        process = Popen(command_list, cwd=conefor_dir, stdout=PIPE,
                        stderr=STDOUT)
        while True:
            line = process.stdout.readline()
            if line != '':
                progress.setText(line)
            else:
                break
        return process.returncode, None, None  # change this

    def _run_the_algorithm(
        self,
        conefor_path,
        nodes_file_path,
        connections_file_path,
        all_connections, prefix,
        progress
    ):
        raise NotImplementedError

    def _problems_to_run(self):
        result = None
        conefor_path = ProcessingConfig.getSetting(
            ConeforProcessingSetting.CONEFOR_CLI_PATH.name)
        if not Path(conefor_path).exists():
            result = (
                "Couldn't find the Conefor executable. Set its correct path in "
                "QGIS settings -> Processing -> Providers -> Conefor"
            )
        return result


class ConeforBinaryIndexBase(ConeforProcessorBase):

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)

    def _create_parameters(self):
        parameters = ConeforProcessorBase._create_parameters(self)
        parameters += [
            ParameterSelection(self.INPUT_CONNECTION_TYPE, 'Connection type',
                               self._connection_types),
            ParameterNumber(self.THRESHOLD_DIRECT_LINKS, 'Threshold '
                            '(distance/probability) for connecting nodes '
                            '(confAdj)'),
            ParameterBoolean(self.CREATE_NODE_IMPORTANCES, 'Process '
                             'individual node importances', default=False),
            ParameterBoolean(self.WRITE_LINKS_FILE, 'Write links file',
                             default=False),
            ParameterBoolean(self.REMOVAL, 'Process link removal importances '
                             '(-removal)', default=False),
            ParameterNumber(self.REMOVAL_DISTANCE, 'Maximum threshold for '
                            'link removal analysis'),
            ParameterBoolean(self.IMPROVEMENT, 'Process link improvement '
                             'importances (-improvement)', default=False),
            ParameterNumber(self.IMPROVEMENT_DISTANCE, 'Maximum threshold '
                            'for link improvement analysis'),
        ]
        return parameters


class ConeforNCProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Number of Components'
    INDEX_CODE = 'NC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def defineCharacteristics(self):
        ConeforBinaryIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _create_parameters(self):
        parameters = ConeforBinaryIndexBase._create_parameters(self)
        parameters += [
            ParameterBoolean(self.WRITE_COMPONENT_FILE, 'Write components '
                             'file', default=False),
        ]
        return parameters

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_component_file=self.getParameterValue(self.WRITE_COMPONENT_FILE),
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforNLProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Number of Links'
    INDEX_CODE = 'NL'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def defineCharacteristics(self):
        ConeforBinaryIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforHProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Harary'
    INDEX_CODE = 'H'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def defineCharacteristics(self):
        ConeforBinaryIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforCCPProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Class Coincidence Probability'
    INDEX_CODE = 'CCP'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def defineCharacteristics(self):
        ConeforBinaryIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforLCPProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Landscape Coincidence Probability'
    INDEX_CODE = 'LCP'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def defineCharacteristics(self):
        ConeforBinaryIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforIICProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Integral Index of Connectivity'
    INDEX_CODE = 'IIC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def defineCharacteristics(self):
        ConeforBinaryIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_component_file=self.getParameterValue(self.WRITE_COMPONENT_FILE),
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforBCProcessor(ConeforProcessorBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Betweeness Centrality (Classic)'
    INDEX_CODE = 'BC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _create_parameters(self):
        parameters = ConeforProcessorBase._create_parameters(self)
        parameters += [
            ParameterSelection(self.INPUT_CONNECTION_TYPE, 'Connection type',
                               self._connection_types),
            ParameterNumber(self.THRESHOLD_DIRECT_LINKS, 'Threshold ' \
                            '(distance/probability) for connecting nodes ' \
                            '(confAdj)'),
            ParameterBoolean(self.WRITE_LINKS_FILE, 'Write links file',
                             default=False),
        ]
        return parameters

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=False,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforBCIICProcessor(ConeforBCProcessor):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Betweeness Centrality Generalized(IIC)'
    INDEX_CODE = 'BCIIC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=['IIC', self.INDEX_CODE],
            only_overall=False,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforProbabilityIndexBase(ConeforProcessorBase):

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)

    def _create_parameters(self):
        parameters = ConeforProcessorBase._create_parameters(self)
        parameters += [
            ParameterBoolean(self.CREATE_NODE_IMPORTANCES, 'Process ' \
                             'individual node importances', default=False),
            ParameterBoolean(self.WRITE_PROB_DIR, 'Write file with direct ' \
                             'dispersal probabilities for each pair of nodes',
                             default=False),
            ParameterBoolean(self.REMOVAL, 'Process link removal importances '
                             '(-removal)', default=False),
            ParameterNumber(self.REMOVAL_DISTANCE, 'Maximum threshold for '
                            'link removal analysis'),
            ParameterBoolean(self.IMPROVEMENT, 'Process link improvement '
                             'importances (-improvement)', default=False),
            ParameterNumber(self.IMPROVEMENT_DISTANCE, 'Maximum threshold '
                            'for link improvement analysis'),
        ]
        return parameters


class ConeforFDistanceProcessor(ConeforProbabilityIndexBase):
    GROUP = 'Probability indices (distance based)'
    INDEX_NAME = 'Flux'
    INDEX_CODE = 'F'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    _connection_type = 'dist'

    def defineCharacteristics(self):
        ConeforProbabilityIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)
 
    def _create_parameters(self):
        parameters = ConeforProbabilityIndexBase._create_parameters(self)
        parameters += [
            ParameterNumber(self.DISTANCE_PROB, 'Distance to match with ' \
                            'probability (confProb distance)'),
            ParameterNumber(self.PROBABILITY_PROB, 'Probability to match ' \
                            'with distance (confProb probability)'),
        ]
        return parameters

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        distance_prob = self.getParameterValue(self.DISTANCE_PROB)
        prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            all_connections,
            decay_distance=distance_prob,
            decay_probability=prob_prob,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_dispersal_probabilities_file=write_prob_dir,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforFProbabilityProcessor(ConeforProbabilityIndexBase):
    GROUP = 'Probability indices (probability based)'
    INDEX_NAME = 'Flux'
    INDEX_CODE = 'F'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    _connection_type = 'prob'

    def defineCharacteristics(self):
        ConeforProbabilityIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        prefix +='_%s' % self.INDEX_CODE
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            all_connections,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_dispersal_probabilities_file=write_prob_dir,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforAWFDistanceProcessor(ConeforProbabilityIndexBase):
    GROUP = 'Probability indices (distance based)'
    INDEX_NAME = 'Area-weighted Flux'
    INDEX_CODE = 'AWF'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    _connection_type = 'dist'

    def defineCharacteristics(self):
        ConeforProbabilityIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _create_parameters(self):
        parameters = ConeforProbabilityIndexBase._create_parameters(self)
        parameters += [
            ParameterNumber(self.DISTANCE_PROB, 'Distance to match with ' \
                            'probability (confProb distance)'),
            ParameterNumber(self.PROBABILITY_PROB, 'Probability to match ' \
                            'with distance (confProb probability)'),
        ]
        return parameters

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        distance_prob = self.getParameterValue(self.DISTANCE_PROB)
        prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            all_connections,
            decay_distance=distance_prob,
            decay_probability=prob_prob,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_dispersal_probabilities_file=write_prob_dir,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforAWFProbabilityProcessor(ConeforProbabilityIndexBase):
    GROUP = 'Probability indices (probability based)'
    INDEX_NAME = 'Area-weighted Flux'
    INDEX_CODE = 'AWF'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    _connection_type = 'prob'

    def defineCharacteristics(self):
        ConeforProbabilityIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        prefix +='_%s' % self.INDEX_CODE
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            all_connections,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_dispersal_probabilities_file=write_prob_dir,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforPCDistanceProcessor(ConeforProbabilityIndexBase):
    GROUP = 'Probability indices (distance based)'
    INDEX_NAME = 'Probability of Connectivity'
    INDEX_CODE = 'PC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    _connection_type = 'dist'

    def defineCharacteristics(self):
        ConeforProbabilityIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _create_parameters(self):
        parameters = ConeforProbabilityIndexBase._create_parameters(self)
        parameters += [
            ParameterNumber(self.DISTANCE_PROB, 'Distance to match with ' \
                            'probability (confProb distance)'),
            ParameterNumber(self.PROBABILITY_PROB, 'Probability to match ' \
                            'with distance (confProb probability)'),
            ParameterBoolean(self.WRITE_PROB_MAX, 'Write file with maximum ' \
                             'product probabilities for each pair of nodes',
                             default=False),
        ]
        return parameters

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        distance_prob = self.getParameterValue(self.DISTANCE_PROB)
        prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            all_connections,
            decay_distance=distance_prob,
            decay_probability=prob_prob,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_dispersal_probabilities_file=write_prob_dir,
            write_maximum_probabilities_file=write_prob_max,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforPCProbabilityProcessor(ConeforProbabilityIndexBase):
    GROUP = 'Probability indices (probability based)'
    INDEX_NAME = 'Probability of Connectivity'
    INDEX_CODE = 'PC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    _connection_type = 'prob'

    def defineCharacteristics(self):
        ConeforProbabilityIndexBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _create_parameters(self):
        parameters = ConeforProbabilityIndexBase._create_parameters(self)
        parameters += [
            ParameterBoolean(self.WRITE_PROB_MAX, 'Write file with maximum ' \
                             'product probabilities for each pair of nodes',
                             default=False),
        ]
        return parameters

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        removal_threshold = self.getParameterValue(self.REMOVAL_DISTANCE)
        if removal_threshold <= 0:
            removal_threshold = None
        improv_threshold = self.getParameterValue(self.IMPROVEMENT_DISTANCE)
        if improv_threshold <= 0:
            improv_threshold = None
        prefix +='_%s' % self.INDEX_CODE
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            all_connections,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            removal=self.getParameterValue(self.REMOVAL),
            removal_threshold=removal_threshold,
            improvement=self.getParameterValue(self.IMPROVEMENT),
            improvement_threshold=improv_threshold,
            write_dispersal_probabilities_file=write_prob_dir,
            write_maximum_probabilities_file=write_prob_max,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforBCPCDistanceProcessor(ConeforProcessorBase):
    GROUP = 'Probability indices (distance based)'
    INDEX_NAME = 'Betweeness Centrality Generalized(PC)'
    INDEX_CODE = 'BCPC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    _connection_type = 'dist'

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _create_parameters(self):
        parameters = ConeforProcessorBase._create_parameters(self)
        parameters += [
            ParameterNumber(self.THRESHOLD_DIRECT_LINKS, '(BC) Threshold ' \
                            '(distance/probability) for connecting nodes ' \
                            '(confAdj)'),
            ParameterBoolean(self.WRITE_LINKS_FILE, '(BC) Write links file',
                             default=False),
            ParameterBoolean(self.CREATE_NODE_IMPORTANCES, 'Process ' \
                             'individual node importances', default=False),
            ParameterNumber(self.DISTANCE_PROB, 'Distance to match with ' \
                            'probability (confProb distance)'),
            ParameterNumber(self.PROBABILITY_PROB, 'Probability to match ' \
                            'with distance (confProb probability)'),
            ParameterBoolean(self.WRITE_PROB_DIR, 'Write file with direct ' \
                             'dispersal probabilities for each pair of nodes',
                             default=False),
            ParameterBoolean(self.WRITE_PROB_MAX, 'Write file with maximum ' \
                             'product probabilities for each pair of nodes',
                             default=False),
        ]
        return parameters

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        distance_prob = self.getParameterValue(self.DISTANCE_PROB)
        prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=['BC'],
            decay_distance=distance_prob,
            decay_probability=prob_prob,
            probability_indexes=['PC', self.INDEX_CODE],
            only_overall=only_overall,
            write_dispersal_probabilities_file=write_prob_dir,
            write_maximum_probabilities_file=write_prob_max,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforBCPCProbabilityProcessor(ConeforProcessorBase):
    GROUP = 'Probability indices (probability based)'
    INDEX_NAME = 'Betweeness Centrality Generalized(PC)'
    INDEX_CODE = 'BCPC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    _connection_type = 'prob'

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        parameters = self._create_parameters()
        self._add_parameters(parameters)

    def _create_parameters(self):
        parameters = ConeforProcessorBase._create_parameters(self)
        parameters += [
            ParameterNumber(self.THRESHOLD_DIRECT_LINKS, '(BC) Threshold ' \
                            '(distance/probability) for connecting nodes ' \
                            '(confAdj)'),
            ParameterBoolean(self.WRITE_LINKS_FILE, '(BC) Write links file',
                             default=False),
            ParameterBoolean(self.CREATE_NODE_IMPORTANCES, 'Process ' \
                             'individual node importances', default=False),
            ParameterBoolean(self.WRITE_PROB_DIR, 'Write file with direct ' \
                             'dispersal probabilities for each pair of nodes',
                             default=False),
            ParameterBoolean(self.WRITE_PROB_MAX, 'Write file with maximum ' \
                             'product probabilities for each pair of nodes',
                             default=False),
        ]
        return parameters

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, all_connections,
                           prefix, progress):
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        prefix +='_%s' % self.INDEX_CODE
        returncode, stdout, stderr = self._run_conefor(
            progress,
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            all_connections,
            threshold_direct_links=thresh_d_links,
            binary_indexes=['BC'],
            probability_indexes=['PC', self.INDEX_CODE],
            only_overall=only_overall,
            write_dispersal_probabilities_file=write_prob_dir,
            write_maximum_probabilities_file=write_prob_max,
            prefix=prefix
        )
        return returncode, stdout, stderr
