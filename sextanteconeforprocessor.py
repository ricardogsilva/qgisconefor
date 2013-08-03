import os
import shutil
from subprocess import Popen, PIPE

from PyQt4.QtGui import QIcon

from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.core.SextanteConfig import SextanteConfig
from sextante.core.SextanteUtils import SextanteUtils
from sextante.parameters.ParameterFile import ParameterFile
from sextante.parameters.ParameterBoolean import ParameterBoolean
from sextante.parameters.ParameterNumber import ParameterNumber
from sextante.parameters.ParameterSelection import ParameterSelection
from sextante.core.GeoAlgorithmExecutionException import \
    GeoAlgorithmExecutionException

class ConeforProcessorBase(GeoAlgorithm):
    NAME = 'Conefor test'
    GROUP = 'Conefor'
    INPUT_NODES_FILE = 'INPUT_NODES_FILE'
    INPUT_CONNECTIONS_FILE = 'INPUT_CONNECTIONS_FILE'
    INPUT_CONNECTION_TYPE = 'INPUT_CONNECTION_TYPE'
    OUTPUT_DIR = 'OUTPUT_DIR'
    _connection_types = ['dist', 'probability'] # links is not supported atm
    _number_of_connections = 'all'
    _precision = 'double'
    _conefor_probability_indexes = [
        ('F', 'Flux'),
        ('AWF', 'Area-weighted Flux'),
        ('PC', 'Probability of Connectivity'), # this is the recommended probability index
        'BCPC',
    ]

    def defineCharacteristics(self):
        self.name = self.NAME
        self.group = self.GROUP
        self.addParameter(ParameterFile(self.OUTPUT_DIR, 'output ' \
                          'directory for placing the results',
                          isFolder=True))
        self.addParameter(ParameterFile(self.INPUT_NODES_FILE,
                          'Nodes file', optional=False))
        self.addParameter(ParameterFile(self.INPUT_CONNECTIONS_FILE,
                          'Connections file', optional=False))

    def checkBeforeOpeningParametersDialog(self):
        return self._problems_to_run()

    def processAlgorithm(self, progress):
        problems = self._problems_to_run()
        if problems is None:
            try:
                conefor_path = SextanteConfig.getSetting(
                    self.provider.CONEFOR_EXECUTABLE_PATH)
                conefor_dir = os.path.dirname(conefor_path)
                before = os.listdir(conefor_dir)
                nodes = self.getParameterValue(self.INPUT_NODES_FILE)
                connections = self.getParameterValue(self.INPUT_CONNECTIONS_FILE)
                prefix = os.path.splitext(os.path.basename(nodes))[0]
                rc, stdout, stderr = self._run_the_algorithm(conefor_path,
                        nodes, connections, prefix)
                after = os.listdir(conefor_dir)
                new_files = [os.path.join(conefor_dir, f) for f in after if \
                             f not in before]
                print('new_files: %s' % new_files)
                # for now, the new files get moved to the inputs directory
                # in the future it would be nice to have a proper output directory
                output_dir = os.path.dirname(nodes)
                self._merge_results(output_dir, new_files)
                progress.setPercentage(100)
            except Exception as e:
                raise GeoAlgorithmExecutionException(e.message)
        else:
            raise GeoAlgorithmExecutionException(problems)

    def getIcon(self):
        return QIcon(':/plugins/conefor_dev/icon.png')

    def helpFile(self):
        return 'qrc:/plugins/conefor_dev/help.html'

    def _extract_results(self, file_path):
        '''
        Extract the results from input file_path.

        This method scans the file that came out of Conefor and returns the
        output.
        '''

        result = []
        with open(file_path) as fh:
            for line in fh:
                result.append(line)
        return result

    def _merge_results(self, intended_output_dir, new_output_files):
        overall_results_file_name = 'results_all_overall_indices.txt'
        ec_iic_results_file_name = 'results_all_EC(IIC).txt'
        ec_pc_results_file_name = 'results_all_EC(PC).txt'
        for f in new_output_files:
            f_name = os.path.basename(f)
            if f_name == overall_results_file_name:
                self._merge_overall_results(intended_output_dir, f)
            elif f_name in (ec_iic_results_file_name, ec_pc_results_file_name):
                self._merge_special_files_results(intended_output_dir, f)
            else:
                self._merge_other_results(intended_output_dir, f)

    def _merge_overall_results(self, intended_output_dir, file_path):
        f_name = os.path.basename(file_path)
        if f_name in os.listdir(intended_output_dir):
            print('the file is already present in %s' % intended_output_dir)
            print('Appending %s to previous existing overal results file ' \
                  'in %s ...' % (f_name, intended_output_dir))
            f_contents = self._extract_results(file_path)
            print('removing original %s ...' % f_name)
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
            print('num_lines after scanning %s: %i' % (file_path, num_lines))
            if num_lines == 0:
                print('the file is empty. Removing...')
                os.remove(file_path)
            else:
                print('Moving %s to %s ...' % (f_name, intended_output_dir))
                shutil.move(file_path, intended_output_dir)

    def _merge_special_files_results(self, intended_output_dir, file_path):
        f_name = os.path.basename(file_path)
        if f_name in os.listdir(intended_output_dir):
            print('the file is already present in %s' % intended_output_dir)
            print('Appending %s to previous existing overal results file ' \
                  'in %s ...' % (f_name, intended_output_dir))
            f_contents = self._extract_results(file_path)
            print('removing original %s ...' % f_name)
            os.remove(file_path)
            with open(os.path.join(intended_output_dir, f_name), 'a') as fh:
                for line in f_contents:
                    fh.write(line)
        else:
            print('Moving %s to %s ...' % (f_name, intended_output_dir))
            shutil.move(file_path, intended_output_dir)

    def _merge_other_results(self, intended_output_dir, file_path):
        f_name = os.path.basename(file_path)
        print('Moving %s to %s ...' % (f_name, intended_output_dir))
        if os.path.isfile(os.path.join(intended_output_dir, f_name)):
            print('%s is already present in %s. Deleting it before moving ' \
                  'the new file...' % (f_name, intended_output_dir))
            os.remove(os.path.join(intended_output_dir, f_name))
        shutil.move(file_path, intended_output_dir)

    def _run_conefor(self, conefor_path, nodes_file_path,
                     connections_file_path, connection_type,
                     threshold_direct_links=0,
                     binary_indexes=[], decay_distance=0, decay_probability=0,
                     probability_indexes=[], only_overall=False,
                     write_component_file=False, write_links_file=False,
                     write_dispersal_probabilities_file=False,
                     write_maximum_probabilities_file=False,
                     land_area=None, prefix=None):
        '''
        Run Conefor and return the output

        In order to successfuly run the conefor CLI executable, the following
        constraints must be take into consideration:

            - conefor will only save the output files to disk if it is called
              from the same directory where the executable is located
            - conefor will save output files in the same directory
              as the executable.
        '''

        #conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        #connection_type = conn_type_param.options[conn_type_param.value]
        conefor_dir, conefor_file_name = os.path.split(conefor_path)
        command_list = []
        if not SextanteUtils.isWindows():
            command_list.append('wine')
        command_list += [
            conefor_file_name,
            '-nodeFile', nodes_file_path,
            '-conFile', connections_file_path,
            '-t', connection_type,
            self._number_of_connections,
        ]
        if any(binary_indexes):
            command_list += ['-confAdj', '%1.3f' % threshold_direct_links]
            if 'BCIIC' in binary_indexes and 'IIC' not in binary_indexes:
                binary_indexes.append('IIC')
            if 'BCIIC' in binary_indexes and 'BC' not in binary_indexes:
                binary_indexes.append('BC')
            for index in binary_indexes:
                command_list.append('-%s' % index)
        if any(probability_indexes):
            command_list += ['-confProb', '%1.3f' % decay_distance, 
                             '%1.3f' % decay_probability]
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
            command_list += ['-landArea', landArea]
        if prefix is not None:
            command_list += ['-prefix', prefix]
        print('command_list: %s' % command_list)
        process = Popen(command_list, cwd=conefor_dir, stdout=PIPE,
                        stderr=PIPE)
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr

    def _run_the_algorithm(self, nodes_file_path, connections_file_path, prefix):
        raise NotImplementedError

    def _check_for_wine(self):
        '''
        Test the presence of WINE for non Windows users.

        WINE is a compatibility layer for POSIX compliant operating
        systems that allows running Windows applications, such as Conefor.
        '''

        result = False
        process = Popen(['wine', '--version'], stdout=PIPE, stderr=PIPE)
        process.communicate()
        if process.returncode == 0:
            result = True
        return result

    def _problems_to_run(self):
        result = None
        conefor_path = SextanteConfig.getSetting(
                        self.provider.CONEFOR_EXECUTABLE_PATH)
        if not os.path.isfile(conefor_path):
            result = ("Couldn't find the Conefor executable. Set its correct "
                      "path in Sextante options and configuration.")
        else:
            if not self._check_for_wine():
                result = ("In order to use the Sextante Conefor plugin on "
                          "a non Windows Operating System you must install "
                          "the WINE compatibility layer. For more information "
                          "visit the WINE website at\n\n\t"
                          "http://www.winehq.org/\n\n")
        return result


