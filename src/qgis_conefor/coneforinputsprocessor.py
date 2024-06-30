import functools
import os
import sys
import traceback
import codecs
from pathlib import Path
from typing import (
    Callable,
    Optional,
)

import qgis.core
from qgis.PyQt import QtCore

from . import utilities
from . import schemas
from .utilities import log


class InvalidFeatureError(Exception):
    pass


class InvalidAttributeError(Exception):
    pass


class InputsProcessor(QtCore.QObject):

    global_progress: int
    update_info = QtCore.pyqtSignal(str, int)
    progress_changed = QtCore.pyqtSignal()

    def __init__(self, project_crs):
        super(InputsProcessor, self).__init__()
        self.project_crs = project_crs
        self.global_progress = 0

    def run_queries(
            self,
            layers: list[schemas.ConeforInputParameters],
            output_dir: str,
            only_selected_features: bool = True,
    ):
        """
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
        """

        self.update_info.emit("Processing started", 0)
        new_files = []
        layer_progress_step = 100 // len(layers)
        try:
            for index, layer_params in enumerate(layers):
                self.update_info.emit(f"layer: {layer_params.layer.name()}", 0)
                layer_files = self.process_layer(
                    layer_params,
                    output_dir,
                    progress_step=layer_progress_step,
                    only_selected_features=only_selected_features,
                    add_vector_layers_out_dir=True
                )
                new_files += layer_files
            self.progress_changed.emit()
        except InvalidFeatureError as err:
            self.update_info.emit(f"ERROR: {err}", 0)
        except InvalidAttributeError as err:
            self.update_info.emit(
                f"ERROR: Selected attributes are not present in every layer - {err}",
                0
            )
        except Exception:
            traceback.print_exc()
            self.update_info.emit(f"ERROR: {traceback.format_exc()}", 0)
        else:
            self.update_info.emit("Processing finished!", 0)
        finally:
            self.global_progress = 0
        return new_files

    def process_layer(
            self,
            layer_params: schemas.ConeforInputParameters,
            output_dir: str,
            attribute=None,
            progress_step: int = 0,
            only_selected_features=True,
            add_vector_layers_out_dir=False
    ):
        """
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
        """

        created_files = []
        encoding = layer_params.layer.dataProvider().encoding()
        if encoding == 'System':
            encoding = sys.getfilesystemencoding()
        num_queries = self._determine_num_queries(layer_params)
        num_files_to_save = num_queries
        if layer_params.centroid_file_name is not None:
            num_files_to_save += 1
        if layer_params.edge_file_name is not None:
            num_files_to_save += 1
        # assuming that the actual processing will take 90% of the time
        # and saving the results to file will take only 10%
        running_queries_step = progress_step * 0.9
        # the attribute query is pretty fast, when compared to the others
        # so we assign it a small progress step
        if num_queries > 1:
            if attribute is not None:
                attribute_query_step = running_queries_step * 0.1
                each_query_step = (
                        (running_queries_step - attribute_query_step) /
                        (num_queries - 1)
                )
            else:
                each_query_step = (running_queries_step / num_queries)
        elif num_queries == 1:
            each_query_step = running_queries_step / num_queries
            attribute_query_step = each_query_step

        saving_files_step = progress_step - running_queries_step
        attribute_query_step = int(attribute_query_step)
        each_query_step = int(each_query_step)
        each_save_file_step = int(saving_files_step / num_files_to_save)
        if all(
                (
                        layer_params.attribute_field_name,
                        layer_params.attribute_file_name
                )
        ):
            output_path = Path(output_dir) / layer_params.attribute_file_name
            attribute_file_path = self._run_attribute_query(
                layer_params,
                only_selected_features,
                attribute_query_step,
                output_path,
                each_save_file_step
            )
            created_files.append(str(attribute_file_path))
        if layer_params.area_file_name is not None:
            output_path = os.path.join(output_dir, layer_params.area_file_name)
            area_file_path = self._run_area_query(
                layer_params,
                encoding,
                only_selected_features,
                each_query_step,
                output_path,
                each_save_file_step
            )
            created_files.append(area_file_path)
        if any((layer_params.centroid_file_name, layer_params.centroid_distance_name)):
            try:
                output_path = os.path.join(output_dir, layer_params.centroid_file_name)
            except (TypeError, AttributeError):
                output_path = None
            try:
                if add_vector_layers_out_dir:
                    shape_output_path = os.path.join(
                        output_dir,
                        'Link_vector_layers',
                        layer_params.centroid_distance_name,
                    )
                else:
                    shape_output_path = os.path.join(
                        output_dir,
                        layer_params.centroid_distance_name,
                    )
            except (TypeError, AttributeError):
                shape_output_path = None
            centroid_files = self._run_centroid_query(
                layer_params,
                encoding,
                only_selected_features,
                each_query_step,
                output_path,
                each_save_file_step,
                shape_output_path
            )
            created_files += centroid_files
        created_files += self._perform_edge_query(
            layer_params,
            encoding,
            only_selected_features,
            each_query_step,
            each_save_file_step,
            output_dir,
            add_vector_layers_out_dir
        )
        self.progress_changed.emit()
        return created_files

    def _perform_edge_query(
            self,
            layer_params: schemas.ConeforInputParameters,
            encoding,
            use_selected,
            analysis_step,
            file_save_step,
            output_dir: str,
            create_vector_dir=False
    ) -> list[str]:
        """
        Inputs:

            text_file - A string with the name of the text file where the
                        edge distances are to be stored. If None, no text file
                        will be saved, but the analysis will still be performed
            shape_file - A string with the name of the shape file where the
                         vector layer holding the edge distances is to be
                         stored. If None, no shape_file will be saved and a
                         faster algorithm is used to calculate the distances.
                         There are two algorithms for calculating edge
                         distances:

                         - slow algorithm. Pure python implementation of edge
                           distance calculation. This method is slower, but
                           provides the output coordinates for the distance
                           points, therefore allowing a vector layer to be
                           created to show the distances;
                         - fast algorithm. Uses QGIS (and therefore GEOS) own
                           edge_distance calculation, which is implemented
                           directly in C++. This method is faster, but
                           unfortunately does not provide the coordinates of
                           the points, only the value of the shortest edge
                           distance. As such, this method cannot be used to
                           create a vector layer showing the distances.
        """

        if layer_params.edge_distance_name:
            # must calculate edge distances AND must plot them -> slow method
            # may not need to save the distances.txt file
            try:
                if create_vector_dir:
                    shape_output_path = os.path.join(
                        output_dir,
                        'Link_vector_layers',
                        layer_params.edge_distance_name
                    )
                else:
                    shape_output_path = os.path.join(
                        output_dir,
                        layer_params.edge_distance_name
                    )
            except (TypeError, AttributeError):
                shape_output_path = None
            if layer_params.edge_file_name:
                # must save the distances.txt file
                try:
                    text_out_path = os.path.join(
                        output_dir, layer_params.edge_file_name)
                except (TypeError, AttributeError):
                    text_out_path = None
            else:
                text_out_path = None
            edge_files = self._run_edge_query(
                layer_params,
                encoding,
                use_selected,
                analysis_step,
                output_path=text_out_path,
                file_save_progress_step=file_save_step,
                shape_file_path=shape_output_path
            )
        else:
            # will not plot edge distances -> fast method
            # may need to save the distances.txt file
            if layer_params.edge_file_name is not None:
                try:
                    text_out_path = os.path.join(
                        output_dir, layer_params.edge_file_name)
                except (TypeError, AttributeError):
                    text_out_path = None
                edge_files = self._run_edge_query_fast(
                    layer_params,
                    encoding,
                    use_selected,
                    analysis_step,
                    text_out_path,
                    file_save_step
                )
            else:
                # do nothing, yay
                edge_files = []
        return edge_files

    def _determine_num_queries(self, layer_params: schemas.ConeforInputParameters):
        """
        Return the number of queries that will be processed.

        This method's main purpose is calculating progress steps.
        """

        num_queries = 0
        num_queries = (
            num_queries + 1 if layer_params.attribute_file_name is not None
            else num_queries
        )
        num_queries = (
            num_queries + 1 if layer_params.area_file_name is not None
            else num_queries
        )
        num_queries = (
            num_queries + 1 if (
                    layer_params.centroid_file_name is not None
                    or layer_params.centroid_distance_name is not None
            )
            else num_queries
        )
        num_queries = (
            num_queries + 1 if (
                    layer_params.edge_file_name is not None
                    or layer_params.edge_distance_name is not None
            )
            else num_queries
        )
        return num_queries

    def _run_attribute_query(
            self,
            layer_params: schemas.ConeforInputParameters,
            use_selected: bool,
            analysis_step: int,
            output_path: Path,
            file_save_progress_step: int = 0
    ) -> Path:
        self.update_info.emit('Running attribute query', 1)
        output_path = run_attribute_query(
            layer_params,
            use_selected,
            output_path,
            info_callback=self.update_info.emit
        )
        self.global_progress += analysis_step + file_save_progress_step
        self.progress_changed.emit()
        return output_path

    def _run_area_query(
            self,
            layer_params: schemas.ConeforInputParameters,
            use_selected: bool,
            analysis_step: int,
            output_path: Path,
            file_save_progress_step: int=0
    ) -> Path:
        self.update_info.emit('Running area query...', 1)
        output_path = run_area_query(
            layer_params,
            use_selected,
            output_path,
            info_callback=self.update_info.emit
        )
        self.global_progress += analysis_step + file_save_progress_step
        self.progress_changed.emit()
        return output_path

    def _run_centroid_query(
            self,
            layer_params: schemas.ConeforInputParameters,
            use_selected,
            analysis_step,
            output_path,
            file_save_progress_step=0,
            shape_file_path=None
    ) -> list[Path]:
        self.update_info.emit('Running centroid query...', 1)
        output_path = run_centroid_query(
            layer_params,
            use_selected,
            output_path,
            info_callback=self.update_info.emit
        )
        self.global_progress += analysis_step + file_save_progress_step
        self.progress_changed.emit()
        return [output_path]

    def _get_measurer(self, source_crs):
        measurer = qgis.core.QgsDistanceArea()
        measurer.setEllipsoidalMode(False)
        measurer.setSourceCrs(source_crs.postgisSrid())
        return measurer

    def _get_transformer(self, layer):
        source_crs = layer.crs()
        transformer = qgis.core.QgsCoordinateTransform(source_crs, self.project_crs)
        return transformer

    def _run_edge_query(
            self,
            layer_params: schemas.ConeforInputParameters,
            encoding,
            use_selected,
            analysis_step,
            output_path=None,
            file_save_progress_step=0,
            shape_file_path=None
    ) -> list[str]:
        # for each current and next features
        #   get the closest edge from current to next -> L1
        #   get the closest edge from next to current -> L2
        #   project L1's vertices on L2 and get their distance from L1
        #   project L2's vertices on L1 and get their distance from L2
        #   the pair with the smallest distance wins!
        self.update_info.emit('Running edge query', 1)
        data = []
        vector_layer = layer_params.layer
        if vector_layer.crs().geographicFlag():
            measurer = self._get_measurer(self.project_crs)
            transformer = self._get_transformer(vector_layer)
        else:
            measurer = self._get_measurer(vector_layer.crs())
            transformer = None
        feature_ids = [f.id() for f in utilities.get_features(vector_layer, use_selected)]
        feature_step = analysis_step / float(len(feature_ids))
        i = 0
        j = 0
        while i < len(feature_ids):
            self.update_info.emit(
                "Processing feature {}/{}".format(i+1, len(feature_ids)), 2)
            features = utilities.get_features(vector_layer, use_selected,
                                              feature_ids[i])
            current = iter(features).next()
            c_id_at = get_numeric_attribute(
                current, layer_params.id_attribute_field_name)
            if c_id_at is not None:
                current_geom = current.geometry()
                geometry_errors = current_geom.validateGeometry()
                if any(geometry_errors):
                    raise InvalidFeatureError('Layer: %s - Feature %s has '
                                              'geometry errors. Aborting...'
                                              % (vector_layer.name(), c_id_at))
                elif current_geom.isMultipart():
                    raise InvalidFeatureError('Feature %s is multipart. '
                                              'Aborting...' % c_id_at)
                current_poly = get_polygon(current_geom, transformer)
                j = i + 1
                while j < len(feature_ids):
                    features = utilities.get_features(vector_layer, use_selected,
                                                      feature_ids[j])
                    next_ = iter(features).next()
                    n_id_at = get_numeric_attribute(
                        next_, layer_params.id_attribute_field_name)
                    if n_id_at is not None:
                        next_geom = next_.geometry()
                        next_poly = get_polygon(next_geom, transformer)
                        segments = get_closest_segments(current_poly,
                                                             next_poly)
                        current_segment, next_segment = segments
                        candidates = []
                        for current_vertex in current_segment:
                            candidate = find_candidate_points(
                                current_vertex,
                                next_segment,
                                measurer
                            )
                            candidates.append(candidate)
                        for next_vertex in next_segment:
                            candidate = find_candidate_points(
                                next_vertex,
                                current_segment,
                                measurer
                            )
                            candidates.append(candidate)
                        ordered_candidates = sorted(candidates, 
                                                    key=lambda c: c[2])
                        winner = ordered_candidates[0]
                        # transform the winner's coordinates back to layer crs
                        from_restored = transform_point(winner[0],
                                                              transformer,
                                                              reverse=True)
                        to_restored = transform_point(winner[1],
                                                            transformer,
                                                            reverse=True)
                        feat_result = {
                            'distance': winner[2],
                            'from': from_restored,
                            'to': to_restored,
                            'from_attribute': c_id_at,
                            'to_attribute': n_id_at,
                        }
                        data.append(feat_result)
                    j += 1
            i += 1
            self.global_progress += feature_step
            self.progress_changed.emit()
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
                self.update_info.emit("Writing edges file...", 1)
                output_file = save_text_file(
                    data_to_write, output_dir, output_name, encoding)
                self.global_progress += file_save_progress_step
                self.progress_changed.emit()
                output_files.append(output_file)
            if shape_file_path is not None:
                output_dir, output_name = os.path.split(shape_file_path)
                self.update_info.emit('Creating edge distance file', 1)
                if not os.path.isdir(output_dir):
                    os.mkdir(output_dir)
                self.update_info.emit("edges ...", 2)
                output_shape = write_distance_file(data, output_dir,
                                                         output_name,
                                                         encoding,
                                                         vector_layer.crs())
                output_files.append(output_shape)
                self.global_progress += file_save_progress_step
                self.progress_changed.emit()
        return output_files

    def _run_edge_query_fast(
            self,
            layer_params: schemas.ConeforInputParameters,
            encoding,
            use_selected,
            analysis_step,
            output_path=None,
            file_save_progress_step=0
    ) -> list[str]:
        """
        This method performs a faster edge query.

        This method is only suitable for creating the output text file with
        edge distances and cannot be used to also write the vector shape
        with visual representation of the distances. Distances are calculated
        with blazing speed using the underlying QGIS (which uses GEOS)
        distance function. Unfortunately these calculations provide only the
        distance and not the actual closest point coordinates.

        Inputs:

        Returns:
        """

        self.update_info.emit('Running fast edge query', 1)
        data = []
        vector_layer = layer_params.layer
        if vector_layer.crs().geographicFlag():
            measurer = self._get_measurer(self.project_crs)
            transformer = self._get_transformer(vector_layer)
        else:
            measurer = self._get_measurer(vector_layer.crs())
            transformer = None
        feature_ids = [f.id() for f in utilities.get_features(
                       vector_layer, use_selected)]
        feature_step = analysis_step / float(len(feature_ids))
        i = 0
        j = 0
        while i < len(feature_ids):
            self.update_info.emit(
                "Processing feature {}/{}".format(i+1, len(feature_ids)), 2)
            features = utilities.get_features(vector_layer, use_selected,
                                              feature_ids[i])
            current = iter(features).next()
            c_id_at = get_numeric_attribute(
                current, layer_params.id_attribute_field_name)
            if c_id_at is not None:
                current_geom = current.geometry()
                if transformer is not None:
                    current_geom.transform(transformer)
                j = i + 1
                while j < len(feature_ids):
                    features = utilities.get_features(vector_layer, use_selected,
                                                      feature_ids[j])
                    next_ = iter(features).next()
                    n_id_at = get_numeric_attribute(
                        next_, layer_params.id_attribute_field_name)
                    if n_id_at is not None:
                        next_geom = next_.geometry()
                        if transformer is not None:
                            next_geom.transform(transformer)
                        dist = current_geom.distance(next_geom)
                        feat_result = {
                            'distance' : dist,
                            'from' : None,
                            'to' : None,
                            'from_attribute' : c_id_at,
                            'to_attribute' : n_id_at,
                        }
                        data.append(feat_result)
                    j += 1
            i += 1
            self.global_progress += feature_step
            self.progress_changed.emit()
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
                self.update_info.emit("Writing edges file...", 1)
                output_file = save_text_file(
                    data_to_write, output_dir, output_name, encoding)
                self.global_progress += file_save_progress_step
                self.progress_changed.emit()
                output_files.append(output_file)
                self.progress_changed.emit()
        return output_files


