import os
import sys
import codecs

from PyQt4.QtCore import *
from qgis.core import *

class NoFeaturesToProcessError(Exception):
    pass


class InputsProcessor(QObject):

    def __init__(self, project_crs):
        super(InputsProcessor, self).__init__()
        self.project_crs = project_crs
        self.global_progress = 0

    def run_queries(self, layers, output_dir, create_distance_files,
                    only_selected_features):
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

            only_selected_features - A boolean indicating if the processing
                should be restricted to the currently selected features on
                each layer.
        '''

        self.emit(SIGNAL('update_info'), 'Processing started...')
        layer_progress_step = 100.0 / len(layers)
        for index, layer_parameters in enumerate(layers):
            try:
                self.emit(SIGNAL('update_info'), 'layer: %s' % \
                                 layer_parameters['layer'].name())
                self.process_layer(layer_parameters['layer'],
                                   layer_parameters['id_attribute'],
                                   layer_parameters['area'],
                                   layer_parameters['attribute'],
                                   layer_parameters['centroid_distance'],
                                   layer_parameters['edge_distance'],
                                   output_dir, layer_progress_step,
                                   create_distance_files,
                                   only_selected_features)
            except NoFeaturesToProcessError:
                print('Layer %s has no features to process' % \
                      layer_parameters['layer'].name())
            self.emit(SIGNAL('progress_changed'))
        self.emit(SIGNAL('update_info'), 'Processing finished!')
        self.global_progress = 0

    def _write_file(self, data, output_dir, output_name, encoding):
        '''
        Write a text file with the input data.

        Inputs:

            data - A list of two element tuples

            output_dir - The output directory where the file is to be written

            output_name - The name of the file to write

            encoding - A string with the encoding to use for writing the new
                file.

        Before being written, the data is sorted by the first element in the
        tuple.
        '''

        sorted_data = sorted(data, key=lambda tup: tup[0])
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        output_path = os.path.join(output_dir, output_name)
        with codecs.open(output_path, 'w', encoding) as file_handler:
            for line in sorted_data:
                file_handler.write(line)

    def _write_distance_file(self, data, output_dir, output_name, encoding,
                             crs, file_type='ESRI Shapefile',
                             load_to_canvas=True):
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

            load_to_canvas - A boolean indicating if the newly saved file
                should be loaded into QGIS' map canvas.
        '''

        output_path = os.path.join(output_dir, output_name)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
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
                from_to = u'%s_%s' % (item['from_attribute'],
                                      item['to_attribute'])
                line = [item['from'], item['to']]
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
        if load_to_canvas:
            new_layer = QgsVectorLayer(output_path, output_name, 'ogr')
            registry = QgsMapLayerRegistry.instance()
            registry.addMapLayer(new_layer)

    def _decode_attribute(self, the_attr, encoding):
        '''
        Decode the byte string the_attr to Unicode.

        Inputs:

            the_attr - a byte string

            encoding - a string with the encoding to use when decoding to
                Unicode.

        Returns a unicode string.
        '''

        if not isinstance(the_attr, basestring):
            the_attr = str(the_attr)
        if isinstance(the_attr, unicode):
            uni_str = the_attr
        else:
            uni_str = unicode(the_attr, encoding)
        return uni_str

    def process_layer(self, layer, id_attribute, area, attribute,
                      centroid, edge, output_dir, progress_step,
                      create_distance_files, only_selected_features,
                      load_distance_files_to_canvas=True):
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

            only_selected_features - A boolean indicating if the processing
                should be restricted to the currently selected features on
                each layer.

            load_distance_files_to_canvas - A boolean indicating if the
                distance files are to be loaded into QGIS' mapCanvas.
        '''

        encoding = layer.dataProvider().encoding()
        if encoding == 'System':
            encoding = sys.getfilesystemencoding()
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
            self.emit(SIGNAL('update_info'), 'Running attribute query...', 1)
            attribute_data = self._run_attribute_query(layer, id_attribute,
                                                       attribute, encoding,
                                                       only_selected_features)
            self.global_progress += each_query_step
            self.emit(SIGNAL('progress_changed'))
        area_data = []
        if area:
            self.emit(SIGNAL('update_info'), 'Running area query...', 1)
            area_data = self._run_area_query(layer, id_attribute, encoding,
                                             only_selected_features)
            self.global_progress += each_query_step
            self.emit(SIGNAL('progress_changed'))
        centroid_data = []
        if centroid:
            self.emit(SIGNAL('update_info'), 'Running centroid query...', 1)
            centroid_data = self._run_centroid_query(layer, id_attribute,
                                                     encoding,
                                                     only_selected_features)
            self.global_progress += each_query_step
            self.emit(SIGNAL('progress_changed'))
        edge_data = []
        if edge:
            self.emit(SIGNAL('update_info'), 'Running edge query...', 1)
            edge_data = self._run_edge_query(layer, id_attribute, encoding,
                                             only_selected_features)
            self.global_progress += each_query_step
            self.emit(SIGNAL('progress_changed'))
        if any(attribute_data):
            self.emit(SIGNAL('update_info'), 'Writing attribute file...', 1)
            output_name = 'nodes_%s_%s' % (attribute, layer.name())
            self._write_file(attribute_data, output_dir, output_name, encoding)
            self.global_progress += each_save_file_step
            self.emit(SIGNAL('progress_changed'))
        if any(area_data):
            self.emit(SIGNAL('update_info'), 'Writing area file...', 1)
            output_name = 'nodes_calculated_area_%s' % layer.name()
            self._write_file(area_data, output_dir, output_name, encoding)
            self.global_progress += each_save_file_step
            self.emit(SIGNAL('progress_changed'))
        if any(centroid_data):
            self.emit(SIGNAL('update_info'), 'Writing centroids file...', 1)
            output_name = 'distances_centroids_%s' % layer.name()
            data_to_write = []
            for c_dict in centroid_data:
                current_id = c_dict['current']['attribute']
                next_id = c_dict['next']['attribute']
                distance = c_dict['distance']
                data_to_write.append('%s\t%s\t%s\n' % (current_id, next_id,
                                     distance))
            self._write_file(data_to_write, output_dir, output_name, encoding)
            self.global_progress += each_save_file_step
            self.emit(SIGNAL('progress_changed'))
        if any(edge_data):
            self.emit(SIGNAL('update_info'), 'Writing edges file...', 1)
            output_name = 'distances_edges_%s' % layer.name()
            data_to_write = []
            for e_dict in edge_data:
                from_id = e_dict['from_attribute']
                to_id = e_dict['to_attribute']
                distance = e_dict['distance']
                data_to_write.append('%s\t%s\t%s\n' % (from_id, to_id,
                                     distance))
            self._write_file(data_to_write, output_dir, output_name, encoding)
            self.global_progress += each_save_file_step
            self.emit(SIGNAL('progress_changed'))
        if create_distance_files:
            self.emit(SIGNAL('update_info'), 'Creating distance files', 1)
            output_dir = os.path.join(output_dir, 'distance_files')
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)
            if any(centroid_data):
                self.emit(SIGNAL('update_info'), 'centroids...', 2)
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
                self._write_distance_file(
                    data_to_write, 
                    output_dir, 
                    output_name, 
                    encoding, 
                    layer.crs(),
                    load_to_canvas=load_distance_files_to_canvas
                )
                self.global_progress += each_save_file_step
                self.emit(SIGNAL('progress_changed'))
            if any(edge_data):
                self.emit(SIGNAL('update_info'), 'edges...', 2)
                output_name = 'edge_distances_%s' % layer.name()
                self._write_distance_file(
                    edge_data, 
                    output_dir, 
                    output_name,
                    encoding, 
                    layer.crs(),
                    load_to_canvas=load_distance_files_to_canvas
                )
                self.global_progress += each_save_file_step
                self.emit(SIGNAL('progress_changed'))
            self.global_progress = 100

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

    def _run_attribute_query(self, layer, id_attribute, attribute, encoding,
                             use_selected):
        result = []
        features = self._get_features(layer, use_selected)
        for feat in features:
            id_attr = self._decode_attribute(feat.attribute(id_attribute),
                                            encoding)
            attr = self._decode_attribute(feat.attribute(attribute),
                                            encoding)
            result.append('%s\t%s\n' % (id_attr, attr))
        return result

    def _run_area_query(self, layer, id_attribute, encoding, use_selected):
        result = []
        if layer.crs().geographicFlag():
            if self.project_crs.geographicFlag():
                print('Neither the layer nor the project\'s coordinate ' \
                        'system is projected. The area calculation will not ' \
                        'be acurate.')
            measurer = self._get_measurer(self.project_crs)
            transformer = self._get_transformer(layer)
        else:
            measurer = self._get_measurer(layer.crs())
            transformer = None
        features = self._get_features(layer, use_selected)
        for feat in features:
            polygon = feat.geometry().asPolygon()
            new_polygon = []
            for ring in polygon:
                new_ring = []
                for point in ring:
                    if transformer is None:
                        new_ring.append(point)
                    else:
                        new_ring.append(transformer.transform(point))
                new_polygon.append(new_ring)
            outer_area = measurer.measurePolygon(new_polygon[0])
            hole_areas = 0
            if len(new_polygon) > 1:
                holes = new_polygon[1:]
                for hole in holes:
                    hole_areas += measurer.measurePolygon(hole)
            total_feat_area = outer_area - hole_areas
            id_attr = self._decode_attribute(feat.attribute(id_attribute),
                                             encoding)
            result.append('%s\t%s\n' % (id_attr, total_feat_area))
        return result

    def _get_features(self, layer, use_selected, filter_id=None):
        '''
        Return the features to process.

        Inputs:

            layer - A QgsVectorLayer

            use_selected - A boolean indicating if only the selected features
                should be used

            filter_id - The id of a feature to extract. If None (the default),
                the result will contain all the features (or all the selected
                features in case the use_selected argument isTrue)

        The output can be either a QgsFeatureIterator or a python list
        with the features. Both datatypes are suitable for using inside a
        for loop.

        If the use_selected argument is True but there are no features
        currently selected, all the features in the layer will be returned.
        '''

        features = []
        if use_selected:
            features = layer.selectedFeatures()
            if filter_id is not None:
                features = [f for f in features if f.id() == filter_id]
        if not any(features):
            if filter_id is not None:
                request = QgsFeatureRequest(filter_id)
                features = layer.getFeatures(request)
            else:
                features = layer.getFeatures()
        return features

    def _run_centroid_query(self, layer, id_attribute, encoding, use_selected):
        result = []
        if layer.crs().geographicFlag():
            measurer = self._get_measurer(self.project_crs)
            transformer = self._get_transformer(layer)
        else:
            measurer = self._get_measurer(layer.crs())
            transformer = None
        feature_ids = [f.id() for f in self._get_features(layer, use_selected)]
        i = 0
        j = 0
        while i < len(feature_ids):
            features = self._get_features(layer, use_selected, feature_ids[i])
            current = iter(features).next()
            c_id_attr = self._decode_attribute(current.attribute(id_attribute),
                                               encoding)
            current_geom = current.geometry()
            orig_curr_centroid = current_geom.centroid().asPoint()
            trans_curr_centroid = self._transform_point(orig_curr_centroid,
                                                         transformer)
            j = i + 1
            while j < len(feature_ids):
                features = self._get_features(layer, use_selected,
                                              feature_ids[j])
                next_ = iter(features).next()
                n_id_attr = self._decode_attribute(next_.attribute(id_attribute),
                                                   encoding)

                next_geom = next_.geometry()
                orig_next_centroid = next_geom.centroid().asPoint()
                trans_next_centroid = self._transform_point(orig_next_centroid,
                                                            transformer)
                distance = measurer.measureLine(trans_curr_centroid,
                                                trans_next_centroid)
                feat_result = {
                    'current' : {
                        'attribute' : c_id_attr,
                        'centroid' : orig_curr_centroid,
                        'feature_geometry' : current_geom,
                    },
                    'next' : {
                        'attribute' : n_id_attr,
                        'centroid' : orig_next_centroid,
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
        transformer = QgsCoordinateTransform(source_crs, self.project_crs)
        return transformer

    def _run_edge_query(self, layer, id_attribute, encoding, use_selected):

        # for each current and next features
        #   get the closest edge from current to next -> L1
        #   get the closest edge from next to current -> L2
        #   project L1's vertices on L2 and get their distance from L1
        #   project L2's vertices on L1 and get their distance from L2
        #   the pair with the smallest distance wins!
        result = []
        if layer.crs().geographicFlag():
            measurer = self._get_measurer(self.project_crs)
            transformer = self._get_transformer(layer)
        else:
            measurer = self._get_measurer(layer.crs())
            transformer = None
        feature_ids = [f.id() for f in self._get_features(layer, use_selected)]
        i = 0
        j = 0
        while i < len(feature_ids):
            features = self._get_features(layer, use_selected, feature_ids[i])
            current = iter(features).next()
            c_id_at = self._decode_attribute(current.attribute(id_attribute),
                                             encoding)
            current_geom = current.geometry()
            current_poly = self._get_polygon(current_geom, transformer)
            j = i + 1
            while j < len(feature_ids):
                features = self._get_features(layer, use_selected,
                                              feature_ids[j])
                next_ = iter(features).next()
                n_id_at = self._decode_attribute(next_.attribute(id_attribute),
                                                   encoding)
                next_geom = next_.geometry()
                next_poly = self._get_polygon(next_geom, transformer)
                segments = self.get_closest_segments(current_poly, next_poly)
                current_segment, next_segment = segments
                candidates = []
                for current_vertex in current_segment:
                    candidate = self.find_candidate_points(current_vertex,
                                                           next_segment,
                                                           measurer)
                    candidates.append(candidate)
                for next_vertex in next_segment:
                    candidate = self.find_candidate_points(next_vertex,
                                                           current_segment,
                                                           measurer)
                    candidates.append(candidate)
                ordered_candidates = sorted(candidates, key=lambda c: c[2])
                winner = ordered_candidates[0]
                # transform the winner's coordinates back to layer crs
                from_restored = self._transform_point(winner[0], transformer,
                                                      reverse=True)
                to_restored = self._transform_point(winner[1], transformer,
                                                    reverse=True)
                feat_result = {
                    'distance' : winner[2],
                    'from' : from_restored,
                    'to' : to_restored,
                    'from_attribute' : c_id_at,
                    'to_attribute' : n_id_at,
                }
                result.append(feat_result)
                j += 1
            i += 1
        return result

    def find_candidate_points(self, point, line_segment, measurer):
        projected, distance = self.project_point(line_segment, point, measurer)
        if self._is_on_the_segment(projected, line_segment):
            candidate = (point, projected, distance)
        else:
            close_vertex = self.get_closest_vertex(projected, line_segment,
                                                   measurer)
            distance = measurer.measureLine(point, close_vertex)
            candidate = (point, close_vertex, distance)
        return candidate

    def _transform_point(self, point, transformer=None,
                         reverse=False):
        '''
        Transform a point from a CRS to another using a transformer.

        Inputs:

            point - A QgsPoint object with the point to transform

            transformer - A QgsCoordinateTransform object configured
                with the source and destination CRSs. If None (the default),
                no transformation is needed, and the returned result is
                the same as the input point

            reverse - A boolean indicating if the reverse transformation
                is desired. Defaults to False, indicating that a forward
                transform is to be processed

        Returns a QgsPoint object with the transformed coordinates.
        '''

        if transformer is not None:
            if reverse:
                result = transformer.transform(
                            point,
                            QgsCoordinateTransform.ReverseTransform
                         )
            else:
                result = transformer.transform(point)
        else:
            result = point
        return result

    def get_closest_segments(self, poly1, poly2):
        '''
        return the closest line segments between poly1 and poly2.

        Inputs:

            poly1 - A QgsPolygon object

            poly2 - A QgsPolygon object

        Returns a two-element tuple with:
            - the closest segment in poly1
            - the closest segment in poly2

        A segment is a two-element list of QgsPoints with the vertices
        of the segment.
        '''

        segments1 = self._get_segments(poly1[0])
        segments2 = self._get_segments(poly2[0])
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

    def _get_polygon(self, geometry, transformer=None):
        '''
        Convert a geometry to polygon and transform its coordinates.

        Inputs:

            geometry - A QgsGeometry object to be converted

            transformer - A QgsCoordinateTransform object configured
                with the source and destination CRSs. If None (the default),
                no transformation is needed, and the returned result is
                the same as the input

        Returns a QgsPolygon object with the transformed coordinates of the
        geometry.
        '''

        if transformer is not None:
            geometry.transform(transformer)
        return geometry.asPolygon()

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
            on the line segment
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
        distance = measurer.measureLine(point, projected)
        return projected, distance

    def _is_on_the_segment(self, pt, line):
        result = False
        p1, p2 = line
        min_x, max_x = sorted((p1.x(), p2.x()))
        min_y, max_y = sorted((p1.y(), p2.y()))
        if (min_x < pt.x() < max_x) and (min_y < pt.y() < max_y):
            result = True
        return result

    def get_closest_vertex(self, pt, line, measurer):
        '''
        Return the closest vertex to an input point.

        Inputs:

            pt - A QgsPoint representing the point to analyze

            line - A QgsLineString representing the line to analyze.

            measurer - A QgsDistanceArea object used to measure the distance

        Returns a QgsPoint of the vertex of the line that is closest to the
        input point.
        '''

        distance = None
        closest = None
        for vertex in line:
            dist = measurer.measureLine(pt, vertex)
            if distance is None or distance > dist:
                closest = vertex
                distance = dist
        return closest