class ConeforBinaryIndexBase(ConeforProcessorBase):
    THRESHOLD_DIRECT_LINKS = 'THRESHOLD_DIRECT_LINKS'
    CREATE_NODE_IMPORTANCES = 'CREATE_NODE_IMPORTANCES'
    WRITE_LINKS_FILE = 'WRITE_LINKS_FILE'

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        self.addParameter(ParameterSelection(self.INPUT_CONNECTION_TYPE,
                          'Connection type', self._connection_types))
        self.addParameter(ParameterNumber(self.THRESHOLD_DIRECT_LINKS,
                          'Threshold (distance/probability) for connecting ' \
                          'nodes (confAdj)'))
        self.addParameter(ParameterBoolean(self.CREATE_NODE_IMPORTANCES,
                          'Process individual node importances', 
                          default=False))
        self.addParameter(ParameterBoolean(self.WRITE_LINKS_FILE,
                          'Write links file',
                          default=False))


class ConeforNCProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Number of Components'
    INDEX_CODE = 'NC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    WRITE_COMPONENT_FILE = 'WRITE_COMPONENT_FILE'

    def defineCharacteristics(self):
        ConeforBinaryIndexBase.defineCharacteristics(self)
        self.addParameter(ParameterBoolean(self.WRITE_COMPONENT_FILE,
                          'Write components file',
                          default=False))

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
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

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforHProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Harary'
    INDEX_CODE = 'H'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforCCPProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Class Coincidence Probability'
    INDEX_CODE = 'CCP'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforLCPProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Landscape Coincidence Probability'
    INDEX_CODE = 'LCP'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforIICProcessor(ConeforBinaryIndexBase):
    GROUP = 'Binary indices'
    INDEX_NAME = 'Integral Index of Connectivity'
    INDEX_CODE = 'IIC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            threshold_direct_links=thresh_d_links,
            binary_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            write_component_file=self.getParameterValue(self.WRITE_COMPONENT_FILE),
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforBCProcessor(ConeforProcessorBase):
    THRESHOLD_DIRECT_LINKS = 'THRESHOLD_DIRECT_LINKS'
    WRITE_LINKS_FILE = 'WRITE_LINKS_FILE'
    GROUP = 'Binary indices'
    INDEX_NAME = 'Betweeness Centrality (Classic)'
    INDEX_CODE = 'BC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        self.addParameter(ParameterSelection(self.INPUT_CONNECTION_TYPE,
                          'Connection type', self._connection_types))
        self.addParameter(ParameterNumber(self.THRESHOLD_DIRECT_LINKS,
                          'Threshold (distance/probability) for connecting ' \
                          'nodes (confAdj)'))
        self.addParameter(ParameterBoolean(self.WRITE_LINKS_FILE,
                          'Write links file',
                          default=False))

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
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
                           connections_file_path, prefix):
        conn_type_param = self.getParameterFromName(self.INPUT_CONNECTION_TYPE)
        connection_type = conn_type_param.options[conn_type_param.value]
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        prefix +='_%s_%s' % (self.INDEX_CODE, thresh_d_links)
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            connection_type,
            threshold_direct_links=thresh_d_links,
            binary_indexes=['IIC', self.INDEX_CODE],
            only_overall=False,
            write_links_file=self.getParameterValue(self.WRITE_LINKS_FILE),
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforProbabilityIndexBase(ConeforProcessorBase):
    CREATE_NODE_IMPORTANCES = 'CREATE_NODE_IMPORTANCES'
    WRITE_PROB_DIR = 'WRITE_PROB_DIR'

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        self.addParameter(ParameterBoolean(self.CREATE_NODE_IMPORTANCES,
                          'Process individual node importances', 
                          default=False))
        self.addParameter(ParameterBoolean(self.WRITE_PROB_DIR,
                          'Write file with direct dispersal probabilities ' \
                          'for each pair of nodes', default=False))


