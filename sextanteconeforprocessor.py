from subprocess import Popen, PIPE

from sextante.core.GeoAlgorithm import GeoAlgorithm
from sextante.core.SextanteConfig import SextanteConfig

class ConeforProcessor(GeoAlgorithm):
    NAME = 'Conefor test'
    GROUP = 'Conefor'

    def defineCharacteristics(self):
        self.name = self.NAME
        self.group = self.GROUP

    def processAlgorithm(self, progress):
        rc, stdout, stderr = self._run_conefor('')
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
