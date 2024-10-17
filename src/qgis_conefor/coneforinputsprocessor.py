from pathlib import Path
from typing import (
    Callable,
    Optional,
    Union,
)

import qgis.core
from qgis.PyQt import (
    QtCore,
)

from .utilities import log

_NUMERIC_FIELD_TYPES = (
    QtCore.QMetaType.Int,
    QtCore.QMetaType.Double,
    QtCore.QMetaType.Float,
    QtCore.QMetaType.Short,
    QtCore.QMetaType.Long,
    QtCore.QMetaType.LongLong,
    QtCore.QMetaType.UInt,
    QtCore.QMetaType.ULong,
    QtCore.QMetaType.ULongLong,
    QtCore.QMetaType.UShort,
)

_IDENTIFIER_FIELD_TYPES = (
    QtCore.QMetaType.Int,
    QtCore.QMetaType.Short,
    QtCore.QMetaType.Long,
    QtCore.QMetaType.LongLong,
    QtCore.QMetaType.UInt,
    QtCore.QMetaType.ULong,
    QtCore.QMetaType.ULongLong,
    QtCore.QMetaType.UShort,
)

_BINARY_FIELD_TYPES = (
    QtCore.QMetaType.Int,
    QtCore.QMetaType.Short,
    QtCore.QMetaType.Long,
    QtCore.QMetaType.LongLong,
    QtCore.QMetaType.UInt,
    QtCore.QMetaType.ULong,
    QtCore.QMetaType.ULongLong,
    QtCore.QMetaType.UShort,
)


class InvalidAttributeError(Exception):
    pass


def validate_node_identifier_attribute(
        feature_source: Union[
            qgis.core.QgsVectorLayer, qgis.core.QgsProcessingFeatureSource],
        field: qgis.core.QgsField,
) -> bool:
    is_eligible = field.type() in _IDENTIFIER_FIELD_TYPES
    field_index = list(feature_source.fields()).index(field)
    has_unique_values = (
            feature_source.featureCount() ==
            len(feature_source.uniqueValues(field_index))
    )
    return is_eligible and has_unique_values


def validate_node_attribute(
        feature_source: Union[
            qgis.core.QgsVectorLayer, qgis.core.QgsProcessingFeatureSource],
        field: qgis.core.QgsField,
) -> bool:
    return field.type() in _NUMERIC_FIELD_TYPES


def validate_node_to_add_attribute(
        feature_source: Union[
            qgis.core.QgsVectorLayer, qgis.core.QgsProcessingFeatureSource],
        field: qgis.core.QgsField,
) -> bool:
    is_eligible = field.type() in _BINARY_FIELD_TYPES
    field_index = list(feature_source.fields()).index(field)
    has_only_binary_values = set(feature_source.uniqueValues(field_index)) <= {0, 1}
    return is_eligible and has_only_binary_values


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
    node_id_field_name: str,
    node_attribute_field_name: str,
    nodes_to_add_field_name: Optional[str],
    feature_iterator_factory: Callable[[], qgis.core.QgsFeatureIterator],
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    progress_step: float,
    start_progress: int = 0,
    info_callback: Optional[Callable[[str], None]] = log,

) -> Optional[Path]:
    """Generate Conefor node file using each feature's attribute as the node attribute."""

    data = []
    current_progress = start_progress
    seen_ids = set()
    for feat in feature_iterator_factory():
        info_callback(f"Processing feature {feat.id()}...")
        if len(list(feat.geometry().constParts())) > 1:
            log(
                f"Feature {feat.id()} has multiple parts",
                level=qgis.core.Qgis.Warning
            )
        id_ = feat[node_id_field_name]
        if id_ not in seen_ids:
            attr = feat[node_attribute_field_name]
            if attr is not None:
                if attr >= 0:
                    if nodes_to_add_field_name is not None:
                        nodes_to_add_attr_value = feat[nodes_to_add_field_name]
                        if nodes_to_add_attr_value is not None:
                            data.append((id_, attr, nodes_to_add_attr_value))
                        else:
                            raise qgis.core.QgsProcessingException(
                                f"node id {id_!r} has invalid value for the 'nodes to add' "
                                f"attribute. Conefor expects 'nodes to add' to be "
                                f"either 0 or 1 - found a value of "
                                f"{nodes_to_add_attr_value!r}."
                            )
                    else:
                        data.append((id_, attr))
                    seen_ids.add(id_)
                    current_progress += progress_step
                    progress_callback(int(current_progress))
                else:
                    info_callback(
                        f"Feature with id {id_!r}: Attribute "
                        f"{node_attribute_field_name!r} "
                        f"has value: {attr!r} - this is lower than zero. Skipping this "
                        f"feature...",
                    )
            else:
                info_callback(
                    f"Was not able to retrieve a valid value for node attribute "
                    f"for node with id ({id_!r}), skipping this feature...",
                )

        else:
            raise qgis.core.QgsProcessingException(
                f"node id {id_!r} is not unique. Conefor node identifiers must be "
                f"unique - Please select another layer field."
            )
        # current_progress += (end_progress - start_progress)/num_features
        # progress_callback(int(start_progress + current_progress))
    info_callback("Writing attribute file...")
    if len(data) > 0:
        return save_text_file(data, output_path)
    else:
        info_callback("Was not able to extract any data")
        return None


