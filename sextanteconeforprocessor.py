from subprocess import Popen, PIPE

from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.core.SextanteConfig import SextanteConfig
from sextante.parameters.ParameterFile import ParameterFile
from sextante.parameters.ParameterBoolean import ParameterBoolean

class ConeforProcessor(GeoAlgorithm):
    NAME = 'Conefor test'
    GROUP = 'Conefor'
    INPUT_NODES_FILE = 'INPUT_NODES_FILE'
    INPUT_CONNECTIONS_FILE = 'INPUT_CONNECTIONS_FILE'

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

    def _run_conefor(self, command):
        '''
        Run Conefor and return the output
        '''

        if SextanteConfig.getSetting(self.provider.RUN_THROUGH_WINE):
            #print('will run through wine')
            command_list = ['wine']
        else:
            #print('will run without wine')
            command_list = []
        conefor_executable = SextanteConfig.getSetting(self.provider.CONEFOR_EXECUTABLE_PATH)
        command_list = command_list + [conefor_executable] + command.split()
        print('command_list: %s' % command_list)
        process = Popen(command_list, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr


class ConeforBinaryIndicesProcessor(ConeforProcessor):
    GROUP = 'Polygons'
    NAME = 'Conefor - Binary indices [%s]' % GROUP
    NL_INDEX = 'NL_INDEX'
    BC_INDEX = 'BC_INDEX'
    NC_INDEX = 'NC_INDEX'

    def defineCharacteristics(self):
        ConeforProcessor.defineCharacteristics(self)
        self.addParameter(ParameterBoolean(self.NL_INDEX,
                          'NL index', default=False))
        self.addParameter(ParameterBoolean(self.BC_INDEX,
                          'BC index', default=False))
        self.addParameter(ParameterBoolean(self.NC_INDEX,
                          'NC index', default=False))