class ConeforProbabilityDistanceProcessor(ConeforProbabilityIndexBase):
    DISTANCE_PROB = 'DISTANCE_PROB'
    PROBABILITY_PROB = 'PROBABILITY_PROB'
    _connection_type = 'dist'
 
    def defineCharacteristics(self):
        ConeforProbabilityIndexBase.defineCharacteristics(self)
        self.addParameter(ParameterNumber(self.DISTANCE_PROB,
                          'Distance to match with probability' \
                          '(confProb distance)'))
        self.addParameter(ParameterNumber(self.PROBABILITY_PROB,
                          'Probability to match with distance' \
                          '(confProb probability)'))


class ConeforFProcessor(ConeforProbabilityDistanceProcessor):
    GROUP = 'Probability indices (distance based)'
    INDEX_NAME = 'Flux'
    INDEX_CODE = 'F'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        distance_prob = self.getParameterValue(self.DISTANCE_PROB)
        prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            decay_distance=distance_prob,
            decay_probability=prob_prob,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            write_dispersal_probabilities_file=write_prob_dir,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforAWFProcessor(ConeforProbabilityDistanceProcessor):
    GROUP = 'Probability indices (distance based)'
    INDEX_NAME = 'Area-weighted Flux'
    INDEX_CODE = 'AWF'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        distance_prob = self.getParameterValue(self.DISTANCE_PROB)
        prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            decay_distance=distance_prob,
            decay_probability=prob_prob,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            write_dispersal_probabilities_file=write_prob_dir,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforPCProcessor(ConeforProbabilityDistanceProcessor):
    GROUP = 'Probability indices (distance based)'
    INDEX_NAME = 'Probability of Connectivity'
    INDEX_CODE = 'PC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    WRITE_PROB_MAX = 'WRITE_PROB_MAX'

    def defineCharacteristics(self):
        ConeforProbabilityDistanceProcessor.defineCharacteristics(self)
        self.addParameter(ParameterBoolean(self.WRITE_PROB_MAX,
                          'Write file with maximum product probabilities ' \
                          'for each pair of nodes', default=False))

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
        distance_prob = self.getParameterValue(self.DISTANCE_PROB)
        prob_prob = self.getParameterValue(self.PROBABILITY_PROB)
        write_prob_dir = self.getParameterValue(self.WRITE_PROB_DIR)
        write_prob_max = self.getParameterValue(self.WRITE_PROB_MAX)
        only_overall = True
        if self.getParameterValue(self.CREATE_NODE_IMPORTANCES):
            only_overall = False
        prefix +='_%s_%s_%s' % (self.INDEX_CODE, distance_prob, prob_prob)
        returncode, stdout, stderr = self._run_conefor(
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
            decay_distance=distance_prob,
            decay_probability=prob_prob,
            probability_indexes=[self.INDEX_CODE],
            only_overall=only_overall,
            write_dispersal_probabilities_file=write_prob_dir,
            write_maximum_probabilities_file=write_prob_max,
            prefix=prefix
        )
        return returncode, stdout, stderr