def get_numeric_attribute(
        feature: qgis.core.QgsFeature,
        attribute_name: str,
) -> Optional[int]:
    try:
        value = feature[attribute_name]
        if type(value) is QtCore.QVariant:  # pyqt was not able to convert this
            result = None
        else:
            result = int(value)
        return result
    except KeyError:
        raise InvalidAttributeError(
            f"attribute {attribute_name!r} does not exist")


def get_output_path(tentative_path: Path) -> Path:
    """
    Rename the output name if it is already present in the directory.
    """

    index = 1
    while True:
        if index == 1:
            to_check = tentative_path
        else:
            original_file_name = tentative_path.stem
            suffix = tentative_path.suffix
            new_name = f"{original_file_name}_{index}{suffix}"
            to_check = tentative_path.parent / new_name
        if not to_check.exists():
            return to_check
        else:
            index += 1


def write_distance_file(
        data,
        output_dir,
        output_name,
        encoding,
        crs,
        file_type="ESRI Shapefile"
):
    """
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
    """

    if file_type == 'ESRI Shapefile':
        if not output_name.endswith('.shp'):
            output_name = '%s.shp' % output_name
    output_name = get_output_file_name(output_dir, output_name)
    output_path = os.path.join(output_dir, output_name)
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    fields = qgis.core.QgsFields()
    fields.append(
        qgis.core.QgsField(
            'From_Node', QtCore.QVariant.String, 'From_NodeID', 255)
    )
    fields.append(
        qgis.core.QgsField('To_Node', QtCore.QVariant.String, 'To_NodeID', 255)
    )
    fields.append(
        qgis.core.QgsField('distance', QtCore.QVariant.Double, 'distance', 255, 1))
    writer = qgis.core.QgsVectorFileWriter(
        output_path, encoding, fields, qgis.core.QGis.WKBLineString, crs, file_type)
    if writer.hasError() == qgis.core.QgsVectorFileWriter.NoError:
        for item in data:
            feat = qgis.core.QgsFeature()
            line = [item['from'], item['to']]
            feat.setGeometry(qgis.core.QgsGeometry.fromPolyline(line))
            feat.setFields(fields)
            feat.initAttributes(3)
            feat.setAttribute('From_Node', item['from_attribute'])
            feat.setAttribute('To_Node', item['to_attribute'])
            feat.setAttribute('distance', item['distance'])
            writer.addFeature(feat)
    else:
        print('Error when creating distances lines '
              'file: {}'.format(writer.hasError()))
    del writer
    return output_path


