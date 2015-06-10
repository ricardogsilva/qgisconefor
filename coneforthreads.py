from PyQt4.QtCore import *

from qgis.core import *


class LayerAnalyzerThread(QThread):

    def __init__(self, lock, parent=None):
        super(LayerAnalyzerThread, self).__init__(parent)
        self.lock = lock
        self.mutex = QMutex()
        self.stopped = False
        self.completed = False

    def initialize(self, loaded_layers):
        self.loaded_layers = loaded_layers

    def run(self):
        usable_layers = self.analyze_layers()
        self.stop()
        self.emit(SIGNAL('finished'), usable_layers)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True

    def is_stopped(self):
        result = False
        with QMutexLocker(self.mutex):
            if self.stopped:
                result = True
        return result

    def analyze_layers(self):
        '''
        Returns a dictionary with the usable layers and unique fields.
        '''

        usable_layers = dict()
        for layer_id, the_layer in self.loaded_layers.iteritems():
            self.emit(SIGNAL('analyzing_layer'), the_layer.name())
            if the_layer.type() == QgsMapLayer.VectorLayer:
                if the_layer.geometryType() in (QGis.Point, QGis.Polygon):
                    the_fields = []
                    for f in the_layer.dataProvider().fields():
                        if f.type() in (QVariant.Int, QVariant.Double):
                            the_fields.append(f.name())
                    if any(the_fields):
                        usable_layers[the_layer] = the_fields
        return usable_layers


class LayerProcessingThread(QThread):

    def __init__(self, lock, processor, parent=None):
        super(LayerProcessingThread, self).__init__(parent)
        self.lock = lock
        self.processor = processor
        self.mutex = QMutex()
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
        self.emit(SIGNAL('finished'), layers, new_files)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True

    def is_stopped(self):
        result = False
        with QMutexLocker(self.mutex):
            if self.stopped:
                result = True
        return result
