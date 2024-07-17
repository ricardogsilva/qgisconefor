from pathlib import Path

from PyQt5.QtGui import QIcon
from qgis.PyQt import QtGui
import qgis.core
from processing.core.ProcessingConfig import (
    ProcessingConfig,
    Setting as ProcessingSetting,
)

from ..schemas import (
    ICON_RESOURCE_PATH,
    ConeforProcessingSetting
)
from .algorithms import (
    coneforinputs,
    coneforprocessor,
)


class ProcessingConeforProvider(qgis.core.QgsProcessingProvider):

    DESCRIPTION = 'Conefor (Habitat patches and landscape connectivity analysis)'
    NAME = 'Conefor'

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

    def _load_models(self) -> list[qgis.core.QgsProcessingModelAlgorithm]:
        centroid_distance_model_path = Path(__file__).parent / "models/centroid_distances.model3"
        centroid_distance_algorithm = qgis.core.QgsProcessingModelAlgorithm(
            name="Create centroid distances file",
        )
        centroid_distance_algorithm.fromFile(str(centroid_distance_model_path))
        centroid_distance_algorithm.groupId = lambda: "utilities"
        centroid_distance_algorithm.group = lambda: "Utilities"
        centroid_distance_algorithm.icon = lambda: QtGui.QIcon(ICON_RESOURCE_PATH)
        centroid_distance_algorithm.displayName = lambda: "Calculate centroid distances file"

        edge_distance_model_path = Path(__file__).parent / "models/edge_distances.model3"
        edge_distance_algorithm = qgis.core.QgsProcessingModelAlgorithm(
            name="Create edge distances file",
        )
        edge_distance_algorithm.fromFile(str(edge_distance_model_path))
        edge_distance_algorithm.groupId = lambda: "utilities"
        edge_distance_algorithm.group = lambda: "Utilities"
        edge_distance_algorithm.icon = lambda: QtGui.QIcon(ICON_RESOURCE_PATH)
        edge_distance_algorithm.displayName = lambda: "Calculate edge distances file"

        return [
            centroid_distance_algorithm,
            edge_distance_algorithm,
        ]

    def loadAlgorithms(self):
        self.addAlgorithm(coneforinputs.ConeforInputsPoint())
        self.addAlgorithm(coneforinputs.ConeforInputsPolygon())
        self.addAlgorithm(coneforprocessor.ConeforNCProcessor())
        self.addAlgorithm(coneforprocessor.ConeforNLProcessor())
        self.addAlgorithm(coneforprocessor.ConeforHProcessor())
        self.addAlgorithm(coneforprocessor.ConeforCCPProcessor())
        self.addAlgorithm(coneforprocessor.ConeforLCPProcessor())
        self.addAlgorithm(coneforprocessor.ConeforIICProcessor())
        self.addAlgorithm(coneforprocessor.ConeforBCProcessor())
        self.addAlgorithm(coneforprocessor.ConeforBCIICProcessor())
        self.addAlgorithm(coneforprocessor.ConeforFDistanceProcessor())
        self.addAlgorithm(coneforprocessor.ConeforAWFDistanceProcessor())
        self.addAlgorithm(coneforprocessor.ConeforPCDistanceProcessor())
        self.addAlgorithm(coneforprocessor.ConeforBCPCDistanceProcessor())
        self.addAlgorithm(coneforprocessor.ConeforFProbabilityProcessor())
        self.addAlgorithm(coneforprocessor.ConeforAWFProbabilityProcessor())
        self.addAlgorithm(coneforprocessor.ConeforPCProbabilityProcessor())
        self.addAlgorithm(coneforprocessor.ConeforBCPCProbabilityProcessor())
        model_algorithms = self._load_models()
        for model_algorithm in model_algorithms:
            self.addAlgorithm(model_algorithm)

