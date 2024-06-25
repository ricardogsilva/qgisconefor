import qgis.core
from qgis.PyQt import QtCore


# class LayerAnalyzerThread(QtCore.QThread):
#
#     loaded_layers: dict[str, qgis.core.QgsMapLayer]
#
#     def __init__(
#             self,
#             *,
#             lock,
#             loaded_layers: dict[str, qgis.core.QgsMapLayer],
#             parent=None
#     ):
#         super(LayerAnalyzerThread, self).__init__(parent)
#         self.lock = lock
#         self.mutex = QtCore.QMutex()
#         self.stopped = False
#         self.completed = False
#         self.loaded_layers = loaded_layers
#
#     def run(self):
#         usable_layers = self.analyze_layers()
#         self.stop()
#         self.finished.emit(usable_layers)
#
#     def stop(self):
#         with QtCore.QMutexLocker(self.mutex):
#             self.stopped = True
#
#     def is_stopped(self):
#         result = False
#         with QtCore.QMutexLocker(self.mutex):
#             if self.stopped:
#                 result = True
#         return result
#
#     def analyze_layers(self):
#         """Returns a dictionary with the usable layers and unique fields."""
#
#         usable_layers = {}
#         relevant_types = (
#             QtCore.QtMetaType.Int,
#             QtCore.QtMetaType.Double,
#             QtCore.QtMetaType.Float,
#             QtCore.QtMetaType.Short,
#             QtCore.QtMetaType.Long,
#             QtCore.QtMetaType.LongLong,
#             QtCore.QtMetaType.UInt,
#             QtCore.QtMetaType.ULong,
#             QtCore.QtMetaType.ULongLong,
#             QtCore.QtMetaType.UShort,
#         )
#         for id_, map_layer in self.loaded_layers.items():
#             if map_layer.type() == qgis.core.QgsMapLayer.LayerType.Vector:
#                 the_layer: qgis.core.QgsVectorLayer
#                 if map_layer.wkbType() in (
#                         qgis.core.QgsWkbTypes.Point,
#                         qgis.core.QgsWkbTypes.Polygon,
#                 ):
#                     the_fields = []
#                     for field in map_layer.fields():
#                         if field.type() in relevant_types:
#                             the_fields.append(field.name())
#                     if any(the_fields):
#                         usable_layers[map_layer] = the_fields
#         return usable_layers


class LayerProcessingThread(QtCore.QThread):

    def __init__(self, lock, processor, parent=None):
        super(LayerProcessingThread, self).__init__(parent)
        self.lock = lock
        self.processor = processor
        self.mutex = QtCore.QMutex()
        self.stopped = False
        self.completed = False

    def initialize(self, layers_data, output_dir, only_selected):
        self.layers_data = layers_data
        self.output_dir = output_dir
        self.only_selected  = only_selected

    def run(self):
        new_files = self.processor.run_queries(
            self.layers_data,
            self.output_dir,
            only_selected_features=self.only_selected
        )
        self.stop()
        layers = [d['layer'] for d in self.layers_data]
        self.finished.emit(layers, new_files)

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True

    def is_stopped(self):
        result = False
        with QtCore.QMutexLocker(self.mutex):
            if self.stopped:
                result = True
        return result
