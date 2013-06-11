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


#TODO
# Add a label with progress info to the GUI
# Filter the id_attribute field choices to show only unique fields
# create a Makefile
# Write the help dialog
# Provide better docstrings
# Add more testing layers (empty features, empty fields)

class NoFeaturesToProcessError(Exception):
    pass


class ConeforProcessor(QObject):

    def __init__(self, iface):
        super(ConeforProcessor, self).__init__()
        self.iface = iface
        self.registry = QgsMapLayerRegistry.instance()
        self.global_progress = 0

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
            if type(the_layers[0]) == str:
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

                    - layer : a QgsMapLayer to be processed
                    - id_attribute : the name of the attribute to be used as
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

        layer_progress_step = 100.0 / len(layers)
        for index, layer_parameters in enumerate(layers):
            try:
                self.process_layer(layer_parameters['layer'],
                                   layer_parameters['id_attribute'],
                                   layer_parameters['area'],
                                   layer_parameters['attribute'],
                                   layer_parameters['centroid_distance'],
                                   layer_parameters['edge_distance'],
                                   output_dir, layer_progress_step,
                                   create_distance_files)
            except NoFeaturesToProcessError:
                print('Layer %s has no features to process' % \
                      layer_parameters['layer'].name())
            self.global_progress += layer_progress_step
            self.emit(SIGNAL('progress_changed'))

    def _write_file(self, data, output_dir, output_name):
        '''
        Write a text file with the input data.

        Inputs:

            data - a list of two element tuples

        Before being written, the data is sorted by the first element in the
        tuple.
        '''

        sorted_data = sorted(data, key=lambda tup: tup[0])
        output_path = os.path.join(output_dir, output_name)
        with open(output_path, 'w') as file_handler:
            for line in sorted_data:
                file_handler.write(line)

    def _write_distance_file(self, data, output_dir, output_name, encoding,
                             crs, file_type='ESRI Shapefile'):
        '''
        Write a GIS file with distances to disk.

        Inputs:

            data - a list of dictionaries with key/values:
                from: A QgsPoint with the coordinates of the
                    start of a line
                to: A QgsPoint with the coordinates of the
                    end of a line
                distance: The distance between the two QgsPoints,
                    measured in meters
                from_attribute - The value of the attribute used
                    as an identifier for features in the layer
                to_attribute - The value of the attribute used
                    as an identifier for features in the layer

            output_dir - The path to the directory where the file will
                be written to.

            output_name - The name for the file, without extension

            encoding - A string with the encoding to use when writing
                the attributes

            crs - A QgsCoordinateReferenceSystem object representing the
                CRS of the output file

            file_type - A string representing the type of file format to use
        '''

        output_path = os.path.join(output_dir, output_name)
        if file_type == 'ESRI Shapefile':
            output_path = '%s.shp' % output_path
        fields = QgsFields()
        fields.append(QgsField('from_to', QVariant.String, 'from_to', 255))
        fields.append(QgsField('distance', QVariant.Double,
                      'distance', 255, 1))
        writer = QgsVectorFileWriter(output_path, encoding, fields,
                                     QGis.WKBLineString, crs, file_type)
        if writer.hasError() == QgsVectorFileWriter.NoError:
            for item in data:
                feat = QgsFeature()
                line = [item['from'], item['to']]
                from_to = '%s_%s' % (item['from_attribute'],
                                     item['to_attribute'])
                feat.setGeometry(QgsGeometry.fromPolyline(line))
                feat.setFields(fields)
                feat.initAttributes(2)
                feat.setAttribute('from_to', from_to)
                feat.setAttribute('distance', item['distance'])
                writer.addFeature(feat)
        else:
            print('Error when creating distances lines file: %s' % \
                  writer.hasError())
        del writer
        new_layer = QgsVectorLayer(output_path, output_name, 'ogr')
        self.registry.addMapLayer(new_layer)

    def process_layer(self, layer, id_attribute, area, attribute,
                      centroid, edge, output_dir, progress_step,
                      create_distance_files):
        '''
        Process an individual layer.

        Inputs:

            layer - A QgsVector layer

            id_attribute - The name of the attribute to be used as id

            area - A boolean indicating if the area is to be processed

            attribute - The name of the attribute to be processed. If None,
                the attribute process does not take place

            centroid - A boolean indicating if the centroid distances are to
                be calculated

            edge - A boolean indicating if the edge distances are to
                be calculated

            output_dir - The directory where the output files are to be saved

            progress_step - The ammount of progress available for using in
                this method

            create_distance_files - A boolean specifying if the output distance
                files are to be created
        '''

        encoding = layer.dataProvider().encoding()
        num_queries = self._determine_num_queries(area, attribute, centroid,
                                                  edge)
        num_files_to_save = num_queries
        if create_distance_files:
            num_files_to_save += centroid + edge
        running_queries_step = progress_step / 2.0
        each_query_step = running_queries_step / num_queries
        saving_files_step = progress_step - running_queries_step
        each_save_file_step = saving_files_step / num_files_to_save
        attribute_data = []
        if attribute is not None:
            attribute_data = self._run_attribute_query(layer, id_attribute,
                                                       attribute)
            self.global_progress += each_query_step
            self.emit(SIGNAL('progress_changed'))
        area_data = []
        if area:
            area_data = self._run_area_query(layer, id_attribute)
            self.global_progress += each_query_step
            self.emit(SIGNAL('progress_changed'))
        centroid_data = []
        if centroid:
            centroid_data = self._run_centroid_query(layer, id_attribute)
            self.global_progress += each_query_step
            self.emit(SIGNAL('progress_changed'))
        edge_data = []
        if edge:
            edge_data = self._run_edge_query(layer, id_attribute)
            self.global_progress += each_query_step
            self.emit(SIGNAL('progress_changed'))
        if any(attribute_data):
            output_name = 'nodes_%s_%s' % (attribute, layer.name())
            self._write_file(attribute_data, output_dir, output_name)
        self.global_progress += each_save_file_step
        self.emit(SIGNAL('progress_changed'))
        if any(area_data):
            output_name = 'nodes_calculated_area_%s' % layer.name()
            self._write_file(area_data, output_dir, output_name)
        self.global_progress += each_save_file_step
        self.emit(SIGNAL('progress_changed'))
        if any(centroid_data):
            output_name = 'distances_centroids_%s' % layer.name()
            data_to_write = []
            for c_dict in centroid_data:
                current_id = c_dict['current']['attribute']
                next_id = c_dict['next']['attribute']
                distance = c_dict['distance']
                data_to_write.append('%s\t%s\t%s\n' % (current_id, next_id,
                                     distance))
            self._write_file(data_to_write, output_dir, output_name)
        self.global_progress += each_save_file_step
        self.emit(SIGNAL('progress_changed'))
        if any(edge_data):
            output_name = 'distances_edges_%s' % layer.name()
            data_to_write = []
            for e_dict in edge_data:
                from_id = e_dict['from_attribute']
                to_id = e_dict['to_attribute']
                distance = e_dict['distance']
                data_to_write.append('%s\t%s\t%s\n' % (from_id, to_id,
                                     distance))
            self._write_file(data_to_write, output_dir, output_name)
        self.global_progress += each_save_file_step
        self.emit(SIGNAL('progress_changed'))
        if create_distance_files:
            output_dir = os.path.join(output_dir, 'distance_files')
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)
            if any(centroid_data):
                data_to_write = []
                for c_dict in centroid_data:
                    the_data = {
                        'from' : c_dict['current']['centroid'],
                        'to' : c_dict['next']['centroid'],
                        'distance' : c_dict['distance'],
                        'from_attribute' : c_dict['current']['attribute'],
                        'to_attribute' : c_dict['next']['attribute'],
                    }
                    data_to_write.append(the_data)
                output_name = 'centroid_distances_%s' % layer.name()
                self._write_distance_file(data_to_write, output_dir,
                                          output_name, encoding, layer.crs())
            self.global_progress += each_save_file_step
            self.emit(SIGNAL('progress_changed'))
            if any(edge_data):
                output_name = 'edge_distances_%s' % layer.name()
                self._write_distance_file(edge_data, output_dir, output_name,
                                          encoding, layer.crs())
            self.global_progress += each_save_file_step
            self.emit(SIGNAL('progress_changed'))

    def _determine_num_queries(self, area, attribute, centroid, edge):
        '''
        Return the number of queries that will be processed.

        This method's main purpose is calculating progress steps.
        '''

        num_queries = 0
        if area:
            num_queries += 1
        if attribute is not None:
            num_queries += 1
        if centroid:
            num_queries += 1
        if edge:
            num_queries += 1
        return num_queries

    def _run_attribute_query(self, layer, id_attribute, attribute):
        result = []
        feat = QgsFeature()
        feat_iterator = layer.getFeatures()
        while feat_iterator.nextFeature(feat):
            id_attr = feat.attribute(id_attribute)
            attr = feat.attribute(attribute)
            result.append('%s\t%s\n' % (id_attr, attr))
        return result

    def _run_geographic_layer_area_query(self, layer, id_attribute):
        result = []
        project_crs = self.iface.mapCanvas().mapRenderer().destinationCrs()
        if project_crs.geographicFlag():
            print('Neither the layer nor the project\'s coordinate ' \
                    'system is projected. The area calculation will not ' \
                    'be acurate.')
        feat = QgsFeature()
        feat_iterator = layer.getFeatures()
        measurer = self._get_measurer(project_crs)
        transformer = self._get_transformer(layer)
        while feat_iterator.nextFeature(feat):
            polygon = feat.geometry().asPolygon()
            new_polygon = []
            for ring in polygon:
                new_ring = []
                for point in ring:
                    new_ring.append(transformer.transform(point))
                new_polygon.append(new_ring)
            outer_area = measurer.measurePolygon(new_polygon[0])
            hole_areas = 0
            if len(new_polygon) > 1:
                holes = new_polygon[1:]
                for hole in holes:
                    hole_areas += measurer.measurePolygon(hole)
            total_feat_area = outer_area - hole_areas
            id_attr = feat.attribute(id_attribute)
            result.append('%s\t%s\n' % (id_attr, total_feat_area))
        return result

    def _run_projected_layer_area_query(self, layer, id_attribute):
        result = []
        measurer = self._get_measurer(layer.crs())
        feat = QgsFeature()
        feat_iterator = layer.getFeatures()
        while feat_iterator.nextFeature(feat):
            id_attr = feat.attribute(id_attribute)
            area = measurer.measure(feat.geometry())
            result.append('%s\t%s\n' % (id_attr, area))
        return result

    def _run_area_query(self, layer, id_attribute):
        if layer.crs().geographicFlag():
            result = self._run_geographic_layer_area_query(layer,
                                                           id_attribute)
        else:
            result = self._run_projected_layer_area_query(layer, id_attribute)
        return result

    def _run_centroid_query(self, layer, id_attribute):
        result = []
        if layer.crs().geographicFlag():
            project_crs = self.iface.mapCanvas().mapRenderer().destinationCrs()
            measurer = self._get_measurer(project_crs)
            transformer = self._get_transformer(layer)
        else:
            measurer = self._get_measurer(layer.crs())
            transformer = None
        feature_ids = self._get_feature_ids(layer)
        current = QgsFeature()
        next_ = QgsFeature()
        i = 0
        j = 0
        while i < len(feature_ids):
            i_current = layer.getFeatures(QgsFeatureRequest(feature_ids[i]))
            i_current.nextFeature(current)
            current_id_attr = current.attribute(id_attribute)
            current_geom = current.geometry()
            original_current_centroid = current_geom.centroid().asPoint()
            transformed_current_centroid = self._get_centroid(current_geom,
                                                              transformer)
            j = i + 1
            while j < len(feature_ids):
                i_next = layer.getFeatures(QgsFeatureRequest(feature_ids[j]))
                i_next.nextFeature(next_)
                next_id_attr = next_.attribute(id_attribute)
                next_geom = next_.geometry()
                original_next_centroid = next_geom.centroid().asPoint()
                transformed_next_centroid = self._get_centroid(next_geom, transformer)
                distance = measurer.measureLine(transformed_current_centroid,
                                                transformed_next_centroid)
                feat_result = {
                    'current' : {
                        'attribute' : current_id_attr,
                        'centroid' : original_current_centroid,
                        'feature_geometry' : current_geom,
                    },
                    'next' : {
                        'attribute' : next_id_attr,
                        'centroid' : original_next_centroid,
                        'feature_geometry' : next_geom,
                    },
                    'distance' : distance,
                }
                result.append(feat_result)
                j += 1
            i += 1
        return result

    def _get_measurer(self, source_crs):
        measurer = QgsDistanceArea()
        measurer.setEllipsoidalMode(False)
        measurer.setSourceCrs(source_crs.postgisSrid())
        return measurer

    def _get_transformer(self, layer):
        source_crs = layer.crs()
        project_crs = self.iface.mapCanvas().mapRenderer().destinationCrs()
        transformer = QgsCoordinateTransform(source_crs, project_crs)
        return transformer

    def _get_feature_ids(self, layer):
        feature_ids = []
        feat = QgsFeature()
        iterator = layer.getFeatures()
        while iterator.nextFeature(feat):
            feature_ids.append(feat.id())
        return feature_ids

    def _run_edge_query(self, layer, id_attribute):

        # for each current and next features
        #   get the closest edge from current to next -> L1
        #   get the closest edge from next to current -> L2
        #   project L1's vertices on L2 and get their distance from L1
        #   project L2's vertices on L1 and get their distance from L2
        #   the pair with the smallest distance wins!
        result = []
        if layer.crs().geographicFlag():
            project_crs = self.iface.mapCanvas().mapRenderer().destinationCrs()
            measurer = self._get_measurer(project_crs)
            transformer = self._get_transformer(layer)
        else:
            measurer = self._get_measurer(layer.crs())
            transformer = None
        feature_ids = self._get_feature_ids(layer)
        current = QgsFeature()
        next_ = QgsFeature()
        i = 0
        j = 0
        while i < len(feature_ids):
            i_current = layer.getFeatures(QgsFeatureRequest(feature_ids[i]))
            i_current.nextFeature(current)
            current_id_attr = current.attribute(id_attribute)
            current_geom = current.geometry()
            j = i + 1
            while j < len(feature_ids):
                i_next = layer.getFeatures(QgsFeatureRequest(feature_ids[j]))
                i_next.nextFeature(next_)
                next_id_attr = next_.attribute(id_attribute)
                next_geom = next_.geometry()
                segments = self.get_closest_segments(current_geom, next_geom)
                current_segment, next_segment = segments
                candidates = []
                for current_vertex in current_segment:
                    projection = self.project_point(next_segment,
                                                    current_vertex,
                                                    measurer)
                    if projection is not None:
                        projected, distance = projection
                        candidates.append((current_vertex, projected,
                                          distance))
                for next_vertex in next_segment:
                    projection = self.project_point(current_segment,
                                                    next_vertex,
                                                    measurer)
                    if projection is not None:
                        projected, distance = projection
                        candidates.append((next_vertex, projected, distance))
                ordered_candidates = sorted(candidates, key=lambda c: c[2])
                winner = ordered_candidates[0]
                feat_result = {
                    'distance' : winner[2],
                    'from' : winner[0],
                    'to' : winner[1],
                    'from_attribute' : current_id_attr,
                    'to_attribute' : next_id_attr,
                }
                result.append(feat_result)
                j += 1
            i += 1
        return result

    def _get_centroid(self, geometry, transformer=None):
        '''
        Return the centroid of the polygon geometry as a QgsPoint.

        Inputs:

            geometry - A QgsGeometry

            transformer - A QgsCoordinateTransform object to convert the
                geometry's coordinates to a projected CRS. If None, no
                transformation is performed.
        '''

        centroid = geometry.centroid().asPoint()
        if transformer is not None:
            result = transformer.transform(centroid)
        else:
            result = centroid
        return result

    def get_closest_segments(self, geom1, geom2):
        '''
        return the closest line segments between geom1 and geom2.

        Inputs:

            geom1 - A QgsGeometry object of type Polygon

            geom2 - A QgsGeometry object of type Polygon

        Returns a two-element tuple with:
            - the closest segment in geom1
            - the closest segment in geom2

        A segment is a two-element list of QgsPoints with the vertices
        of the segment.
        '''

        pol1 = geom1.asPolygon()
        pol2 = geom2.asPolygon()
        segments1 = self._get_segments(pol1[0])
        segments2 = self._get_segments(pol2[0])
        closest_segments = []
        distance = None
        for seg1 in segments1:
            for seg2 in segments2:
                line1 = QgsGeometry.fromPolyline(seg1)
                line2 = QgsGeometry.fromPolyline(seg2)
                dist = line1.distance(line2)
                if distance is None or distance > dist:
                    distance = dist
                    closest_segments = (seg1, seg2)
        return closest_segments

    def _get_segments(self, line_string):
        '''
        Return the line segments that compose input line_string.

        Inputs:

            line_string - A QgsLineString

        Returns a list of two-element lists with QgsPoint objects that
        represent the segments of the input line_string.
        '''

        segments = []
        for index, pt1 in enumerate(line_string):
            if index < (len(line_string) - 1):
                pt2 = line_string[index+1]
                segments.append([pt1, pt2])
        return segments

    def project_point(self, line_segment, point, measurer):
        '''
        Project a point on a line segment.

        Inputs:

            line_segment - A two-element tuple of QgsPoint objects

            point - A QgsPoint representing the point to project.

            measurer - A QgsDistanceArea object

        Returns a two-element tuple with:
            - a QgsPoint representing the projection of the input point
            on the line segment or None in case the projection falls outside
            the segment
            - the distance between the input point and the projected point

        This code is adapted from:
            http://www.vcskicks.com/code-snippet/point-projection.php
        '''

        pt1, pt2 = line_segment
        try:
            m = (pt2.y() - pt1.y()) / (pt2.x() - pt1.x())
            b = pt1.y() - (m * pt1.x())
            x = (point.x() + m * point.y() - m * b) / (m * m + 1)
            y = (m * m * point.y() + m * point.x() + b) / (m * m + 1)
        except ZeroDivisionError:
            # line_string is paralel to y axis
            x = pt1.x()
            y = point.y()
        projected = QgsPoint(x, y)
        if self._is_on_the_line(projected, line_segment):
            distance = measurer.measureLine(point, projected)
            result = (projected, distance)
        else:
            result = None
        return result

    def _is_on_the_line(self, pt, line):
        result = False
        line_x1 = line[0].x()
        line_y1 = line[0].y()
        line_x2 = line[1].x()
        line_y2 = line[1].y()
        x = pt.x()
        y = pt.y()
        line_delta_x = abs(line_x2 - line_x1)
        norm_x = abs(x - line_x1)
        line_delta_y = abs(line_y2 - line_y1)
        norm_y = y - abs(line_y1)
        if norm_x < line_delta_x and norm_y < line_delta_y:
            result = True
        return result