def generate_connection_file_with_centroid_distances(
    node_id_field_name: str,
    crs: qgis.core.QgsCoordinateReferenceSystem,
    feature_iterator_factory: Callable[[], qgis.core.QgsFeatureIterator],
    num_features: int,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    progress_step: float,
    start_progress: int = 0,
    info_callback: Optional[Callable[[str], None]] = log,
    cancelled_callback: Optional[Callable[[], bool]] = None,
) -> Optional[Path]:
    data = []
    measurer = get_measurer(crs)
    current_progress = start_progress
    seen_ids = set()
    for feat in feature_iterator_factory():
        feat_id = feat[node_id_field_name]
        if feat_id not in seen_ids:
            seen_ids.add(feat_id)
            info_callback(f"Processing feature {feat_id}...")
            feat_centroid = feat.geometry().centroid().asPoint()
            for pair_feat in feature_iterator_factory():
                should_abort = cancelled_callback() if cancelled_callback is not None else False
                if should_abort:
                    info_callback("Aborting...")
                    break
                if pair_feat.id() > feat.id():
                    pair_feat_id = pair_feat[node_id_field_name]
                    pair_centroid = pair_feat.geometry().centroid().asPoint()
                    centroid_distance = measurer.measureLine([feat_centroid, pair_centroid])
                    data.append((feat_id, pair_feat_id, centroid_distance))
                    current_progress += progress_step
                    progress_callback(int(current_progress))
            else:
                # this `else` block belongs to the inner `for` block and
                # it gets executed if the `for` loop is able to run until
                # completion (i.e. is not stopped by a `break`).
                # current_progress += (end_progress - start_progress) / num_features
                # progress_callback(int(start_progress + current_progress))
                continue
            # if the inner loop did not run until completion, then the outer loop should `break` too
            break
        else:
            raise qgis.core.QgsProcessingException(
                f"node id {feat_id!r} is not unique. Conefor node identifiers must be "
                f"unique - Please select another layer field."
            )

    info_callback("Writing connections file...")
    info_callback(f"{data=}")
    if not cancelled_callback():
        if len(data) > 0:
            return save_text_file(data, output_path)
        else:
            info_callback("Was not able to extract any data")
    else:
        info_callback("Did not write any output file, processing has been aborted")


def generate_connection_file_with_edge_distances(
    node_id_field_name: Optional[str],
    crs: qgis.core.QgsCoordinateReferenceSystem,
    feature_iterator_factory: Callable[[], qgis.core.QgsFeatureIterator],
    num_features: int,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    progress_step: float,
    start_progress: int = 0,
    info_callback: Optional[Callable[[str], None]] = log,
    cancelled_callback: Optional[Callable[[], bool]] = None,
) -> Optional[Path]:
    data = []
    if crs.isGeographic():
        qgis_project = qgis.core.QgsProject.instance()
        destination_crs = qgis.core.QgsCoordinateReferenceSystem(qgis_project.crs())
        transformer = qgis.core.QgsCoordinateTransform(
            crs, destination_crs, qgis_project.transformContext())
    else:
        transformer = None
    current_progress = start_progress
    info_callback(f"About to start processing {num_features} features...")
    seen_ids = set()
    for feat in feature_iterator_factory():
        feat_id = feat[node_id_field_name]
        if feat_id not in seen_ids:
            seen_ids.add(feat_id)
            info_callback(f"Processing feature {feat_id}...")
            feat_geom = feat.geometry()
            if transformer is not None:
                feat_geom.transform(transformer)
            for pair_feat in feature_iterator_factory():
                should_abort = cancelled_callback() if cancelled_callback is not None else False
                if should_abort:
                    info_callback("Aborting...")
                    break
                if pair_feat.id() > feat.id():
                    pair_feat_id = pair_feat[node_id_field_name]
                    pair_feat_geom = pair_feat.geometry()
                    if transformer is not None:
                        pair_feat_geom.transform(transformer)
                    edge_distance = feat_geom.distance(pair_feat_geom)
                    data.append((feat_id, pair_feat_id, edge_distance))
                    current_progress += progress_step
                    progress_callback(int(current_progress))
            else:
                # this `else` block belongs to the inner `for` block and
                # it gets executed if the `for` loop is able to run until
                # completion (i.e. is not stopped by a `break`).
                # current_progress += (end_progress - start_progress) / num_features
                # progress_callback(int(start_progress + current_progress))
                continue
            # if the inner loop did not run until completion, then the outer loop should `break` too
            break
        else:
            raise qgis.core.QgsProcessingException(
                f"node id {feat_id!r} is not unique. Conefor node identifiers must be "
                f"unique - Please select another layer field."
            )
    info_callback("Writing edges file...")
    if not cancelled_callback():
        if len(data) > 0:
            return save_text_file(data, output_path)
        else:
            info_callback("Was not able to extract any data")
    else:
        info_callback("Did not write any output file, processing has been aborted")