def get_closest_vertex(pt, line, measurer):
    """
    Return the closest vertex to an input point.

    Inputs:

        pt - A QgsPoint representing the point to analyze

        line - A QgsLineString representing the line to analyze.

        measurer - A QgsDistanceArea object used to measure the distance

    Returns a QgsPoint of the vertex of the line that is closest to the
    input point.
    """

    distance = None
    closest = None
    for vertex in line:
        dist = measurer.measureLine(pt, vertex)
        if distance is None or distance > dist:
            closest = vertex
            distance = dist
    return closest


def is_on_the_segment(pt, line):
    result = False
    p1, p2 = line
    min_x, max_x = sorted((p1.x(), p2.x()))
    min_y, max_y = sorted((p1.y(), p2.y()))
    if (min_x < pt.x() < max_x) and (min_y < pt.y() < max_y):
        result = True
    return result


def project_point(line_segment, point, measurer):
    """
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
    """

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
    projected = qgis.core.QgsPoint(x, y)
    distance = measurer.measureLine(point, projected)
    return projected, distance

def transform_point(
        point,
        transformer=None,
        reverse=False
):
    """
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
    """

    if transformer is not None:
        if reverse:
            result = transformer.transform(
                point,
                qgis.core.QgsCoordinateTransform.ReverseTransform
            )
        else:
            result = transformer.transform(point)
    else:
        result = point
    return result


