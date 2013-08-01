import os
from subprocess import Popen, PIPE

from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.core.SextanteConfig import SextanteConfig
from sextante.core.SextanteUtils import SextanteUtils
from sextante.parameters.ParameterFile import ParameterFile
from sextante.parameters.ParameterBoolean import ParameterBoolean
from sextante.parameters.ParameterNumber import ParameterNumber
from sextante.core.GeoAlgorithmExecutionException import \
    GeoAlgorithmExecutionException

class ConeforProcessorBase(GeoAlgorithm):
    NAME = 'Conefor test'
    GROUP = 'Conefor'
    INPUT_NODES_FILE = 'INPUT_NODES_FILE'
    INPUT_CONNECTIONS_FILE = 'INPUT_CONNECTIONS_FILE'
    _type_of_connection_file = 'dist' # only dist is currently supported
    _number_of_connections = 'all'
    _precision = 'double'
    _conefor_binary_indexes = [
        ('CCP', 'Class Coincidence Probability'),
        ('LCP', 'Landscape Coincidence Probability'),
        ('IIC', 'Integral Index of Connectivity'), # this is the recommended binary index
        ('BC', 'Betweeness Centrality'),
        'BCIIC',
        ('NC', 'Number of Components'),
        ('NL', 'Number of Links'),
        ('H', 'Harary index'),
    ]
    _conefor_probability_indexes = [
        ('F', 'Flux)',
        ('AWF', 'Area-weighted Flux'),
        ('PC', 'Probability of Connectivity'), # this is the recommended probability index
        'BCPC',
    ]
    _conefor_bc_indexes = [
        ('BC', 'Classical Betweeness Centrality'),
        ('BC()', 'Classical Betweeness Centrality'),
        ('BC()', 'Classical Betweeness Centrality'),
    ]


    def defineCharacteristics(self):
        self.name = self.NAME
        self.group = self.GROUP
        self.addParameter(ParameterFile(self.INPUT_NODES_FILE,
                          'Nodes file', optional=False))
        self.addParameter(ParameterFile(self.INPUT_CONNECTIONS_FILE,
                          'Connections file', optional=False))

    def checkBeforeOpeningParametersDialog(self):
        return self._problems_to_run()

    def processAlgorithm(self, progress):
        problems = self._problems_to_run()
        if problems is None:
            nodes = self.getParameterValue(self.INPUT_NODES_FILE)
            connections = self.getParameterValue(self.INPUT_CONNECTIONS_FILE)
            rc, stdout, stderr = self._run_the_algorithm(nodes, connections)
            print('rc: %s' % rc)
            print('stdout: %s' % stdout)
            print('stderr: %s' % stderr)
        else:
            raise GeoAlgorithmExecutionException(problems)

    def _run_conefor(self, nodes_file_path, connections_file_path,
                     threshold_direct_links=0, binary_indexes=[],
                     decay_distance=0, decay_probability=0,
                     probability_indexes=[],
                     only_overall=False, write_component_file=True,
                     write_links_file=True,
                     write_dispersal_probabilities_file=True,
                     write_maximum_probabilities_file=True,
                     land_area=None):
        '''
        Run Conefor and return the output
        '''

        command_list = []
        if not SextanteUtils.isWindows():
            command_list.append('wine')
        command_list += [
            SextanteConfig.getSetting(self.provider.CONEFOR_EXECUTABLE_PATH),
            '-nodeFile', nodes_file_path,
            '-conFile', connections_file_path,
            '-t', self._type_of_connection_file,
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
            command_list += ['-confProb', decay_distance, decay_probability]
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
        print('command_list: %s' % command_list)
        process = Popen(command_list, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr

    def _run_the_algorithm(self, nodes_file_path, connections_file_path):
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

class ConeforBinaryIndicesProcessor(ConeforProcessorBase):
    GROUP = 'Polygons'
    NAME = 'Conefor - Binary indexes [%s]' % GROUP
    THRESHOLD_DIRECT_LINKS = 'THRESHOLD_DIRECT_LINKS'
    ONLY_OVERALL = 'ONLY_OVERALL'

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        self.addParameter(ParameterNumber(self.THRESHOLD_DIRECT_LINKS,
                          'Threshold for direct links (confAdj)'))
        for index in self._conefor_binary_indexes:
            self.addParameter(ParameterBoolean(index, '%s index' % index,
                              default=False))

    def _run_the_algorithm(self, nodes_file_path, connections_file_path):
        thresh_d_links = self.getParameterValue(self.THRESHOLD_DIRECT_LINKS)
        binary_indexes = []
        for index in self._conefor_binary_indexes:
            to_process = self.getParameterValue(index)
            if to_process:
                binary_indexes.append(index)
        returncode, stderr, stdout = self._run_conefor(
            nodes_file_path,
            connections_file_path,
            thresh_d_links,
            binary_indexes
        )
        return returncode, stderr, stdout

class ConeforBetweenessCentralityMetricsProcessor(ConeforProcessorBase):
    '''
    This GeoAlgorithm allows the calculation of the various BC indexes:

        - BC
        - BC(IIC)
        - BC(PC)

    These metrics differ from the other metrics calculated in Conefor in
    that they can only be calculated at the level of individual nodes. They
    do not provide an overall value characterizing the connectivity of the
    entire landscape (thus the onlyoverall option is not used)
    '''

    pass


class ConeforHabitatAvailabilityMetricsProcessor(ConeforProcessorBase):
    '''
    This GeoAlgorithm allows the calculation of of indexes related to
    habitat availability:

        - IIC
        - PC
    '''

