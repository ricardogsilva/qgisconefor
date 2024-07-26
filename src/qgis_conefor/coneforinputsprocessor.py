from pathlib import Path
from typing import (
    Callable,
    Optional,
)

import qgis.core
from qgis.PyQt import QtCore

from .utilities import log


class InvalidAttributeError(Exception):
    pass


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


def autogenerate_feature_id(feature: qgis.core.QgsFeature) -> int:
    return feature.id() + 1


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
    node_id_field_name: Optional[str],
    node_attribute_field_name: str,
    feature_iterator_factory: Callable[[], qgis.core.QgsFeatureIterator],
    num_features: int,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    start_progress: int = 0,
    end_progress: int = 100,
    info_callback: Optional[Callable[[str], None]] = log,

) -> Optional[Path]:
    """Generate Conefor node file using each feature's attribute as the node attribute."""

    data = []
    current_progress = 0
    seen_ids = set()
    for feat in feature_iterator_factory():
        info_callback(f"Processing feature {feat.id()}...")
        if len(list(feat.geometry().constParts())) > 1:
            log(
                f"Feature {feat.id()} has multiple parts",
                level=qgis.core.Qgis.Warning
            )
        id_ = (
            autogenerate_feature_id(feat) if node_id_field_name is None
            else get_numeric_attribute(feat, node_id_field_name)
        )
        attr = get_numeric_attribute(feat, node_attribute_field_name)
        info_callback(f"{id_=} - {attr=}")
        if id_ is not None and attr is not None:
            if id_ not in seen_ids:
                if attr >= 0:
                    data.append((id_, attr))
                    seen_ids.add(id_)
                else:
                    info_callback(
                        f"Feature with id {id_!r}: Attribute "
                        f"{node_attribute_field_name!r} "
                        f"has value: {attr!r} - this is lower than zero. Skipping this "
                        f"feature...",
                    )
            else:
                raise qgis.core.QgsProcessingException(
                    f"node id {id_!r} is not unique. Conefor node identifiers must be "
                    f"unique - Please select another layer field."
                )
        else:
            info_callback(
                f"Was not able to retrieve a valid value for id ({id_!r}) and "
                f"attribute ({attr!r}), skipping this feature...",
            )

        current_progress += (end_progress - start_progress)/num_features
        progress_callback(int(start_progress + current_progress))
    info_callback("Writing attribute file...")
    if len(data) > 0:
        return save_text_file(data, output_path)
    else:
        info_callback("Was not able to extract any data")
        return None


def generate_node_file_by_area(
    node_id_field_name: Optional[str],
    crs: qgis.core.QgsCoordinateReferenceSystem,
    feature_iterator_factory: Callable[[], qgis.core.QgsFeatureIterator],
    num_features: int,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    start_progress: int = 0,
    end_progress: int = 100,
    info_callback: Optional[Callable[[str], None]] = log,
) -> Optional[Path]:
    """Generate Conefor node file using each feature's area as the node attribute."""
    data = []
    area_measurer = get_measurer(crs)
    current_progress = 0
    seen_ids = set()
    for feat in feature_iterator_factory():
        info_callback(f"Processing feature {feat.id()}...")
        geom = feat.geometry()
        feat_area = area_measurer.measureArea(geom)
        id_ = (
            autogenerate_feature_id(feat) if node_id_field_name is None
            else get_numeric_attribute(feat, node_id_field_name)
        )
        if id_ is not None:
            if id_ not in seen_ids:
                data.append((id_, feat_area))
                seen_ids.add(id_)
            else:
                raise qgis.core.QgsProcessingException(
                    f"node id {id_!r} is not unique. Conefor node identifiers must be "
                    f"unique - Please select another layer field."
                )
        else:
            info_callback(
                f"Was not able to retrieve a valid value for id ({id_!r}), skipping "
                f"this feature...",
            )

        current_progress += (end_progress - start_progress)/num_features
        progress_callback(int(start_progress + current_progress))
    info_callback("Writing area file...")
    if len(data) > 0:
        return save_text_file(data, output_path)
    else:
        info_callback("Was not able to extract any data")
        return None