def find_candidate_points(point, line_segment, measurer):
    projected, distance = project_point(line_segment, point,
                                        measurer)
    if is_on_the_segment(projected, line_segment):
        candidate = (point, projected, distance)
    else:
        close_vertex = get_closest_vertex(projected, line_segment,
                                          measurer)
        distance = measurer.measureLine(point, close_vertex)
        candidate = (point, close_vertex, distance)
    return candidate

def get_segments(line_string):
    """
    Return the line segments that compose input line_string.

    Inputs:

        line_string - A QgsLineString

    Returns a list of two-element lists with QgsPoint objects that
    represent the segments of the input line_string.
    """

    segments = []
    for index, pt1 in enumerate(line_string):
        if index < (len(line_string) - 1):
            pt2 = line_string[index+1]
            segments.append([pt1, pt2])
    return segments

def get_closest_segments(poly1, poly2):
    """
    return the closest line segments between poly1 and poly2.

    Inputs:

        poly1 - A QgsPolygon object

        poly2 - A QgsPolygon object

    Returns a two-element tuple with:
        - the closest segment in poly1
        - the closest segment in poly2

    A segment is a two-element list of QgsPoints with the vertices
    of the segment.
    """

    segments1 = get_segments(poly1[0])
    segments2 = get_segments(poly2[0])
    closest_segments = []
    distance = None
    for seg1 in segments1:
        for seg2 in segments2:
            line1 = qgis.core.QgsGeometry.fromPolyline(seg1)
            line2 = qgis.core.QgsGeometry.fromPolyline(seg2)
            dist = line1.distance(line2)
            if distance is None or distance > dist:
                distance = dist
                closest_segments = (seg1, seg2)
    return closest_segments

