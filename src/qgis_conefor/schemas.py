import dataclasses
import enum
from typing import Optional

from qgis.PyQt import QtCore

import qgis.core

ICON_RESOURCE_PATH = ":/plugins/qgisconefor/icon.png"

PROCESSING_TASK_ID_SEPARATOR = "*_*_*_"

AUTOGENERATE_NODE_ID_LABEL = "<AUTOGENERATE>"
NONE_LABEL = "<NONE>"
GENERATE_FROM_AREA_LABEL = "<GENERATE_FROM_AREA>"

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


class ConeforProcessingSetting(enum.Enum):
    CONEFOR_CLI_PATH = "conefor executable path"


class QgisConeforSettingsKey(enum.Enum):
    OUTPUT_DIR = "PythonPlugins/qgisconefor/output_dir"
    USE_SELECTED = "PythonPlugins/qgisconefor/use_selected_features"


@dataclasses.dataclass(frozen=True)
class ConeforInputParameters:
    layer: qgis.core.QgsVectorLayer
    id_attribute_field_name: Optional[str] = None  # None means autogenerate a node id
    attribute_field_name: Optional[str] = None  # None means use area as the attribute
    connections_method: NodeConnectionType = NodeConnectionType.EDGE_DISTANCE
    # attribute_file_name: Optional[str] = None
    # area_file_name: Optional[str] = None
    # centroid_file_name: Optional[str] = None
    # edge_file_name: Optional[str] = None
    # centroid_distance_name: Optional[str] = None
    # edge_distance_name: Optional[str] = None

    def __hash__(self):
        return hash(
            "".join((
                self.layer.name(),
                self.id_attribute_field_name or AUTOGENERATE_NODE_ID_LABEL,
                self.attribute_field_name or GENERATE_FROM_AREA_LABEL,
                self.connections_method.value
            ))
        )


# This will replace processlayer.ProcessLayer
@dataclasses.dataclass
class TableModelItem:
    layer: qgis.core.QgsVectorLayer
    # calculate_centroid_distance: bool
    # calculate_edge_distance: bool
    id_attribute_field_name: str = AUTOGENERATE_NODE_ID_LABEL
    attribute_field_name: str = GENERATE_FROM_AREA_LABEL
    # calculate_area_as_node_attribute: bool = False
