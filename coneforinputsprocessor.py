import os
import sys
import traceback
import codecs

from PyQt4.QtCore import *
from qgis.core import *

import utilities


class InvalidFeatureError(Exception):
    pass


class InputsProcessor(QObject):

    def __init__(self, project_crs):
        super(InputsProcessor, self).__init__()
        self.project_crs = project_crs
        self.global_progress = 0

    def run_queries(self, layers, output_dir,
                    only_selected_features=True,
                    save_text_files=True):
        '''
        Create the Conefor inputs files.

        Inputs:

            layers - A list of dictionaries that have the parameters of the
                layers to process. Each dictionary has the following key/value
                pairs:

                    - layer : a QgsMapLayer to be processed

                    - id_attribute : the name of the attribute to be used as
                      an id for Conefor queries

                    - attribute : the name of the attribute to use for the
                      attribute query. Can be None, resulting in no
                      attribute query being performed

                    - centroid_distance_name : the name for the shapefile
                      with centroid distances

                    - edge_distance_name : the name for the shapefile with
                      edge distances

            output_dir - The full path to the desired output directory;

            only_selected_features - A boolean indicating if the processing
                should be restricted to the currently selected features on
                each layer.

            save_text_files - A boolean indicating if the text files are to be
                saved to disk.
        '''

        self.emit(SIGNAL('update_info'), 'Processing started...')
        new_files = []
        layer_progress_step = 100.0 / len(layers)
        try:
            for index, layer_parameters in enumerate(layers):
                self.emit(SIGNAL('update_info'), 'layer: %s' % \
                                 layer_parameters['layer'].name())
                layer_files = self.process_layer(
                    layer_parameters['layer'],
                    layer_parameters['id_attribute'],
                    output_dir, 
                    attribute=layer_parameters['attribute'],
                    progress_step=layer_progress_step,
                    area_file_name=layer_parameters['area_file_name'],
                    attribute_file_name=layer_parameters['attribute_file_name'],
                    centroid_file_name=layer_parameters['centroid_file_name'],
                    edge_file_name=layer_parameters['edge_file_name'],
                    centroid_distance_file_name=layer_parameters['centroid_distance_name'],
                    edge_distance_file_name=layer_parameters['edge_distance_name'],
                    only_selected_features=only_selected_features,
                    add_vector_layers_out_dir=True
                )
                new_files += layer_files
            self.emit(SIGNAL('progress_changed'))
        except InvalidFeatureError as e:
            self.emit(SIGNAL('update_info'), 'ERROR: %s' % e)
        except Exception as e:
            traceback.print_exc()
            self.emit(SIGNAL('update_info'),
                      'ERROR: %s' % traceback.format_exc())
        else:
            self.emit(SIGNAL('update_info'), 'Processing finished!')
        finally:
            self.global_progress = 0
        return new_files

    def _get_output_file_name(self, directory, name):
        '''
        Rename the output name if it is already present in the directory.
        '''

        the_name, extension = os.path.splitext(name)
        path_already_exists = True
        index = 1
        while path_already_exists:
            if index == 1:
                tentative_name = '%s%s' % (the_name, extension)
            else:
                tentative_name = '%s%i%s' % (the_name, index, extension)
            tentative_path = os.path.join(directory, tentative_name)
            if not os.path.isfile(tentative_path):
                path_already_exists = False
            index += 1
        return tentative_name

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

        if file_type == 'ESRI Shapefile':
            if not output_name.endswith('.shp'):
                output_name = '%s.shp' % output_name
        output_name = self._get_output_file_name(output_dir, output_name)
        output_path = os.path.join(output_dir, output_name)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        fields = QgsFields()
        fields.append(QgsField('From_Node', QVariant.String, 'From_NodeID',
                      255))
        fields.append(QgsField('To_Node', QVariant.String, 'To_NodeID', 255))
        fields.append(QgsField('distance', QVariant.Double,
                      'distance', 255, 1))
        writer = QgsVectorFileWriter(output_path, encoding, fields,
                                     QGis.WKBLineString, crs, file_type)
        if writer.hasError() == QgsVectorFileWriter.NoError:
            for item in data:
                feat = QgsFeature()
                line = [item['from'], item['to']]
                feat.setGeometry(QgsGeometry.fromPolyline(line))
                feat.setFields(fields)
                feat.initAttributes(3)
                feat.setAttribute('From_Node', item['from_attribute'])
                feat.setAttribute('To_Node', item['to_attribute'])
                feat.setAttribute('distance', item['distance'])
                writer.addFeature(feat)
        else:
            print('Error when creating distances lines file: %s' % \
                  writer.hasError())
        del writer
        return output_path

    # unused?
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

    def _save_text_file(self, data, log_text, output_dir, output_name,
                        encoding, progress_step):
        self.emit(SIGNAL('update_info'), '%s' % log_text, 1)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        if not output_name.endswith('.txt'):
            output_name = '%s.txt' % output_name
        output_name = self._get_output_file_name(output_dir, output_name)
        sorted_data = sorted(data, key=lambda tup: tup[0])
        output_path = os.path.join(output_dir, output_name)
        with codecs.open(output_path, 'w', encoding) as file_handler:
            for tup in sorted_data:
                line = ''
                for item in tup:
                    line += '%s\t' % item
                line = line[:-1] + '\n'
                file_handler.write(line)
            # Conefor manual states that files should terminate with a blank
            # line
            file_handler.write('\n')
        self.global_progress += progress_step
        self.emit(SIGNAL('progress_changed'))
        return output_path

    def process_layer(self, layer, id_attribute, output_dir, attribute=None,
                      progress_step=0, area_file_name=None,
                      attribute_file_name=None, centroid_file_name=None,
                      edge_file_name=None, centroid_distance_file_name=None,
                      edge_distance_file_name=None,
                      only_selected_features=True,
                      add_vector_layers_out_dir=False):
        '''
        Process an individual layer.

        Inputs:

            layer - A QgsVector layer

            id_attribute - The name of the attribute to be used as id

            output_dir - The directory where the output files are to be saved

            attribute - The name of the attribute to be processed. If None,
                the attribute process does not take place

            progress_step - The ammount of progress available for using in
                this method

            area_file_name - A string with the name of the text file where
                the results from the area query will be written. A value of
                None will cause the area query to be skipped.

            attribute_file_name - A string with the name of the text file
                where the results from the attribute query will be written

            centroid_file_name - A string with the name of the text file where
                the results from the centroid distance query will be saved

            edge_file_name - A string with the name of the text file where the
                results from the edge distance query will be saved

            centroid_distance_file_name - A string with the name of the vector
                file for creating centroid distances. A value of None disables
                saving the vector file.

            edge_distance_file_name - A string with the name of the vector
                file for creating edge distances. A value of None disables
                saving the vector file.

            only_selected_features - A boolean indicating if the processing
                should be restricted to the currently selected features on
                each layer.

            add_vector_layers_out_dir - A boolean indicating if a dedicated
                subdirectory should be created under the input output_dir
                in order to store the vector files with the distances.
                Defaults to False.
        '''

        created_files = []
        encoding = layer.dataProvider().encoding()
        if encoding == 'System':
            encoding = sys.getfilesystemencoding()
        num_queries = self._determine_num_queries(attribute_file_name,
                                                  area_file_name,
                                                  centroid_file_name, 
                                                  edge_file_name)
        num_files_to_save = num_queries
        if centroid_distance_file_name is not None:
            num_files_to_save += 1
        if edge_distance_file_name is not None:
            num_files_to_save += 1
        running_queries_step = progress_step / 2.0
        each_query_step = running_queries_step / num_queries
        saving_files_step = progress_step - running_queries_step
        each_save_file_step = saving_files_step / num_files_to_save
        if attribute is not None and attribute_file_name is not None:
            output_path = os.path.join(output_dir, attribute_file_name)
            attribute_file = self._run_attribute_query(layer, id_attribute,
                                                       attribute, encoding,
                                                       only_selected_features,
                                                       each_query_step,
                                                       output_path,
                                                       each_save_file_step)
            if attribute_file is not None:
                created_files.append(attribute_file)
        if area_file_name is not None:
            output_path = os.path.join(output_dir, area_file_name)
            area_file = self._run_area_query(layer, id_attribute, encoding,
                                 only_selected_features, each_query_step,
                                 output_path, each_save_file_step)
            if area_file is not None:
                created_files.append(area_file)
        if centroid_file_name is not None or \
                centroid_distance_file_name is not None:
            try:
                output_path = os.path.join(output_dir, centroid_file_name)
            except (TypeError, AttributeError):
                output_path = None
            try:
                if add_vector_layers_out_dir:
                    shape_output_path = os.path.join(
                        output_dir,
                        'Link_vector_layers',
                        centroid_distance_file_name
                    )
                else:
                    shape_output_path = os.path.join(
                        output_dir,
                        centroid_distance_file_name
                    )
            except (TypeError, AttributeError):
                shape_output_path = None
            centroid_files = self._run_centroid_query(
                layer,
                id_attribute,
                encoding,
                only_selected_features,
                each_query_step,
                output_path,
                each_save_file_step,
                shape_output_path
            )
            created_files += centroid_files
        if edge_file_name is not None or edge_distance_file_name is not None:
            try:
                output_path = os.path.join(output_dir, edge_file_name)
            except (TypeError, AttributeError):
                output_path = None
            try:
                if add_vector_layers_out_dir:
                    shape_output_path = os.path.join(
                        output_dir,
                        'Link_vector_layers',
                        edge_distance_file_name
                    )
                else:
                    shape_output_path = os.path.join(
                        output_dir,
                        edge_distance_file_name
                    )
            except (TypeError, AttributeError):
                shape_output_path = None
            edge_files = self._run_edge_query(layer, id_attribute, encoding,
                                              only_selected_features,
                                              each_query_step, output_path,
                                              each_save_file_step,
                                              shape_output_path)
            created_files += edge_files
        self.global_progress = 100
        self.emit(SIGNAL('progress_changed'))
        return created_files

    def _determine_num_queries(self, attribute_file_name, area_file_name,
                               centroid_file_name, edge_file_name):
        '''
        Return the number of queries that will be processed.

        This method's main purpose is calculating progress steps.
        '''

        num_queries = 0
        if attribute_file_name is not None:
            num_queries += 1
        if area_file_name is not None:
            num_queries += 1
        if centroid_file_name is not None:
            num_queries += 1
        if edge_file_name is not None:
            num_queries += 1
        if num_queries == 0:
            num_queries = 1
        return num_queries

    def _run_attribute_query(self, layer, id_attribute, attribute, encoding,
                             use_selected, analysis_step, output_path,
                             file_save_progress_step=0):
        '''
        Process the attribute data query.

        Inputs:

            layer - A QgsVectorLayer object

            id_attribute - The name of the attribute that uniquely identifies
                each feature in the layer

            attribute - The name of the attribute to use in the processing
                query

            encoding - The encoding to use when processing the attributes and
                saving the results to disk

            use_selected - A boolean indicating if the processing is to be
                performed only on the selected features or on all features

            analysis_step - A number indicating the ammount of overall
                progress is to be added after this processing is done

            output_path - The full path to the text file where the results
                are to be saved.

            file_save_progress_step - A number indicating the ammount of 
                overall progress to be added after saving the text file with
                the results
        '''

        self.emit(SIGNAL('update_info'), 'Running attribute query...', 1)
        data = []
        features = utilities.get_features(layer, use_selected)
        for feat in features:
            id_attr = self._get_numeric_attribute(feat, id_attribute)
            attr = self._get_numeric_attribute(feat, attribute, float)
            if attr is not None and id_attr is not None:
                if attr < 0:
                    raise ValueError('Attribute must be non negative')
                else:
                    data.append((id_attr, attr))
        self.global_progress += analysis_step
        self.emit(SIGNAL('progress_changed'))
        output_dir, output_name = os.path.split(output_path)
        output_file = self._save_text_file(data, 'Writing attribute file...',
                                           output_dir, output_name, encoding,
                                           file_save_progress_step)
        return output_file

    def _get_numeric_attribute(self, feature, attribute_name, type_=int):
        the_attribute = feature.attribute(attribute_name)
        result = None
        if the_attribute != NULL:
            result = type_(the_attribute)
        return result

    def _run_area_query(self, layer, id_attribute, encoding, use_selected,
                        analysis_step, output_path, file_save_progress_step=0):
        '''
        Process the area data query.

        Inputs:

            layer - A QgsVectorLayer object

            id_attribute - The name of the attribute that uniquely identifies
                each feature in the layer

            encoding - The encoding to use when processing the attributes and
                saving the results to disk

            use_selected - A boolean indicating if the processing is to be
                performed only on the selected features or on all features

            analysis_step - A number indicating the ammount of overall
                progress is to be added after this processing is done

            output_path - The full path to the text file where the results
                are to be saved.

            file_save_progress_step - A number indicating the ammount of 
                overall progress to be added after saving the text file with
                the results
        '''

        self.emit(SIGNAL('update_info'), 'Running area query...', 1)
        data = []
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
        features = utilities.get_features(layer, use_selected)
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
            id_attr = self._get_numeric_attribute(feat, id_attribute)
            if id_attr is not None:
                data.append((id_attr, total_feat_area))
        self.global_progress += analysis_step
        self.emit(SIGNAL('progress_changed'))
        output_file = None
        if any(data):
            output_dir, output_name = os.path.split(output_path)
            output_file = self._save_text_file(data, 'Writing area file...',
                                               output_dir, output_name,
                                               encoding,
                                               file_save_progress_step)
        return output_file

    def _run_centroid_query(self, layer, id_attribute, encoding, use_selected,
                            analysis_step, output_path=None,
                            file_save_progress_step=0,
                            shape_file_path=None):
        self.emit(SIGNAL('update_info'), 'Running centroid query...', 1)
        data = []
        if layer.crs().geographicFlag():
            measurer = self._get_measurer(self.project_crs)
            transformer = self._get_transformer(layer)
        else:
            measurer = self._get_measurer(layer.crs())
            transformer = None
        feature_ids = [f.id() for f in utilities.get_features(layer, use_selected)]
        i = 0
        j = 0
        while i < len(feature_ids):
            features = utilities.get_features(layer, use_selected, feature_ids[i])
            current = iter(features).next()
            c_id_attr = self._get_numeric_attribute(current, id_attribute)
            if c_id_attr is not None:
                current_geom = current.geometry()
                geometry_errors = current_geom.validateGeometry()
                if any(geometry_errors):
                    raise InvalidFeatureError('Layer: %s - Feature %s has '
                                              'geometry errors. Aborting...' \
                                              % (layer.name(), c_id_attr))
                elif current_geom.isMultipart():
                    raise InvalidFeatureError('Feature %s is multipart. '
                                              'Aborting...' % c_id_attr)
                orig_curr_centroid = current_geom.centroid().asPoint()
                trans_curr_centroid = self._transform_point(orig_curr_centroid,
                                                            transformer)
                j = i + 1
                while j < len(feature_ids):
                    features = utilities.get_features(layer, use_selected,
                                                feature_ids[j])
                    next_ = iter(features).next()
                    n_id_attr = self._get_numeric_attribute(next_, id_attribute)
                    if n_id_attr is not None:
                        next_geom = next_.geometry()
                        orig_n_centroid = next_geom.centroid().asPoint()
                        trans_n_centroid = self._transform_point(orig_n_centroid,
                                                                    transformer)
                        distance = measurer.measureLine(trans_curr_centroid,
                                                        trans_n_centroid)
                        feat_result = {
                            'current' : {
                                'attribute' : c_id_attr,
                                'centroid' : orig_curr_centroid,
                                'feature_geometry' : current_geom,
                            },
                            'next' : {
                                'attribute' : n_id_attr,
                                'centroid' : orig_n_centroid,
                                'feature_geometry' : next_geom,
                            },
                            'distance' : distance,
                        }
                        data.append(feat_result)
                    j += 1
            i += 1
        output_files = []
        if any(data):
            if output_path is not None:
                output_dir, output_name = os.path.split(output_path)
                data_to_write = []
                for c_dict in data:
                    current_id = c_dict['current']['attribute']
                    next_id = c_dict['next']['attribute']
                    distance = c_dict['distance']
                    data_to_write.append((current_id, next_id, distance))
                output_file = self._save_text_file(data_to_write,
                                                   'Writing centroids file...',
                                                   output_dir, output_name, 
                                                   encoding,
                                                   file_save_progress_step)
                output_files.append(output_file)
            if shape_file_path is not None:
                output_dir, output_name = os.path.split(shape_file_path)
                self.emit(SIGNAL('update_info'), 'Creating centroid distance file', 1)
                if not os.path.isdir(output_dir):
                    os.mkdir(output_dir)
                #self.emit(SIGNAL('update_info'), 'centroids...', 2)
                data_to_write = []
                for c_dict in data:
                    the_data = {
                        'from' : c_dict['current']['centroid'],
                        'to' : c_dict['next']['centroid'],
                        'distance' : c_dict['distance'],
                        'from_attribute' : c_dict['current']['attribute'],
                        'to_attribute' : c_dict['next']['attribute'],
                    }
                    data_to_write.append(the_data)
                output_shape = self._write_distance_file(data_to_write,
                                                         output_dir,
                                                         output_name,
                                                         encoding, layer.crs())
                output_files.append(output_shape)
                self.global_progress += file_save_progress_step
                self.emit(SIGNAL('progress_changed'))
        return output_files

    def _get_measurer(self, source_crs):
        measurer = QgsDistanceArea()
        measurer.setEllipsoidalMode(False)
        measurer.setSourceCrs(source_crs.postgisSrid())
        return measurer

    def _get_transformer(self, layer):
        source_crs = layer.crs()
        transformer = QgsCoordinateTransform(source_crs, self.project_crs)
        return transformer

    def _run_edge_query(self, layer, id_attribute, encoding, use_selected,
                        analysis_step, output_path=None,
                        file_save_progress_step=0, 
                        shape_file_path=None):
        # for each current and next features
        #   get the closest edge from current to next -> L1
        #   get the closest edge from next to current -> L2
        #   project L1's vertices on L2 and get their distance from L1
        #   project L2's vertices on L1 and get their distance from L2
        #   the pair with the smallest distance wins!
        self.emit(SIGNAL('update_info'), 'Running edge query...', 1)
        data = []
        if layer.crs().geographicFlag():
            measurer = self._get_measurer(self.project_crs)
            transformer = self._get_transformer(layer)
        else:
            measurer = self._get_measurer(layer.crs())
            transformer = None
        feature_ids = [f.id() for f in utilities.get_features(layer, use_selected)]
        i = 0
        j = 0
        while i < len(feature_ids):
            features = utilities.get_features(layer, use_selected, 
                                              feature_ids[i])
            current = iter(features).next()
            c_id_at = self._get_numeric_attribute(current, id_attribute)
            if c_id_at is not None:
                current_geom = current.geometry()
                geometry_errors = current_geom.validateGeometry()
                if any(geometry_errors):
                    raise InvalidFeatureError('Layer: %s - Feature %s has '
                                              'geometry errors. Aborting...' \
                                              % (layer.name(), c_id_at))
                elif current_geom.isMultipart():
                    raise InvalidFeatureError('Feature %s is multipart. '
                                              'Aborting...' % c_id_at)
                current_poly = self._get_polygon(current_geom, transformer)
                j = i + 1
                while j < len(feature_ids):
                    features = utilities.get_features(layer, use_selected,
                                                      feature_ids[j])
                    next_ = iter(features).next()
                    n_id_at = self._get_numeric_attribute(next_, id_attribute)
                    if n_id_at is not None:
                        next_geom = next_.geometry()
                        next_poly = self._get_polygon(next_geom, transformer)
                        segments = self.get_closest_segments(current_poly,
                                                             next_poly)
                        current_segment, next_segment = segments
                        candidates = []
                        for current_vertex in current_segment:
                            candidate = self.find_candidate_points(
                                current_vertex,
                                next_segment,
                                measurer
                            )
                            candidates.append(candidate)
                        for next_vertex in next_segment:
                            candidate = self.find_candidate_points(
                                next_vertex,
                                current_segment,
                                measurer
                            )
                            candidates.append(candidate)
                        ordered_candidates = sorted(candidates, 
                                                    key=lambda c: c[2])
                        winner = ordered_candidates[0]
                        # transform the winner's coordinates back to layer crs
                        from_restored = self._transform_point(winner[0],
                                                              transformer,
                                                              reverse=True)
                        to_restored = self._transform_point(winner[1],
                                                            transformer,
                                                            reverse=True)
                        feat_result = {
                            'distance' : winner[2],
                            'from' : from_restored,
                            'to' : to_restored,
                            'from_attribute' : c_id_at,
                            'to_attribute' : n_id_at,
                        }
                        data.append(feat_result)
                    j += 1
            i += 1
        output_files = []
        if any(data):
            if output_path is not None:
                output_dir, output_name = os.path.split(output_path)
                data_to_write = []
                for e_dict in data:
                    from_id = e_dict['from_attribute']
                    to_id = e_dict['to_attribute']
                    distance = e_dict['distance']
                    data_to_write.append((from_id, to_id, distance))
                output_file = self._save_text_file(data_to_write, 'Writing '
                                                   'edges file...',
                                                   output_dir, output_name,
                                                   encoding,
                                                  file_save_progress_step)
                output_files.append(output_file)
            if shape_file_path is not None:
                output_dir, output_name = os.path.split(shape_file_path)
                self.emit(SIGNAL('update_info'), 'Creating edge distance file', 1)
                if not os.path.isdir(output_dir):
                    os.mkdir(output_dir)
                self.emit(SIGNAL('update_info'), 'edges...', 2)
                output_shape = self._write_distance_file(data, output_dir,
                                                         output_name, encoding,
                                                         layer.crs())
                output_files.append(output_shape)
                self.global_progress += file_save_progress_step
                self.emit(SIGNAL('progress_changed'))
        return output_files

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
