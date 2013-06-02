#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
A QGIS plugin for writing input files to the Conefor software.
'''

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from conefordialog import ConeforDialog

class ConeforProcessor(object):

    def __init__(self, iface):
        self.iface = iface
        self.registry = QgsMapLayerRegistry.instance()

    def initGui(self):
        self.action = QAction(QIcon(':plugins/conefor_dev/icon.png'), 
                              'Conefor inputs plugin. Requires at least one ' \
                              'loaded vector layer.', self.iface.mainWindow())
        #self.action.setWhatsThis('')
        self.action.setStatusTip('Conefor inputs plugin (requires at least ' \
                                 'one loaded vector layer)')
        QObject.connect(self.action, SIGNAL('triggered()'), self.run)
        QObject.connect(self.registry,
                        SIGNAL('layersAdded(QList<QgsMapLayer*>)'),
                        self.toggle_availability)
        QObject.connect(self.registry,
                        SIGNAL('layersWillBeRemoved(QStringList)'),
                        self.toggle_availability)
        self.iface.addPluginToVectorMenu('&Conefor inputs', self.action)
        self.iface.addVectorToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginVectorMenu('&Conefor inputs', self.action)
        self.iface.removeVectorToolBarIcon(self.action)

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

            the_layers - can be either a QStringList or a Qlist of
                QgsVectorLayers depending on wether the method is called
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
        if type(the_layers) == QStringList:
            for to_delete in the_layers:
                if usable_layers.get(QString(to_delete)) is not None:
                    del usable_layers[QString(to_delete)]
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

        This plugin only works with vector layers of types Point, MultiPoint,
        Polygon, MutiPolygon.
        '''

        usable_layers = dict()
        loaded_layers = self.registry.mapLayers()
        for layer_id, the_layer in loaded_layers.iteritems():
            if the_layer.type() == QgsMapLayer.VectorLayer:
                if the_layer.geometryType() in (QGis.Point, QGis.Polygon):
                    usable_layers[layer_id] = the_layer
        return usable_layers

    def run_queries(self, layers, output_dir, create_distance_files):
        '''
        Create the Conefor inputs files.

        Inputs:

            layers - A list of dictionaries that have the parameters of the
                layers to process. Each dictionary has the following key/value
                pairs:
                    
                    - layer_name : the name of the ayer, as displayed in the
                      TOC
                    - id_attribute : the attribute who is to be used as
                        an id for Conefor queries
                    - edge_distance : a boolean indicating if the edge
                        distance query is to be performed on this layer
                    - centroid_distance : a boolean indicating if the
                        centroid distance query is to be performed on this
                        layer
                    - area : a boolean indicating if the area query is to 
                        be performed on this layer
                    - attribute : the name of the attribute to use for the
                        attribute query. Can be None, resulting in no 
                        attribute query being performed

            output_dir - The full path to the desired output directory;

            create_distance_files - A boolean indicating if the vector files
                with the lines representing the distances should be created;
        '''

        for layer_parameters in layers:
            print('layer: %s' % layer_parameters['layer_name'])
            if layer_parameters['edge_distance']:
                e_distances = self._run_edge_distance_query(layer_parameters)
                self._write_file(e_distances, output_dir, 'output_name.txt')
                if create_distance_files:
                    self._write_distance_file(layer_parameters, e_distances)
            if layer_parameters['centroid_distance']:
                c_distances = self._run_centroid_distance_query(layer_parameters)
                self._write_file(c_distances, output_dir, 'output_name.txt')
                if create_distance_files:
                    self._write_distance_file(layer_parameters, c_distances)
            if layer_parameters['area']:
                area = self._run_area_query(layer_parameters)
                self._write_file(area, output_dir, 'output_name.txt')
            if layer_parameters['attribute'] is not None:
                attribute = self._run_attribute_query(layer_parameters)
                self._write_file(attribute, output_dir, 'output_name.txt')
            print('------')
    
    def _write_file(self, data, output_dir, output_name):
        '''
        Write a text file with the input data.
        '''

        print('_write_file called')

    def _write_distance_file(layer_parameters, distances):

        print('_write_distance_file called')

    def _run_edge_distance_query(self, layer_parameters):
        '''
        '''

        print('_run_edge_distance_query called')

    def _run_centroid_distance_query(self, layer_parameters):
        '''
        '''

        print('_run_centroid_distance_query called')

    def _run_area_query(self, layer_parameters):
        '''
        '''

        print('_run_area_query called')

    def _run_attribute_query(self, layer_parameters):
        '''
        '''

        print('_run_attribute_query called')
