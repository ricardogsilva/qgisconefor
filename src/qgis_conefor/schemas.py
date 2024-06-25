import dataclasses
from typing import Optional

import qgis.core


@dataclasses.dataclass
class ConeforInputParameters:
    layer: qgis.core.QgsVectorLayer
    id_attribute_field_name: str
    attribute_field_name: Optional[str]
    attribute_file_name: Optional[str]
    area_file_name: Optional[str]
    centroid_file_name: Optional[str]
    edge_file_name: Optional[str]
    centroid_distance_name: Optional[str]
    edge_distance_name: Optional[str]
