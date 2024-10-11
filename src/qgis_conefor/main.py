"""
A QGIS plugin for writing input files to the Conefor software.
"""

import dataclasses
import functools
import uuid
from typing import Optional

import qgis.core
import qgis.gui
from processing.tools.dataobjects import createContext
from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets,
)

# Initialize Qt resources from file resources.py
from .resources import *  # noqa

from . import (
    schemas,
    tasks,
)
from .conefordialog import ConeforDialog
from .processing.provider import ProcessingConeforProvider
from .processing.algorithms.coneforinputs import ConeforInputsPolygon
from .tablemodel import (
    TableModelItem,
    TableModelLabel,
    ProcessLayerDelegate,
    ProcessLayerTableModel,
)
from .utilities import (
    log,
    load_settings_key,
)


@dataclasses.dataclass(frozen=True)
class ConeforInputParameters:
    layer: qgis.core.QgsVectorLayer
    id_attribute_field_name: Optional[str] = None  # None means autogenerate a node id
    attribute_field_name: Optional[str] = None  # None means use area as the attribute
    nodes_to_add_field_name: Optional[str] = None  # None means do not used the 'nodes to add' Conefor feature
    connections_method: schemas.NodeConnectionType = schemas.NodeConnectionType.EDGE_DISTANCE

    def __hash__(self):
        return hash(
            "".join((
                self.layer.name(),
                self.id_attribute_field_name or "",
                self.attribute_field_name or "",
                self.nodes_to_add_field_name or "",
                self.connections_method.value,
            ))
        )