def get_polygon(geometry, transformer=None):
    """
    Convert a geometry to polygon and transform its coordinates.

    Inputs:

        geometry - A QgsGeometry object to be converted

        transformer - A QgsCoordinateTransform object configured
            with the source and destination CRSs. If None (the default),
            no transformation is needed, and the returned result is
            the same as the input

    Returns a QgsPolygon object with the transformed coordinates of the
    geometry.
    """

    if transformer is not None:
        geometry.transform(transformer)
    return geometry.asPolygon()


def save_text_file(
        data,
        tentative_output_path: Path,
        encoding: Optional[str] = "utf-8",
) -> Path:
    tentative_output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = get_output_path(tentative_output_path)
    sorted_data = sorted(data, key=lambda tup: tup[0])
    with output_path.open(encoding=encoding, mode="w") as fh:
        for tup in sorted_data:
            line = "\t".join(str(i) for i in tup)
            fh.write(f"{line}\n")
        # Conefor manual states that files should terminate with a blank line
        fh.write("\n")
    return output_path


def get_measurer(
    source_crs: qgis.core.QgsCoordinateReferenceSystem
) -> qgis.core.QgsDistanceArea:
    measurer = qgis.core.QgsDistanceArea()
    qgis_project = qgis.core.QgsProject.instance()
    measurer.setEllipsoid(qgis_project.ellipsoid())
    measurer.setSourceCrs(source_crs, qgis_project.transformContext())
    return measurer


