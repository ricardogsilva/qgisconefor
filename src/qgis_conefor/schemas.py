import dataclasses
import enum
from pathlib import Path
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


class ConeforNodeConnectionType(enum.Enum):
    DISTANCE = "dist"
    PROBABILITY = "prob"
    # links is not supported


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
    id_attribute_field_name: str = AUTOGENERATE_NODE_ID_LABEL
    attribute_field_name: str = GENERATE_FROM_AREA_LABEL


@dataclasses.dataclass
class ConeforRuntimeParameters:
    conefor_path: Path
    nodes_path: Path
    connections_path: Path
    connection_type: ConeforNodeConnectionType
    all_pairs_connected: bool
    threshold_direct_links: Optional[float] = 0.0
    binary_indexes: Optional[list[str]] = None
    decay_distance: float = 0.0
    decay_probability: float = 0.0
    probability_indexes: Optional[list[str]] = None
    only_overall: bool = False
    removal: bool = False
    removal_threshold: Optional[float] = None
    improvement: bool = False
    improvement_threshold: Optional[float] = None
    write_component_file: bool = False
    write_links_file: bool = False
    write_dispersal_probabilities_file: bool = False
    write_maximum_probabilities_file: bool = False
    land_area: Optional[float] = None
    prefix: Optional[str] = None

