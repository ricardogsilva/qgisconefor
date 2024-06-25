import enum
import os
from typing import Optional
from pathlib import Path

import qgis.core
import qgis.gui
from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets,
    uic,
)

from . import tasks
from .processlayer import (
    ProcessLayer,
    ProcessLayerTableModel,
    ProcessLayerDelegate,
)
from .coneforinputsprocessor import InputsProcessor
from .schemas import ConeforInputParameters

UI_DIR = Path(__file__).parent / "ui"
FORM_CLASS, _ = uic.loadUiType(str(UI_DIR / "conefor_dlg.ui"))


class QgisConeforSettingsKey(enum.Enum):
    OUTPUT_DIR = "PythonPlugins/qgisconefor/output_dir"
    USE_SELECTED = "PythonPlugins/qgisconefor/use_selected_features"


class ConeforDialog(QtWidgets.QDialog, FORM_CLASS):

    # tasks
    analyzer_task: qgis.core.QgsTask
    processing_task: Optional[qgis.core.QgsTask]

    _layers: dict[qgis.core.QgsVectorLayer, list[qgis.core.QgsField]]
    iface: qgis.gui.QgisInterface
    model: Optional[ProcessLayerTableModel]
    processor: InputsProcessor

    # UI controls
    add_row_btn: QtWidgets.QPushButton
    create_distances_files_chb: QtWidgets.QCheckBox
    help_btn: QtWidgets.QPushButton
    layers_la: QtWidgets.QLabel
    lock_layers_chb: QtWidgets.QCheckBox
    progressBar: QtWidgets.QProgressBar
    progress_la: QtWidgets.QLabel
    output_la: QtWidgets.QLabel
    output_dir_le: QtWidgets.QLineEdit
    output_dir_btn: QtWidgets.QPushButton
    remove_row_btn: QtWidgets.QPushButton
    run_btn: QtWidgets.QPushButton
    tableView: QtWidgets.QTableView
    use_selected_features_chb: QtWidgets.QCheckBox


    def __init__(self, plugin_obj, parent=None):
        super(ConeforDialog, self).__init__(parent)
        self.setupUi(self)
        self.processor = plugin_obj.processor
        self.model = None
        self.iface = plugin_obj.iface
        self.lock = QtCore.QReadWriteLock()
        self.change_ui_availability(False)
        self.help_btn.released.connect(self.show_help)
        self.progress_la.setText('Analyzing layers...')
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.use_selected_features_chb.setChecked(
            self.load_settings_key(
                QgisConeforSettingsKey.USE_SELECTED,
                default_to=False
            )
        )
        self.use_selected_features_chb.stateChanged.connect(
            self.use_selected_features_toggled)
        self._layers = {}
        self.processing_task = None
        task_manager = qgis.core.QgsApplication.taskManager()
        self.analyzer_task = tasks.LayerAnalyzerTask(
            description="analyze currently loaded layers",
            layers_to_analyze=qgis.core.QgsProject.instance().mapLayers(),
        )
        self.analyzer_task.layers_analyzed.connect(self.finished_analyzing_layers)
        task_manager.addTask(self.analyzer_task)

    def use_selected_features_toggled(self, state: int):
        self.save_settings_key(
            QgisConeforSettingsKey.USE_SELECTED,
            True if state == QtCore.Qt.CheckState.Checked else False
        )

    def finished_processing_layers(
            self, new_files: Optional[list[str]] = None
    ):
        self.processing_thread.wait()
        self.change_ui_availability(True)
        if self.create_distances_files_chb.isChecked():
            for new_layer_path in new_files or []:
                if new_layer_path.endswith(".shp"):
                    layer_name = os.path.basename(new_layer_path)
                    new_layer = qgis.core.QgsVectorLayer(
                        new_layer_path, layer_name,"ogr")
                    qgis_project = qgis.core.QgsProject.instance()
                    qgis_project.addMapLayer(new_layer)

    def finished_analyzing_layers(
            self,
            usable_layers: dict[qgis.core.QgsVectorLayer, list[qgis.core.QgsField]]
    ):
        if any(usable_layers):
            self._layers = usable_layers
            selected_in_toc = self.iface.layerTreeView().selectedLayers()
            selected_layers = [la for la in selected_in_toc if la in self._layers.keys()]
            if not any(selected_layers):
                selected_layers.append(self._layers.keys()[0])
            self.change_ui_availability(True)
            selected_layers: list[qgis.core.QgsVectorLayer]
            self.model = ProcessLayerTableModel(
                qgis_layers=self._layers,
                current_layers=selected_layers,
                processor=self.processor,
                dialog=self
            )
            self.tableView.setModel(self.model)
            delegate = ProcessLayerDelegate(dialog=self, parent=self)
            self.tableView.setItemDelegate(delegate)
            self.add_row_btn.released.connect(self.add_conefor_input)
            self.remove_row_btn.released.connect(self.remove_conefor_input)
            self.run_btn.released.connect(self.run_queries)
            self.output_dir_btn.released.connect(self.get_output_dir)
            self.lock_layers_chb.toggled.connect(self.toggle_lock_layers)
            self.processor.progress_changed.connect(self.update_progress)
            self.processor.update_info.connect(self.update_info)
            self.model.is_runnable_check.connect(self.toggle_run_button)
            if len(selected_layers) < 2:
                self.remove_row_btn.setEnabled(False)
            self.toggle_run_button()
            output_dir = self.load_settings_key(
                QgisConeforSettingsKey.OUTPUT_DIR, default_to=str(Path.home()))
            self.output_dir_le.setText(output_dir)
            self.create_distances_files_chb.setChecked(False)
            self.progressBar.setValue(self.processor.global_progress)
            self.update_info("")
        else:
            self.change_ui_availability(False)
            self.progress_la.setText(
                "No suitable layers found. Please load some vector layers and check "
                "out the plugin documentation"
            )
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Foreground, QtCore.Qt.GlobalColor.red)
            self.progress_la.setPalette(palette)
        self.reset_progress_bar()

    def toggle_lock_layers(self, lock):
        index = self.model.index(0, 0)
        self.tableView.setFocus()

    def reset_progress_bar(self):
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

    def show_help(self):
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl("https://github.com/ricardogsilva/qgisconefor"))

    def add_conefor_input(self):
        row = self.model.rowCount()
        self.model.insertRows(row)
        index = self.model.index(row, 0)
        self.tableView.setFocus()
        self.tableView.setCurrentIndex(index)
        self.tableView.edit(index)
        if self.model.rowCount() > 1:
            self.remove_row_btn.setEnabled(True)
        else:
            self.remove_row_btn.setEnabled(False)

    def remove_conefor_input(self):
        last_row = self.model.rowCount() - 1
        self.model.removeRows(last_row)
        if self.model.rowCount() == 1:
            self.remove_row_btn.setEnabled(False)

    def get_output_dir(self):
        initial_dir = self.load_settings_key(
            QgisConeforSettingsKey.OUTPUT_DIR,
            default_to=str(Path.home())
        )
        chosen_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select output directory", directory=initial_dir)
        final_dir = chosen_dir or initial_dir
        self.save_settings_key(QgisConeforSettingsKey.OUTPUT_DIR, final_dir)
        self.output_dir_le.setText(final_dir)

    def save_settings_key(self, key: QgisConeforSettingsKey, value):
        settings = qgis.core.QgsSettings()
        settings.setValue(key.value, value)
        settings.sync()

    def load_settings_key(
            self,
            key: QgisConeforSettingsKey,
            default_to=None
    ):
        settings = qgis.core.QgsSettings()
        return settings.value(key.value, defaultValue=default_to)

    def get_conefor_input_parameters(
            self,
            layer_info: ProcessLayer,
            load_to_canvas: bool,
            default_node_identifier_name: Optional[str] = None,
            default_node_attribute_name: Optional[str] = None,
            default_process_area: Optional[bool] = None,
            default_process_centroid_distance: Optional[bool] = None,
            default_process_edge_distance: Optional[bool] = None,
    ) -> ConeforInputParameters:
        node_identifier_name = (
                default_node_identifier_name or layer_info.id_field_name)
        if node_identifier_name != "<None>":
            node_attribute_name = (
                    default_node_attribute_name or layer_info.attribute_field_name)
            if node_attribute_name == "<None>":
                node_attribute_name = None

            process_area = (
                default_process_area if default_process_area is not None
                else layer_info.process_area
            )
            process_centroid_distance = (
                default_process_centroid_distance
                if default_process_centroid_distance is not None
                else layer_info.process_centroid_distance
            )
            process_edge_distance = (
                default_process_edge_distance
                if default_process_edge_distance is not None
                else layer_info.process_edge_distance
            )
            return ConeforInputParameters(
                layer=layer_info.qgis_layer,
                id_attribute_field_name=node_identifier_name,
                attribute_field_name=node_attribute_name,
                attribute_file_name=(
                    f"nodes_{node_attribute_name}_{layer_info.qgis_layer.name()}"
                    if node_attribute_name else None
                ),
                area_file_name=(
                    f"nodes_calculated_area_{layer_info.qgis_layer.name()}"
                    if process_area else None
                ),
                centroid_file_name=(
                    f"distances_centroids_{layer_info.qgis_layer.name()}"
                    if process_centroid_distance else None
                ),
                edge_file_name=(
                    f"distances_edges_{layer_info.qgis_layer.name()}"
                    if process_edge_distance else None
                ),
                centroid_distance_name=(
                    f"Centroid_links_{layer_info.qgis_layer.name()}"
                    if load_to_canvas else None
                ),
                edge_distance_name=(
                    f"Edge_links_{layer_info.qgis_layer.name()}"
                    if load_to_canvas else None
                ),
            )
        else:
            raise NoUniqueFieldError

    def run_queries(self):
        self.update_progress()
        layer_inputs = []
        load_to_canvas = self.create_distances_files_chb.isChecked()
        output_dir = str(self.output_dir_le.text())
        only_selected_features = self.use_selected_features_chb.isChecked()

        kwargs = {}
        if len(self.model.layers) > 1:
            first = self.model.layers[0]
            kwargs.update({
                "default_node_identifier_name": first.id_field_name,
                "default_node_attribute_name": first.attribute_field_name,
                "default_process_area": first.process_area,
                "default_process_centroid_distance": first.process_centroid_distance,
                "default_process_edge_distance": first.process_edge_distance,
            })

        for layer_number, la in enumerate(self.model.layers):
            if layer_number == 0 or not self.lock_layers_chb.isChecked():
                input_parameters = self.get_conefor_input_parameters(
                    la, load_to_canvas)
            else:
                input_parameters = self.get_conefor_input_parameters(
                    la, load_to_canvas, **kwargs)
            layer_inputs.append(input_parameters)
        self.change_ui_availability(False)
        self.processing_task = tasks.LayerProcessorTask(
            description="Generate Conefor input files",
            conefor_processor=self.processor,
            layers_data=layer_inputs,
            output_dir=output_dir,
            use_selected_features=only_selected_features
        )
        task_manager = qgis.core.QgsApplication.taskManager()
        task_manager.addTask(self.processing_task)

    def update_progress(self):
        self.progressBar.setValue(self.processor.global_progress)

    def update_info(self, info, section=0):
        """
        Update the progress label with the input info string.

        The information displayed in the progress label is a string composed
        of three sections:

        * section 0
        * section 1
        * section 2

        Inputs:

            info - a string with the information to display in the progress
                   label
            section - an integer specifying where in the displayed string
                      should the 'info' argument be placed.
        """

        if section == 0:
            self.progress_la.setText(info)
        else:
            current_text = self.progress_la.text()
            sections = current_text.split(' - ')
            try:
                sections[section] = info
            except IndexError:
                sections.append(info)
            self.progress_la.setText(' - '.join(sections))
        if "ERROR" in info:
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Foreground, QtCore.Qt.GlobalColor.red)
            self.progress_la.setPalette(palette)

    def toggle_run_button(self):
        """
        Toggle the active state of the run button based on the availability
        of selected layers to process.
        """
        all_layers_runnable = []
        for la in self.model.layers:
            runnable = False
            if la.id_field_name != "<None>":
                has_attr = la.attribute_field_name != "<None>"
                has_area = la.process_area
                has_cent = la.process_centroid_distance
                has_edge = la.process_edge_distance
                if any((has_attr, has_area, has_cent, has_edge)):
                    runnable = True
            all_layers_runnable.append(runnable)
        if any(all_layers_runnable) and all(all_layers_runnable):
            self.run_btn.setEnabled(True)
        else:
            self.run_btn.setEnabled(False)

    def change_ui_availability(self, enabled: bool):
        widgets = [
            self.layers_la,
            self.tableView,
            self.remove_row_btn,
            self.add_row_btn,
            self.use_selected_features_chb,
            self.create_distances_files_chb,
            self.output_la,
            self.output_dir_le,
            self.output_dir_btn,
            self.progressBar,
            self.run_btn,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)


class NoUniqueFieldError(Exception):
    pass