def generate_node_file_by_attribute(
    node_id_field_name: Optional[str],
    node_attribute_field_name: str,
    feature_iterator,
    num_features: int,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    info_callback: Optional[Callable[[str], None]] = log,

) -> Path:
    """Generate Conefor node file using each feature's attribute as the node attribute."""

    data = []
    current_progress = 0
    for feat in feature_iterator:
        info_callback(f"Processing feature {feat.id()}...")
        if len(list(feat.geometry().constParts())) > 1:
            log(
                f"Feature {feat.id()} has multiple parts",
                level=qgis.core.Qgis.Warning
            )
        id_ = (
            feat.id() if node_id_field_name is None
            else get_numeric_attribute(feat, node_id_field_name)
        )

        attr = get_numeric_attribute(feat, node_attribute_field_name)
        info_callback(f"{id_=} - {attr=}")
        if id_ is not None and attr is not None:
            if attr >= 0:
                data.append((id_, attr))
            else:
                log(
                    f"Feature with id {id_!r}: Attribute "
                    f"{node_attribute_field_name!r} "
                    f"has value: {attr!r} - this is lower than zero. Skipping this "
                    f"feature...",
                    level=qgis.core.Qgis.Warning
                )
        else:
            log(
                f"Was not able to retrieve a valid value for id ({id_!r}) and "
                f"attribute ({attr!r}), skipping this feature...",
                level=qgis.core.Qgis.Warning
            )
        current_progress += 1/num_features
        progress_callback(current_progress)
    info_callback("Writing attribute file...")
    return save_text_file(data, output_path)


