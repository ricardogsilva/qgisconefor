"""
A QGIS plugin for writing input files to the Conefor software.
"""

import functools
from typing import Optional

import qgis.core
import qgis.gui
from processing.tools.dataobjects import createContext
from qgis.PyQt import (
    QtGui,
    QtWidgets,
)

# Initialize Qt resources from file resources.py
from .resources import *  # noqa

from . import (
    schemas,
    tablemodel,
    tasks,
)
from .coneforinputsprocessor import InputsProcessor
from .conefordialog import ConeforDialog
from .processing.provider import ProcessingConeforProvider
from .processing.algorithms.coneforinputs import (
    ConeforInputsPoint,
    ConeforInputsPolygon,
)
from .utilities import log


class QgisConefor:

    _action_title = "Conefor inputs"

    action: QtWidgets.QAction
    dialog: Optional[QtWidgets.QDialog]
    processing_provider: ProcessingConeforProvider
    inputs_from_points_algorithm: Optional[qgis.core.QgsProcessingAlgorithm]
    inputs_from_polygons_algorithm: Optional[qgis.core.QgsProcessingAlgorithm]
    model: Optional[tablemodel.ProcessLayerTableModel]
    layers: dict[str, list[str]]
    processing_context: Optional[qgis.core.QgsProcessingContext]
    processing_tasks: dict[
        schemas.ConeforInputParameters, qgis.core.QgsProcessingAlgRunnerTask]

    analyzer_task: Optional[tasks.LayerAnalyzerTask]

    def __init__(self, iface: qgis.gui.QgisInterface):
        self.iface = iface
        self.dialog = None
        project_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        self.layers = {}
        self.model = tablemodel.ProcessLayerTableModel(
            qgis_layers={},
            initial_layers_to_process=[],
            lock_layers=False,
            dialog=None
        )
        self.processor = InputsProcessor(project_crs)
        self.processing_provider = ProcessingConeforProvider()
        self.processing_context = None
        self.inputs_from_points_algorithm = None
        self.inputs_from_polygons_algorithm = None
        self.processing_tasks = {}

    def init_processing(self):
        processing_registry = qgis.core.QgsApplication.processingRegistry()
        processing_registry.addProvider(self.processing_provider)

    def initGui(self):
        self.init_processing()
        processing_registry = qgis.core.QgsApplication.processingRegistry()
        self.inputs_from_points_algorithm = processing_registry.createAlgorithmById(
            "conefor:inputsfrompoint")
        self.inputs_from_polygons_algorithm = processing_registry.createAlgorithmById(
            "conefor:inputsfrompolygon")
        self.analyzer_task = None
        self.dialog = ConeforDialog(self, model=self.model)
        self.dialog.setModal(True)
        self.dialog.finished.connect(self.handle_dialog_closed)
        self.dialog.accepted.connect(self.prepare_conefor_inputs)
        self.action = QtWidgets.QAction(
            QtGui.QIcon(schemas.ICON_RESOURCE_PATH),
            self._action_title,
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addPluginToVectorMenu(f"&{self._action_title}", self.action)
        self.iface.addVectorToolBarIcon(self.action)
        qgis_project = qgis.core.QgsProject.instance()
        qgis_project.legendLayersAdded.connect(self.check_for_new_layers)
        qgis_project.layersRemoved.connect(self.check_for_removed_layers)

    def unload(self):
        processing_registry = qgis.core.QgsApplication.processingRegistry()
        # processing_registry.removeProvider(self.processing_provider)
        self.iface.removePluginVectorMenu(f"&{self._action_title}", self.action)
        self.iface.removeVectorToolBarIcon(self.action)

    def start_analyzing_layers(self, disregard_ids: Optional[list[str]] = None) -> None:
        current_layers = qgis.core.QgsProject.instance().mapLayers()
        to_disregard = disregard_ids or []
        relevant_layers = {
            id_: la for id_, la in current_layers.items() if id_ not in to_disregard}
        self.analyzer_task = tasks.LayerAnalyzerTask(
            description="analyze currently loaded layers",
            layers_to_analyze=relevant_layers,
        )
        self.analyzer_task.layers_analyzed.connect(self.finished_analyzing_layers)
        task_manager = qgis.core.QgsApplication.taskManager()
        task_manager.addTask(self.analyzer_task)

    def run(self):
        # self.analyzer_task = tasks.LayerAnalyzerTask(
        #     description="analyze currently loaded layers",
        #     layers_to_analyze=qgis.core.QgsProject.instance().mapLayers(),
        # )
        # self.analyzer_task.layers_analyzed.connect(self.dialog.finished_analyzing_layers)
        # task_manager = qgis.core.QgsApplication.taskManager()
        # task_manager.addTask(self.analyzer_task)

        self.model.data_ = self.layers
        num_rows = self.model.rowCount()
        self.model.removeRows(num_rows)


        self.dialog.show()

    def finished_analyzing_layers(
            self,
            usable_layers: dict[qgis.core.QgsVectorLayer, list[str]],
            usable_layer_ids: dict[str, list[str]],
    ):
        log(f"{usable_layer_ids=}")
        self.layers = usable_layers

        if any(self.layers):
            self.action.setEnabled(True)
        else:
            self.action.setEnabled(False)

    def handle_dialog_closed(self, result: int):
        log(f"Dialog has been closed with result {result!r}")
        self.dialog.hide()

    def prepare_conefor_inputs(self):
        log(f"Inside prepare_conefor_inputs, now we need data to work with")
        layer_inputs = []
        load_to_canvas = self.dialog.create_distances_files_chb.isChecked()
        output_dir = str(self.dialog.output_dir_le.text())
        only_selected_features = self.dialog.use_selected_features_chb.isChecked()

        kwargs = {}
        if len(self.dialog.model.layers_to_process) > 1:
            first = self.dialog.model.layers_to_process[0]
            kwargs.update({
                "default_node_identifier_name": first.id_attribute_field_name,
                "default_node_attribute_name": first.attribute_field_name,
                # "default_process_centroid_distance": first.calculate_centroid_distance,
                # "default_process_edge_distance": first.calculate_edge_distance,
            })
        for idx, data_item in enumerate(self.dialog.model.layers_to_process):
            if idx == 0 or not self.dialog.lock_layers_chb.isChecked():
                input_parameters = self.get_conefor_input_parameters(
                    data_item, load_to_canvas)
            else:
                input_parameters = self.get_conefor_input_parameters(
                    data_item, load_to_canvas, **kwargs)
            layer_inputs.append(input_parameters)
        task_manager = qgis.core.QgsApplication.taskManager()
        self.processing_tasks = {}
        self.processing_context = createContext()
        for layer_to_process in layer_inputs:
            common_params = {
                ConeforInputsPolygon.INPUT_NODE_IDENTIFIER_NAME[0]: (
                        layer_to_process.id_attribute_field_name or ""),
                ConeforInputsPolygon.INPUT_NODE_ATTRIBUTE_NAME[0]: (
                        layer_to_process.attribute_field_name or ""),
                ConeforInputsPolygon.INPUT_DISTANCE_THRESHOLD[0]: "",
                ConeforInputsPolygon.INPUT_OUTPUT_DIRECTORY[0]: str(output_dir),
            }
            log(f"{common_params=}")
            if layer_to_process.layer.geometryType() == qgis.core.Qgis.GeometryType.Polygon:
                log(f"Creating the conefor:inputsfrompolygon runner task")
                task = qgis.core.QgsProcessingAlgRunnerTask(
                    algorithm=self.inputs_from_polygons_algorithm,
                    parameters={
                        ConeforInputsPolygon.INPUT_POLYGON_LAYER[0]: (
                            layer_to_process.layer),
                        ConeforInputsPolygon.INPUT_NODE_CONNECTION_DISTANCE_METHOD[0]: (
                            layer_to_process.connections_method.value),
                        **common_params
                    },
                    context=self.processing_context
                )
            elif layer_to_process.layer.geometryType() == qgis.core.Qgis.GeometryType.Point:
                task = qgis.core.QgsProcessingAlgRunnerTask(
                    algorithm=self.inputs_from_points_algorithm,
                    parameters={
                        ConeforInputsPoint.INPUT_POINT_LAYER[0]: (
                            layer_to_process.layer),
                        **common_params
                    },
                    context=self.processing_context
                )
            else:
                raise RuntimeError(
                    f"layer: {layer_to_process.layer.name()!r} has invalid "
                    f"geometry type: {layer_to_process.layer.geometryType()!r}"
                )
            task.executed.connect(
                functools.partial(self.finalize_task_execution, layer_to_process)
            )
            self.processing_tasks[layer_to_process] = task
            log(f"{self.processing_tasks=}")
            task_manager.addTask(task)

    def get_conefor_input_parameters(
        self,
        data_item: schemas.TableModelItem,
        load_to_canvas: bool,
        default_node_identifier_name: Optional[str] = None,
        default_node_attribute_name: Optional[str] = None,
    ) -> schemas.ConeforInputParameters:
        node_identifier_name = (
                default_node_identifier_name or data_item.id_attribute_field_name)
        if node_identifier_name != schemas.NONE_LABEL:
            node_attribute_name = (
                    default_node_attribute_name or data_item.attribute_field_name)
            process_edge_distance = self.dialog.edge_distance_rb.isChecked()
            return schemas.ConeforInputParameters(
                layer=data_item.layer,
                id_attribute_field_name=(
                    node_identifier_name
                    if node_identifier_name != schemas.AUTOGENERATE_NODE_ID_LABEL
                    else None
                ),
                attribute_field_name=(
                    node_attribute_name if node_attribute_name != schemas.GENERATE_FROM_AREA_LABEL
                    else None
                ),
                connections_method=(
                    schemas.NodeConnectionType.EDGE_DISTANCE if process_edge_distance
                    else schemas.NodeConnectionType.CENTROID_DISTANCE
                )
            )
        else:
            raise NoUniqueFieldError

    def finalize_task_execution(
        self, layer_params: schemas.ConeforInputParameters, *args, **kwargs):
        log(f"Finalizing task execution for layer params {layer_params=} {args=} {kwargs=}")

    def check_for_new_layers(self, new_layers: list[qgis.core.QgsMapLayer]):
        log("inside check_for_new_layers")
        self.start_analyzing_layers()

    def check_for_removed_layers(self, removed_layer_ids: list[str]):
        log("inside check_for_removed_layers")
        self.start_analyzing_layers(disregard_ids=removed_layer_ids)



class NoUniqueFieldError(Exception):
    pass
