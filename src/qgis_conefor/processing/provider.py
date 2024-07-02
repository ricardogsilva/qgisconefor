from pathlib import Path

from qgis.PyQt import (
    QtCore,
    QtGui,
)
import qgis.core
from processing.core.ProcessingConfig import (
    ProcessingConfig,
    Setting as ProcessingSetting,
)

from ..schemas import (
    ICON_RESOURCE_PATH,
    ConeforProcessingSetting
)
from .algorithms import coneforinputs


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

        edge_distance_model_path = Path(__file__).parent / "models/edge_distances.model3"
        edge_distance_algorithm = qgis.core.QgsProcessingModelAlgorithm(
            name="Create edge distances file",
        )
        edge_distance_algorithm.fromFile(str(edge_distance_model_path))

        return [
            centroid_distance_algorithm,
            edge_distance_algorithm,
        ]

    def loadAlgorithms(self):
        self.addAlgorithm(coneforinputs.ConeforInputsPoint())
        self.addAlgorithm(coneforinputs.ConeforInputsPolygon())
        model_algorithms = self._load_models()
        for model_algorithm in model_algorithms:
            self.addAlgorithm(model_algorithm)

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
