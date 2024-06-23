import qgis.core
from qgis.PyQt import QtCore


class LayerAnalyzerThread(QtCore.QThread):

    analyzing_layer = QtCore.pyqtSignal()

    def __init__(self, lock, parent=None):
        super(LayerAnalyzerThread, self).__init__(parent)
        self.lock = lock
        self.mutex = QtCore.QMutex()
        self.stopped = False
        self.completed = False

    def initialize(
            self,
            loaded_layers: dict[str, qgis.core.QgsMapLayer]
    ):
        self.loaded_layers = loaded_layers

    def run(self):
        usable_layers = self.analyze_layers()
        self.stop()
        self.finished.emit(usable_layers)

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True

    def is_stopped(self):
        result = False
        with QtCore.QMutexLocker(self.mutex):
            if self.stopped:
                result = True
        return result

    def analyze_layers(self):
        """Returns a dictionary with the usable layers and unique fields."""

        usable_layers = dict()
        for layer_id, the_layer in self.loaded_layers.iteritems():
            self.analyzing_layer.emit(the_layer.name())
            if the_layer.type() == qgis.core.QgsMapLayer.VectorLayer:
                the_layer: qgis.core.QgsVectorLayer
                if the_layer.wkbType() in (
                        qgis.core.QgsWkbTypes.Point,
                        qgis.core.QgsWkbTypes.Polygon
                ):
                    the_fields = []
                    for f in the_layer.dataProvider().fields():
                        if f.type() in (QtCore.QVariant.Int, QtCore.QVariant.Double):
                            the_fields.append(f.name())
                    if any(the_fields):
                        usable_layers[the_layer] = the_fields
        return usable_layers


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
