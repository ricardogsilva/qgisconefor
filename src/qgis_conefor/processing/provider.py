import enum
import os

from qgis.PyQt import (
    QtCore,
    QtGui,
)
import qgis.core
from processing.core.ProcessingConfig import (
    ProcessingConfig,
    Setting as ProcessingSetting,
)

from ..schemas import ICON_RESOURCE_PATH
from .algorithms import coneforinputs


class ConeforProcessingSetting(enum.Enum):
    CONEFOR_CLI_PATH = "conefor executable path"


class ProcessingConeforProvider(qgis.core.QgsProcessingProvider):

    DESCRIPTION = 'Conefor (Habitat patches and landscape connectivity analysis)'
    NAME = 'Conefor'
    CONEFOR_EXECUTABLE_PATH = 'CONEFOR_EXECUTABLE_PATH'

    def id(self) -> str:
        return "conefor"

    def name(self) -> str:
        return self.id().capitalize()

    def icon(self) -> QtGui.QIcon:
        return QtGui.QIcon(ICON_RESOURCE_PATH)

    def load(self):
        ProcessingConfig.settingIcons[self.name()] = self.icon()
        ProcessingConfig.addSetting(
            ProcessingSetting(
                group=self.name(),
                name=ConeforProcessingSetting.CONEFOR_CLI_PATH.name,
                description=ConeforProcessingSetting.CONEFOR_CLI_PATH.value,
                default="",
            )
        )
        return super().load()

    def loadAlgorithms(self):
        self.addAlgorithm(coneforinputs.ConeforInputsAttribute())

        # self.addAlgorithm(processingconeforinputs.ConeforInputsPointAttribute())
        # self.addAlgorithm(processingconeforinputs.ConeforInputsPolygonAttribute())
        # self.addAlgorithm(processingconeforinputs.ConeforInputsPolygonArea())
        # self.addAlgorithm(processingconeforinputs.ConeforInputsPointCentroid())
        # self.addAlgorithm(processingconeforinputs.ConeforInputsPolygonCentroid())
        # self.addAlgorithm(processingconeforinputs.ConeforInputsPolygonEdge())
        # self.addAlgorithm(processingconeforinputs.ConeforInputsPointCentroidDistance())
        # self.addAlgorithm(processingconeforinputs.ConeforInputsPolygonCentroidDistance())
        # self.addAlgorithm(processingconeforinputs.ConeforInputsPolygonEdgeDistance())

        # self.addAlgorithm(processingconeforprocessor.ConeforNCProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforNLProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforHProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforCCPProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforLCPProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforIICProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforBCProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforBCIICProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforFDistanceProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforFProbabilityProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforAWFDistanceProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforAWFProbabilityProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforPCDistanceProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforPCProbabilityProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforBCPCDistanceProcessor())
        # self.addAlgorithm(processingconeforprocessor.ConeforBCPCProbabilityProcessor())