def generate_connection_file_with_centroid_distances(
    node_id_field_name: Optional[str],
    crs: qgis.core.QgsCoordinateReferenceSystem,
    feature_iterator_factory: Callable[[], qgis.core.QgsFeatureIterator],
    num_features: int,
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]],
    start_progress: int = 0,
    end_progress: int = 100,
    info_callback: Optional[Callable[[str], None]] = log,
    cancelled_callback: Optional[Callable[[], bool]] = None,
    distance_threshold: Optional[int] = None,
) -> Optional[Path]:
    data = []
    measurer = get_measurer(crs)
    current_progress = 0
    seen_ids = set()
    for feat in feature_iterator_factory():
        feat_id = (
            autogenerate_feature_id(feat) if node_id_field_name is None
            else get_numeric_attribute(feat, node_id_field_name)
        )
        if feat_id is not None:
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
                        pair_feat_id = (
                            autogenerate_feature_id(pair_feat) if node_id_field_name is None
                            else get_numeric_attribute(pair_feat, node_id_field_name)
                        )
                        if pair_feat_id is not None:
                            # info_callback(f"Processing pair feature {pair_feat_id}...")
                            pair_centroid = pair_feat.geometry().centroid().asPoint()
                            centroid_distance = measurer.measureLine([feat_centroid, pair_centroid])
                            # info_callback(f"{centroid_distance=}")
                            if distance_threshold is None or centroid_distance <= distance_threshold:
                                data.append((feat_id, pair_feat_id, centroid_distance))
                        else:
                            info_callback(
                                f"Was not able to retrieve a valid value for feature pair "
                                f"id ({pair_feat_id!r}), skipping this feature...",
                            )
                else:
                    # this `else` block belongs to the inner `for` block and
                    # it gets executed if the `for` loop is able to run until
                    # completion (i.e. is not stopped by a `break`).
                    current_progress += (end_progress - start_progress) / num_features
                    progress_callback(int(start_progress + current_progress))
                    continue
                # if the inner loop did not run until completion, then the outer loop should `break` too
                break
            else:
                raise qgis.core.QgsProcessingException(
                    f"node id {feat_id!r} is not unique. Conefor node identifiers must be "
                    f"unique - Please select another layer field."
                )
        else:
            info_callback(
                f"Was not able to retrieve a valid value for feature id ({feat_id!r}), "
                f"skipping this feature...",
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
    start_progress: int = 0,
    end_progress: int = 100,
    info_callback: Optional[Callable[[str], None]] = log,
    cancelled_callback: Optional[Callable[[], bool]] = None,
    distance_threshold: Optional[int] = None,
) -> Optional[Path]:
    data = []
    if crs.isGeographic():
        qgis_project = qgis.core.QgsProject.instance()
        destination_crs = qgis.core.QgsCoordinateReferenceSystem(qgis_project.crs())
        transformer = qgis.core.QgsCoordinateTransform(
            crs, destination_crs, qgis_project.transformContext())
    else:
        transformer = None
    current_progress = 0
    info_callback(f"About to start processing {num_features} features...")
    seen_ids = set()
    for feat in feature_iterator_factory():
        feat_id = (
            autogenerate_feature_id(feat) if node_id_field_name is None
            else get_numeric_attribute(feat, node_id_field_name)
        )
        if feat_id is not None:
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
                        pair_feat_id = (
                            autogenerate_feature_id(pair_feat) if node_id_field_name is None
                            else get_numeric_attribute(pair_feat, node_id_field_name)
                        )
                        if pair_feat_id is not None:
                            # info_callback(f"Processing pair feature {pair_feat_id}...")
                            pair_feat_geom = pair_feat.geometry()
                            if transformer is not None:
                                pair_feat_geom.transform(transformer)
                            edge_distance = feat_geom.distance(pair_feat_geom)
                            # info_callback(f"{edge_distance=}")
                            if distance_threshold is None or edge_distance <= distance_threshold:
                                data.append((feat_id, pair_feat_id, edge_distance))
                        else:
                            info_callback(
                                f"Was not able to retrieve a valid value for feature pair "
                                f"id ({pair_feat_id!r}), skipping this feature...",
                            )
                else:
                    # this `else` block belongs to the inner `for` block and
                    # it gets executed if the `for` loop is able to run until
                    # completion (i.e. is not stopped by a `break`).
                    current_progress += (end_progress - start_progress) / num_features
                    progress_callback(int(start_progress + current_progress))
                    continue
                # if the inner loop did not run until completion, then the outer loop should `break` too
                break
            else:
                raise qgis.core.QgsProcessingException(
                    f"node id {feat_id!r} is not unique. Conefor node identifiers must be "
                    f"unique - Please select another layer field."
                )
        else:
            info_callback(
                f"Was not able to retrieve a valid value for feature id ({feat_id!r}), "
                f"skipping this feature..."
            )
    info_callback("Writing edges file...")
    if not cancelled_callback():
        if len(data) > 0:
            return save_text_file(data, output_path)
        else:
            info_callback("Was not able to extract any data")
    else:
        info_callback("Did not write any output file, processing has been aborted")
