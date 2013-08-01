from subprocess import Popen, PIPE

from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.core.SextanteConfig import SextanteConfig
from sextante.parameters.ParameterFile import ParameterFile
from sextante.parameters.ParameterBoolean import ParameterBoolean

class ConeforProcessorBase(GeoAlgorithm):
    NAME = 'Conefor test'
    GROUP = 'Conefor'
    INPUT_NODES_FILE = 'INPUT_NODES_FILE'
    INPUT_CONNECTIONS_FILE = 'INPUT_CONNECTIONS_FILE'
    _type_of_connection_file = 'dist'
    _connections = 'all'
    _precision = 'double'

    def defineCharacteristics(self):
        self.name = self.NAME
        self.group = self.GROUP
        self.addParameter(ParameterFile(self.INPUT_NODES_FILE,
                          'Nodes file', optional=False))
        self.addParameter(ParameterFile(self.INPUT_CONNECTIONS_FILE,
                          'Connections file', optional=False))

    def processAlgorithm(self, progress):
        nodes = self.getParameterValue(self.INPUT_NODES_FILE)
        connections = self.getParameterValue(self.INPUT_CONNECTIONS_FILE)
        command = '-nodeFile %s -conFile %s' % (nodes, connections)
        rc, stdout, stderr = self._run_conefor(command)
        print('rc: %s' % rc)
        print('stdout: %s' % stdout)
        print('stderr: %s' % stderr)

    def _run_conefor(self, nodes_file_path, connections_file_path,
                     threshold_direct_links=0, binary_indexes=[],
                     probability_indexes=[],
                     only_overall=False, write_component_file=False, 
                     write_links_file=False,
                     write_dispersal_probabilities_file=False,
                     write_maximum_probabilities_file=False,
                     land_area=None):
        '''
        Run Conefor and return the output
        '''

        if SextanteConfig.getSetting(self.provider.RUN_THROUGH_WINE):
            command_list = ['wine']
        else:
            command_list = []
        conefor_executable = SextanteConfig.getSetting(
            self.provider.CONEFOR_EXECUTABLE_PATH)
        command_list += [
            conefor_executable,
            '-nodeFile', nodes_file_path,
            '-conFile', connections_file_path,
            '-t', self._type_of_connection_file,
            self._connections,
        ]
        if any(binary_indexes):
            command_list += ['-confAdj', threshold_direct_links]
            if 'BCIIC' in binary_indexes and 'IIC' not in binary_indexes:
                binary_indexes.append('IIC')
            for index in binary_indexes:
                command_list.append('-%s' % index)
        if any(probability_indexes):
            command_list += ['-confProb']
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


class ConeforBinaryIndicesProcessor(ConeforProcessorBase):
    GROUP = 'Polygons'
    NAME = 'Conefor - Binary indices [%s]' % GROUP
    NL_INDEX = 'NL_INDEX'
    BC_INDEX = 'BC_INDEX'
    NC_INDEX = 'NC_INDEX'

    def defineCharacteristics(self):
        ConeforProcessorBase.defineCharacteristics(self)
        self.addParameter(ParameterBoolean(self.NL_INDEX,
                          'NL index', default=False))
        self.addParameter(ParameterBoolean(self.BC_INDEX,
                          'BC index', default=False))
        self.addParameter(ParameterBoolean(self.NC_INDEX,
                          'NC index', default=False))