def generate_node_file_by_area(
    node_id_field_name: Optional[str],
    crs: qgis.core.QgsCoordinateReferenceSystem,
    feature_iterator,
    num_features: int,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    info_callback: Optional[Callable[[str], None]] = log,
) -> Path:
    """Generate Conefor node file using each feature's area as the node attribute."""
    data = []
    area_measurer = get_measurer(crs)
    current_progress = 0
    for feat in feature_iterator:
        info_callback(f"Processing feature {feat.id()}...")
        geom = feat.geometry()
        feat_area = area_measurer.measureArea(geom)
        id_ = (
            feat.id() if node_id_field_name is None
            else get_numeric_attribute(feat, node_id_field_name)
        )
        data.append((id_, feat_area))
        current_progress += 1 / num_features
        progress_callback(current_progress)
    info_callback("Writing area file...")
    return save_text_file(data, output_path)


def generate_connection_file_with_attribute() -> Path:
    """
    Generate conefor node connections file using feature attribute as connection info.

    Attribute can represent either:

    - binary link between pairs of features
    - the probability of connectedness
    - the distance between features

    In any case, this information is coming directly from the feature's relevant field
    """
    ...



def generate_connection_file_with_centroid_distances(
        layer_params: schemas.ConeforInputParameters,
        use_selected,
        output_path: Path,
        progress_callback: Optional[Callable[[int], None]],
        info_callback: Optional[Callable[[str], None]] = log,
) -> Path:
    data = []
    vector_layer = layer_params.layer
    measurer = get_measurer(vector_layer)
    feature_iterator = (
        vector_layer.getSelectedFeatures() if use_selected else vector_layer.getFeatures())
    for feat in feature_iterator:
        info_callback(f"Processing feature {feat.id()}...")
        feat_id = get_feature_id(layer_params, feat)
        feat_centroid = feat.geometry().centroid().asPoint()
        pair_iterator = (
            vector_layer.getSelectedFeatures() if use_selected else vector_layer.getFeatures())
        for pair_feat in pair_iterator:
            if feat.id() != pair_feat.id():
                pair_feat_id = get_feature_id(layer_params, pair_feat)
                pair_centroid = pair_feat.geometry().centroid().asPoint()
                centroid_distance = measurer.measureLine([feat_centroid, pair_centroid])
                data.append((feat_id, pair_feat_id, centroid_distance))

    info_callback("Writing centroids file...")
    encoding = layer_params.layer.dataProvider().encoding()
    if encoding == 'System':
        encoding = sys.getfilesystemencoding()
    return save_text_file(data, output_path, encoding)


def get_feature_id(
    node_id_field_name: Optional[str],
    feature: qgis.core.QgsFeature
) -> int:
    if node_id_field_name is None:
        feat_id = feature.id()
    else:
        feat_id = get_numeric_attribute(feature, node_id_field_name)
    return feat_id


def run_edge_query(
    layer_params: schemas.ConeforInputParameters,
    use_selected: bool,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    info_callback: Optional[Callable[[str], None]] = log,
) -> Path:
    data = []
    vector_layer = layer_params.layer
    if vector_layer.crs().isGeographic():
        qgis_project = qgis.core.QgsProject.instance()
        destination_crs = qgis.core.QgsCoordinateReferenceSystem(qgis_project.crs())
        transformer = qgis.core.QgsCoordinateTransform(vector_layer.crs(), destination_crs, qgis_project.transformContext())
    else:
        transformer = None
    feature_iterator = (
        vector_layer.getSelectedFeatures() if use_selected else vector_layer.getFeatures())
    for feat in feature_iterator:
        info_callback(f"Processing feature {feat.id()}...")
        feat_id = get_feature_id(layer_params, feat)
        feat_geom = feat.geometry()
        if transformer is not None:
            feat_geom.transform(transformer)
        pair_iterator = (
            vector_layer.getSelectedFeatures() if use_selected else vector_layer.getFeatures())
        for pair_feat in pair_iterator:
            if feat.id() != pair_feat.id():
                pair_feat_id = get_feature_id(layer_params, pair_feat)
                pair_feat_geom = pair_feat.geometry()
                if transformer is not None:
                    pair_feat_geom.transform(transformer)
                edge_distance = feat_geom.distance(pair_feat_geom)
                data.append(feat_id, pair_feat_id, edge_distance)
    info_callback("Writing edges file...")
    encoding = layer_params.layer.dataProvider().encoding()
    if encoding == 'System':
        encoding = sys.getfilesystemencoding()
    return save_text_file(data, output_path, encoding)
