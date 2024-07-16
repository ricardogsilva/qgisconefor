import qgis.core
from qgis.PyQt import QtCore

from . import schemas
from .utilities import log


class LayerAnalyzerTask(qgis.core.QgsTask):
    """Collects useful info about input qGIS layers."""

    layers_analyzed = QtCore.pyqtSignal(dict)

    layers_to_analyze: dict[str, qgis.core.QgsMapLayer]
    relevant_layers: dict[qgis.core.QgsVectorLayer, list[str]]
    relevant_layer_ids: dict[str, list[str]]

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
        self.relevant_layer_ids = {}

    def run(self):
        if len(self.layers_to_analyze) > 0:
            progress_step = 100 / len(self.layers_to_analyze)
            for index, layer_id in enumerate(self.layers_to_analyze.keys()):
                layer = self.layers_to_analyze[layer_id]
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
                            self.relevant_layer_ids[layer_id] = the_fields
                percent_done = progress_step + index * progress_step
                self.setProgress(percent_done)
        else:
            self.setProgress(100)
        return True

    def finished(self, result):
        self.layers_analyzed.emit(self.relevant_layers)