class QgisConefor:

    _action_title = "Conefor inputs"

    action: QtWidgets.QAction
    dialog: Optional[QtWidgets.QDialog]
    processing_provider: ProcessingConeforProvider
    algorithm: Optional[qgis.core.QgsProcessingAlgorithm]
    model: Optional[ProcessLayerTableModel]
    processing_context: Optional[qgis.core.QgsProcessingContext]
    _processing_tasks: dict[
        str,
        qgis.core.QgsProcessingAlgRunnerTask
    ]
    _task_results: dict[str, bool]

    analyzer_task: Optional[tasks.LayerAnalyzerTask]

    def __init__(self, iface: qgis.gui.QgisInterface):
        self.iface = iface
        self.dialog = None
        self.model = ProcessLayerTableModel(
            qgis_layers={},
            initial_layers_to_process=[],
            lock_layers=False,
            dialog=None
        )
        self.processing_provider = ProcessingConeforProvider()
        self.processing_context = None
        self.algorithm = None
        self._processing_tasks = {}
        self._task_results = {}

    def init_processing(self):
        processing_registry = qgis.core.QgsApplication.processingRegistry()
        processing_registry.addProvider(self.processing_provider)

    def initGui(self):
        self.init_processing()
        processing_registry = qgis.core.QgsApplication.processingRegistry()
        self.algorithm = processing_registry.createAlgorithmById(
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
        self.action.setEnabled(False)
        self.iface.addPluginToVectorMenu(None, self.action)
        self.iface.addVectorToolBarIcon(self.action)
        qgis_project = qgis.core.QgsProject.instance()
        qgis_project.legendLayersAdded.connect(self.start_tracking_layers)
        qgis_project.layersRemoved.connect(self.check_for_removed_layers)

    def unload(self):
        processing_registry = qgis.core.QgsApplication.processingRegistry()
        processing_registry.removeProvider(self.processing_provider)
        qgis_project = qgis.core.QgsProject.instance()
        qgis_project.legendLayersAdded.disconnect(self.start_tracking_layers)
        qgis_project.layersRemoved.disconnect(self.check_for_removed_layers)
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
        delegate = ProcessLayerDelegate()
        self.dialog.tableView.setItemDelegate(delegate)
        self.model.removeRows(position=0, rows=self.model.rowCount())
        selected_layers = self.iface.layerTreeView().selectedLayers()
        # self.model.insertRows(0, rows=1)
        selected_usable = [la for la in selected_layers if la in self.model.data_]
        if len(selected_usable) > 0:
            self.model.add_layers(selected_usable)
        else:
            self.model.insertRows(0, rows=1)
        exist_selected_features = False
        for usable_layer in self.model.data_:
            if usable_layer.selectedFeatureCount() > 0:
                exist_selected_features = True
                break
        self.dialog.use_selected_features_chb.setChecked(exist_selected_features)
        self.dialog.show()

    def finished_analyzing_layers(
            self,
            usable_layers: dict[qgis.core.QgsVectorLayer, schemas.LayerRelevantFields],
    ):
        self.model.data_ = usable_layers
        self.action.setEnabled(any(usable_layers))

    def handle_dialog_closed(self, result: int):
        log(f"Dialog has been closed with result {result!r}")
        self.dialog.hide()

    def _process_layer(
            self,
            layer_params: ConeforInputParameters,
            output_dir: str,
            use_selected_features: bool
    ):
        process_id = schemas.PROCESSING_TASK_ID_SEPARATOR.join((
            str(uuid.uuid4()),
            layer_params.layer.name()
        ))
        input_layer_param = qgis.core.QgsProcessingFeatureSourceDefinition(
            source=layer_params.layer.id(),
            selectedFeaturesOnly=use_selected_features,
            featureLimit=-1,
            geometryCheck=self.processing_context.invalidGeometryCheck(),
        )
        connection_method = ConeforInputsPolygon._NODE_DISTANCE_CHOICES.index(
            layer_params.connections_method.value)
        task = qgis.core.QgsProcessingAlgRunnerTask(
            algorithm=self.algorithm,
            parameters={
                ConeforInputsPolygon.INPUT_NODE_IDENTIFIER_NAME[0]: (
                        layer_params.id_attribute_field_name or ""),
                ConeforInputsPolygon.INPUT_NODE_ATTRIBUTE_NAME[0]: (
                        layer_params.attribute_field_name or ""),
                ConeforInputsPolygon.INPUT_NODES_TO_ADD_ATTRIBUTE_NAME[0]: (
                    layer_params.nodes_to_add_field_name or ""),
                ConeforInputsPolygon.INPUT_DISTANCE_THRESHOLD[0]: "",
                ConeforInputsPolygon.INPUT_OUTPUT_DIRECTORY[0]: output_dir,
                ConeforInputsPolygon.INPUT_POLYGON_LAYER[0]: (
                    input_layer_param),
                ConeforInputsPolygon.INPUT_NODE_CONNECTION_DISTANCE_METHOD[0]: (
                    connection_method),
            },
            context=self.processing_context
        )
        task.executed.connect(
            functools.partial(
                self.finalize_task_execution, process_id, layer_params)
        )
        self._processing_tasks[process_id] = task
        task_manager = qgis.core.QgsApplication.taskManager()
        log(f"About to enqueue task with process_id: {process_id!r}")
        task_manager.addTask(task)

    def prepare_conefor_inputs(self):
        layer_inputs = set()
        output_dir = str(self.dialog.output_dir_le.text())
        only_selected_features = self.dialog.use_selected_features_chb.isChecked()

        kwargs = {}
        if len(self.dialog.model.layers_to_process) > 1:
            first = self.dialog.model.layers_to_process[0]
            kwargs.update({
                "default_node_identifier_name": first.id_attribute_field_name,
                "default_node_attribute_name": first.attribute_field_name,
                "default_nodes_to_add_attribute_name": first.nodes_to_add_field_name,
            })
        for idx, data_item in enumerate(self.dialog.model.layers_to_process):
            if idx == 0 or not self.dialog.lock_layers_chb.isChecked():
                input_parameters = self.get_conefor_input_parameters(data_item)
            else:
                input_parameters = self.get_conefor_input_parameters(
                    data_item, **kwargs)
            layer_inputs.add(input_parameters)
        self.processing_context = createContext()
        for layer_to_process in layer_inputs:
            self._process_layer(
                layer_to_process,
                output_dir=output_dir,
                use_selected_features=only_selected_features,
            )

    def get_conefor_input_parameters(
        self,
        data_item: TableModelItem,
        default_node_identifier_name: Optional[str] = None,
        default_node_attribute_name: Optional[str] = None,
        default_nodes_to_add_attribute_name: Optional[str] = None,
    ) -> ConeforInputParameters:
        node_identifier_name = (
                default_node_identifier_name or data_item.id_attribute_field_name)
        if node_identifier_name != TableModelLabel.NONE.value:
            node_attribute_name = (
                    default_node_attribute_name or data_item.attribute_field_name)
            nodes_to_add_attribute_name = (
                default_nodes_to_add_attribute_name or data_item.nodes_to_add_field_name
            )
            process_edge_distance = self.dialog.edge_distance_rb.isChecked()
            return ConeforInputParameters(
                layer=data_item.layer,
                id_attribute_field_name=(
                    node_identifier_name
                    if node_identifier_name != TableModelLabel.AUTOGENERATE.value
                    else None
                ),
                attribute_field_name=(
                    node_attribute_name if node_attribute_name != TableModelLabel.GENERATE_FROM_AREA.value
                    else None
                ),
                nodes_to_add_field_name=(
                    nodes_to_add_attribute_name
                    if nodes_to_add_attribute_name not in (
                        TableModelLabel.UNAVAILABLE.value, TableModelLabel.NONE.value
                    ) else None
                ),
                connections_method=(
                    schemas.NodeConnectionType.EDGE_DISTANCE if process_edge_distance
                    else schemas.NodeConnectionType.CENTROID_DISTANCE
                )
            )
        else:
            raise NoUniqueFieldError

    def finalize_task_execution(
            self,
            process_id: str,
            layer_params: ConeforInputParameters,
            was_successful: bool,
            results: dict,
    ):
        log(f"Finalizing task {process_id!r} with layer params {layer_params=} {was_successful=} {results=}")
        unique_part, dynamic_part = process_id.partition(
            schemas.PROCESSING_TASK_ID_SEPARATOR)[::2]

        if results.get("output_generated_layer") is not None:
            log("loading generated layer onto map canvas...")
            layer_store = self.processing_context.temporaryLayerStore()
            temp_store_layer_id = results["output_generated_layer"]
            log(f"{layer_store.mapLayers()=}")
            temp_store_output_layer = layer_store.mapLayers()[temp_store_layer_id]
            output_layer = layer_store.takeMapLayer(temp_store_output_layer)
            output_layer.setName(f"{layer_params.layer.name()}_conefor")
            qgis_project = qgis.core.QgsProject.instance()
            qgis_project.addMapLayer(output_layer)

        if dynamic_part != layer_params.layer.name():
            _, distance_part = dynamic_part.rpartition(
                schemas.PROCESSING_TASK_ID_SEPARATOR)[::2]
            if "distance" in dynamic_part:
                log("loading distance layer onto map canvas...")
                temp_store_layer_id = results["output"]
                layer_store = self.processing_context.temporaryLayerStore()
                temp_store_output_layer = layer_store.mapLayers()[temp_store_layer_id]
                output_layer = layer_store.takeMapLayer(temp_store_output_layer)
                output_layer.setName(f"{layer_params.layer.name()}_{distance_part}")
                qgis_project = qgis.core.QgsProject.instance()
                qgis_project.addMapLayer(output_layer)
        self._task_results[process_id] = was_successful
        del self._processing_tasks[process_id]
        all_done = len(self._processing_tasks) == 0
        if all_done:
            if not all(self._task_results.values()):
                self.iface.messageBar().pushMessage(
                    "Conefor inputs",
                    "Some tasks failed - Check the Processing tab of the QGIS logs for more info",
                    level=qgis.core.Qgis.Critical
                )
            else:
                message_widget = self.iface.messageBar().createMessage(
                    "Conefor inputs", "Plugin finished execution")
                open_output_dir_btn = QtWidgets.QPushButton(message_widget)
                open_output_dir_btn.setText("Open output directory")
                open_output_dir_btn.pressed.connect(self.open_output_dir)
                message_widget.layout().addWidget(open_output_dir_btn)
                self.iface.messageBar().pushWidget(
                    message_widget,
                    level=qgis.core.Qgis.Info
                )
            self._task_results = {}

    def start_tracking_layers(self, new_layers: list[qgis.core.QgsMapLayer]):
        for layer in (
                l for l in new_layers
                if l.type() == qgis.core.QgsMapLayer.LayerType.Vector
        ):
            layer: qgis.core.QgsVectorLayer
            if layer.geometryType() == qgis.core.Qgis.GeometryType.Polygon:
                layer.committedAttributesAdded.connect(self._react_to_layer_attributes_added)
                layer.committedAttributesDeleted.connect(self._react_to_layer_attributes_deleted)
        self.start_analyzing_layers()

    def check_for_removed_layers(self, removed_layer_ids: list[str]):
        self.start_analyzing_layers(disregard_ids=removed_layer_ids)

    def open_output_dir(self):
        output_dir = load_settings_key(
            schemas.QgisConeforSettingsKey.OUTPUT_DIR)
        output_dir_url = QtCore.QUrl.fromLocalFile(output_dir)
        QtGui.QDesktopServices.openUrl(output_dir_url)

    def _react_to_layer_attributes_added(
            self,
            layer_id: str,
            added_attributes: list[qgis.core.QgsField]
    ):
        log(f"inside _react_to_layer_attributes_added called - {locals()}")
        self.start_analyzing_layers()

    def _react_to_layer_attributes_deleted(
            self,
            layer_id: str,
            deleted_attributes: list[int],
    ):
        log(f"inside _react_to_layer_attributes_deleted called - {locals()}")
        self.start_analyzing_layers()



class NoUniqueFieldError(Exception):
    pass
