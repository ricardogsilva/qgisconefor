import qgis.core
from qgis.PyQt import QtCore

from .coneforinputsprocessor import InputsProcessor
from . import schemas
from .utilities import log


class LayerAnalyzerTask(qgis.core.QgsTask):
    """Collects useful info about input qGIS layers."""

    layers_analyzed = QtCore.pyqtSignal(dict)

    layers_to_analyze: dict[str, qgis.core.QgsMapLayer]
    relevant_layers: dict[qgis.core.QgsVectorLayer, list[str]]

    _relevant_geometry_types = (
        qgis.core.Qgis.GeometryType.Point,
        qgis.core.Qgis.GeometryType.Polygon,
    )

    def __init__(
            self,
            description: str,
            layers_to_analyze: dict[str, qgis.core.QgsMapLayer]
    ):
        super().__init__(description)
        self.layers_to_analyze = layers_to_analyze
        self.relevant_layers = {}

    def run(self):
        progress_step = 100 / len(self.layers_to_analyze)
        for index, layer in enumerate(self.layers_to_analyze.values()):
            log(f"Analyzing layer {layer.name()!r}...")
            if layer.type() == qgis.core.QgsMapLayer.LayerType.Vector:
                layer: qgis.core.QgsVectorLayer
                if layer.geometryType() in self._relevant_geometry_types:
                    the_fields = []
                    for field in layer.fields():
                        if field.type() in schemas.RELEVANT_FIELD_TYPES:
                            the_fields.append(field.name())
                    if any(the_fields):
                        self.relevant_layers[layer] = the_fields
            percent_done = progress_step + index * progress_step
            self.setProgress(percent_done)
        return True

    def finished(self, result):
        self.layers_analyzed.emit(self.relevant_layers)


class LayerProcessorTask(qgis.core.QgsTask):

    layers_processed = QtCore.pyqtSignal(list)

    conefor_processor: InputsProcessor
    layers_data: list[schemas.ConeforInputParameters]
    output_dir: str
    use_selected_features: bool
    processed_results: dict[qgis.core.QgsVectorLayer, list[str]]
    generated_file_paths: list[str]

    def __init__(
            self,
            description: str,
            conefor_processor: InputsProcessor,
            layers_data: list[schemas.ConeforInputParameters],
            output_dir: str,
            use_selected_features: bool,
    ):
        super().__init__(description)
        self.conefor_processor = conefor_processor
        self.layers_data = layers_data
        self.output_dir = output_dir
        self.use_selected_features = use_selected_features

    def run(self):
        self.generated_file_paths = self.conefor_processor.run_queries(
            self.layers_data,
            self.output_dir,
            only_selected_features=self.use_selected_features
        )
        return True

    def finished(self, result: bool):
        self.layers_processed.emit(self.generated_file_paths)
