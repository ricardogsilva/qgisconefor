import dataclasses
import enum
from pathlib import Path
from typing import Optional

from qgis.PyQt import QtCore

import qgis.core

ICON_RESOURCE_PATH = ":/plugins/qgisconefor/icon.png"

PROCESSING_TASK_ID_SEPARATOR = "*_*_*_"


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


@dataclasses.dataclass
class LayerRelevantFields:
    unique_field_names: list[str] = dataclasses.field(default_factory=list)
    numerical_field_names: list[str] = dataclasses.field(default_factory=list)
    binary_value_field_names: list[str] = dataclasses.field(default_factory=list)


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

