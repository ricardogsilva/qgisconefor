import qgis.core
from qgis.PyQt import (
    QtCore,
    QtWidgets,
)


class LayerAnalyzer(qgis.core.QgsTask):

    layers_analyzed = QtCore.pyqtSignal(dict)

    layers_to_analyze: dict[str, qgis.core.QgsMapLayer]
    relevant_layers: dict[qgis.core.QgsVectorLayer, list[qgis.core.QgsField]]

    _relevant_vector_types = (
        qgis.core.QgsWkbTypes.Point,
        qgis.core.QgsWkbTypes.Polygon,
    )

    _relevant_field_types = (
        QtCore.QMetaType.Int,
        QtCore.QMetaType.Double,
        QtCore.QMetaType.Float,
        QtCore.QMetaType.Short,
        QtCore.QMetaType.Long,
        QtCore.QMetaType.LongLong,
        QtCore.QMetaType.UInt,
        QtCore.QMetaType.ULong,
        QtCore.QMetaType.ULongLong,
        QtCore.QMetaType.UShort,
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
        for id_, map_layer in self.layers_to_analyze.items():
            if map_layer.type() == qgis.core.QgsMapLayer.LayerType.Vector:
                the_layer: qgis.core.QgsVectorLayer
                if map_layer.wkbType() in self._relevant_vector_types:
                    the_fields = []
                    for field in map_layer.fields():
                        if field.type() in self._relevant_field_types:
                            the_fields.append(field.name())
                    if any(the_fields):
                        self.relevant_layers[map_layer] = the_fields
        return True

    def finished(self, result):
        self.layers_analyzed.emit(self.relevant_layers)


class LayerProcessor(qgis.core.QgsTask):
    ...
