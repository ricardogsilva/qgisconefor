#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
A QGIS plugin for writing input files to the Conefor software.
'''

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from coneforinputsprocessor import InputsProcessor
from conefordialog import ConeforDialog

#from sextante.core.Sextante import Sextante
#from sextanteconeforprovider import SextanteConeforProvider


class NoFeaturesToProcessError(Exception):
    pass


class ConeforProcessor(object):

    _plugin_name = 'Conefor inputs'

    def __init__(self, iface):
        self.iface = iface
        self.registry = QgsMapLayerRegistry.instance()
        project_crs = self.iface.mapCanvas().mapRenderer().destinationCrs()
        self.processor = InputsProcessor(project_crs)
        #self.sextante_provider = SextanteConeforProvider()

    def initGui(self):
        #Sextante.addProvider(self.sextante_provider)
        self.action = QAction(QIcon(':plugins/conefor_dev/icon.png'), 
                              self._plugin_name, self.iface.mainWindow())
        QObject.connect(self.action, SIGNAL('triggered()'), self.run)
        QObject.connect(self.registry,
                        SIGNAL('layersAdded(QList<QgsMapLayer*>)'),
                        self.toggle_availability)
        QObject.connect(self.registry,
                        SIGNAL('layersWillBeRemoved(QStringList)'),
                        self.toggle_availability)
        self.iface.addPluginToVectorMenu('&Conefor inputs', self.action)
        self.iface.addVectorToolBarIcon(self.action)
        usable_layers = self.get_usable_layers()
        self.action.setEnabled(False)
        if any(usable_layers):
            self.action.setEnabled(True)

    def unload(self):
        self.iface.removePluginVectorMenu('&Conefor inputs', self.action)
        self.iface.removeVectorToolBarIcon(self.action)
        #Sextante.removeProvider(self.sextante_provider)

    def run(self):
        usable_layers = self.get_usable_layers()
        cl = self.iface.mapCanvas().currentLayer()
        if cl not in usable_layers.values():
            cl = usable_layers.values()[0]
        dialog = ConeforDialog(usable_layers, cl, self)
        result = dialog.exec_()

    def toggle_availability(self, the_layers):
        '''
        Toggle the plugin's availability.

        inputs:

            the_layers - can be either a list of the ids of the layers that
                are about to be removed or a list of QgsVectorLayers that are
                about to be added, depending on wether the method is called
                by the 'layersWillBeRemoved' or the 'layersAdded' signals
                of the mapLayerRegistry.

        This method is called whenever the mapLayerRegistry emits either
        the 'layersAdded' or the 'layersWillBeRemoved' signals.

        Plugin availability depends on the availability of vector
        layers loaded in QGIS.
        '''

        usable_layers = self.get_usable_layers()
        # mapLayerRegistry's layersWillBeRemoved signal is sent before the
        # layers are removed so we need to check which layers are going to be
        # removed and act as if they were already gone
        if any(the_layers):
            if isinstance(the_layers[0], basestring):
                for to_delete in the_layers:
                    if usable_layers.get(to_delete) is not None:
                        del usable_layers[to_delete]
        one_vector_loaded = False
        if any(usable_layers):
            for layer_id, layer in usable_layers.iteritems():
                if layer.type() == QgsMapLayer.VectorLayer:
                    one_vector_loaded = True
                    break
        self.action.setEnabled(one_vector_loaded)

    def get_usable_layers(self):
        '''
        return a dictionary with layerid as key and layer as value.

        This plugin only works with vector layers of types Point and Polygon.
        '''

        usable_layers = dict()
        loaded_layers = self.registry.mapLayers()
        for layer_id, the_layer in loaded_layers.iteritems():
            if the_layer.type() == QgsMapLayer.VectorLayer:
                if the_layer.geometryType() in (QGis.Point, QGis.Polygon):
                    unique_fields = self._get_unique_fields(the_layer)
                    if any(unique_fields):
                        usable_layers[layer_id] = the_layer
        return usable_layers

    def _get_unique_fields(self, layer):
        '''
        Return the names of the attributes that contain unique values only.

        Inputs:

            layer - A QgsVectorLayer

        Returns a list of strings with the names of the fields that have only
        unique values.
        '''

        result = []
        fields = layer.dataProvider().fields()
        all_ = self._get_all_values(layer)
        for f in fields:
            the_values = [v['value'] for v in all_ if v['field'] == f.name()]
            unique_values = set(the_values)
            if len(the_values) == len(unique_values):
                result.append(f.name())
        return result

    def _get_all_values(self, layer):
        result = []
        fields = layer.dataProvider().fields()
        for feat in layer.getFeatures():
            for field in fields:
                result.append({
                    'field' : field.name(),
                    'value' : feat.attribute(field.name()),
                })
        return result