class ConeforBCPCProcessor(ConeforProcessorBase):
    GROUP = 'Probability indices (distance based)'
    INDEX_NAME = 'Betweeness Centrality Generalized(PC)'
    INDEX_CODE = 'BCPC'
    NAME = '%s index (%s) [%s]' % (INDEX_CODE, INDEX_NAME, GROUP)
    THRESHOLD_DIRECT_LINKS = 'THRESHOLD_DIRECT_LINKS'
    CREATE_NODE_IMPORTANCES = 'CREATE_NODE_IMPORTANCES'
    WRITE_LINKS_FILE = 'WRITE_LINKS_FILE'
    DISTANCE_PROB = 'DISTANCE_PROB'
    PROBABILITY_PROB = 'PROBABILITY_PROB'
    WRITE_PROB_DIR = 'WRITE_PROB_DIR'
    WRITE_PROB_MAX = 'WRITE_PROB_MAX'
    _connection_type = 'dist'

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        self.addParameter(ParameterNumber(self.THRESHOLD_DIRECT_LINKS,
                          '(BC) Threshold (distance/probability) for ' \
                          'connecting nodes (confAdj)'))
        self.addParameter(ParameterBoolean(self.WRITE_LINKS_FILE,
                          '(BC) Write links file',
                          default=False))
        self.addParameter(ParameterBoolean(self.CREATE_NODE_IMPORTANCES,
                          'Process individual node importances', 
                          default=False))
        self.addParameter(ParameterNumber(self.DISTANCE_PROB,
                          'Distance to match with probability' \
                          '(confProb distance)'))
        self.addParameter(ParameterNumber(self.PROBABILITY_PROB,
                          'Probability to match with distance' \
                          '(confProb probability)'))
        self.addParameter(ParameterBoolean(self.WRITE_PROB_DIR,
                          'Write file with direct dispersal probabilities ' \
                          'for each pair of nodes', default=False))
        self.addParameter(ParameterBoolean(self.WRITE_PROB_MAX,
                          'Write file with maximum product probabilities ' \
                          'for each pair of nodes', default=False))

    def _run_the_algorithm(self, conefor_path, nodes_file_path,
                           connections_file_path, prefix):
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
            conefor_path,
            nodes_file_path,
            connections_file_path,
            self._connection_type,
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


class ConeforProbabilityProbabilityProcessor(ConeforProbabilityIndexBase):
    connection_type = 'prob'

    pass
