import dataclasses
import enum
from typing import Optional

from qgis.PyQt import QtCore

import qgis.core

ICON_RESOURCE_PATH = ":/plugins/qgisconefor/icon.png"

AUTOGENERATE_NODE_ID_LABEL = "<AUTOGENERATE>"
NONE_LABEL = "<NONE>"

RELEVANT_FIELD_TYPES = (
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


class NodeConnectionType(enum.Enum):
    EDGE_DISTANCE = "edge distance"
    CENTROID_DISTANCE = "centroid distance"


class QgisConeforSettingsKey(enum.Enum):
    OUTPUT_DIR = "PythonPlugins/qgisconefor/output_dir"
    USE_SELECTED = "PythonPlugins/qgisconefor/use_selected_features"


@dataclasses.dataclass
class ConeforInputParameters:
    layer: qgis.core.QgsVectorLayer
    id_attribute_field_name: str
    attribute_field_name: Optional[str] = None
    attribute_file_name: Optional[str] = None
    area_file_name: Optional[str] = None
    centroid_file_name: Optional[str] = None
    edge_file_name: Optional[str] = None
    centroid_distance_name: Optional[str] = None
    edge_distance_name: Optional[str] = None


# This will replace processlayer.ProcessLayer
@dataclasses.dataclass
class TableModelItem:
    layer: qgis.core.QgsVectorLayer
    calculate_centroid_distance: bool
    calculate_edge_distance: bool
    id_attribute_field_name: str = AUTOGENERATE_NODE_ID_LABEL
    attribute_field_name: str = NONE_LABEL
    calculate_area_as_node_attribute: bool = False