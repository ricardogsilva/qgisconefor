from PyQt4.QtCore import *

from qgis.core import *

import utilities

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
                    unique_fields = utilities.get_unique_fields(the_layer)
                    if any(unique_fields):
                        usable_layers[the_layer] = unique_fields
        return usable_layers
