import qgis.core
from qgis.PyQt import QtCore

from . import schemas
from .utilities import log
from .coneforinputsprocessor import (
    validate_node_identifier_attribute,
    validate_node_attribute,
    validate_node_to_add_attribute,
)


class LayerAnalyzerTask(qgis.core.QgsTask):
    """Collects useful info about input qGIS layers."""

    layers_analyzed = QtCore.pyqtSignal(dict)

    layers_to_analyze: dict[str, qgis.core.QgsMapLayer]
    relevant_layers: dict[qgis.core.QgsVectorLayer, schemas.LayerRelevantFields]

    def __init__(
            self,
            description: str,
            layers_to_analyze: dict[str, qgis.core.QgsMapLayer]
    ):
        super().__init__(description)
        self.layers_to_analyze = layers_to_analyze
        self.relevant_layers = {}

    def run(self):
        if len(self.layers_to_analyze) > 0:
            progress_step = 100 / len(self.layers_to_analyze)
            for index, layer_id in enumerate(self.layers_to_analyze.keys()):
                layer = self.layers_to_analyze[layer_id]
                log(f"Analyzing layer {layer.name()!r}...")
                if layer.type() == qgis.core.QgsMapLayer.LayerType.Vector:
                    layer: qgis.core.QgsVectorLayer
                    if layer.geometryType() == qgis.core.Qgis.GeometryType.Polygon:
                        unique_fields = []
                        numeric_fields = []
                        binary_fields = []
                        for field_index, field in enumerate(layer.fields()):
                            name = field.name()
                            if validate_node_identifier_attribute(layer, field):
                                unique_fields.append(name)
                            if validate_node_attribute(layer, field):
                                numeric_fields.append(name)
                            if validate_node_to_add_attribute(layer, field):
                                binary_fields.append(name)
                        if any(numeric_fields):
                            self.relevant_layers[layer] = schemas.LayerRelevantFields(
                                numerical_field_names=numeric_fields,
                                unique_field_names=unique_fields,
                                binary_value_field_names=binary_fields
                            )
                percent_done = progress_step + index * progress_step
                self.setProgress(percent_done)
        else:
            self.setProgress(100)
        return True

    def finished(self, result):
        self.layers_analyzed.emit(self.relevant_layers)
