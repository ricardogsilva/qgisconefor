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

from . import (
    schemas,
    tablemodel,
)
from .utilities import (
    load_settings_key,
    log,
    save_settings_key,
)

UI_DIR = Path(__file__).parent / "ui"
FORM_CLASS, _ = uic.loadUiType(str(UI_DIR / "conefor_dlg.ui"))


class ConeforDialog(QtWidgets.QDialog, FORM_CLASS):

    _layers: dict[qgis.core.QgsVectorLayer, list[str]]
    iface: qgis.gui.QgisInterface
    model: Optional[tablemodel.ProcessLayerTableModel]

    # UI controls
    add_row_btn: QtWidgets.QPushButton
    buttonBox: QtWidgets.QDialogButtonBox
    centroid_distance_rb: QtWidgets.QRadioButton
    create_distances_files_chb: QtWidgets.QCheckBox
    edge_distance_rb: QtWidgets.QRadioButton
    layers_la: QtWidgets.QLabel
    lock_layers_chb: QtWidgets.QCheckBox
    progress_la: QtWidgets.QLabel
    output_la: QtWidgets.QLabel
    output_dir_le: QtWidgets.QLineEdit
    output_dir_btn: QtWidgets.QPushButton
    remove_row_btn: QtWidgets.QPushButton
    tableView: QtWidgets.QTableView
    use_selected_features_chb: QtWidgets.QCheckBox


    def __init__(self, plugin_obj, parent=None):
        super(ConeforDialog, self).__init__(parent)
        self.setupUi(self)
        self.edge_distance_rb.setChecked(True)
        self.model = None
        self.iface = plugin_obj.iface
        self.lock = QtCore.QReadWriteLock()
        self.change_ui_availability(False)
        self.buttonBox.button(self.buttonBox.Help).released.connect(self.show_help)
        self.buttonBox.button(self.buttonBox.Cancel).released.connect(self.reject)
        self.buttonBox.button(self.buttonBox.Ok).released.connect(self.accept)
        self.progress_la.setText('Analyzing layers...')
        self.use_selected_features_chb.setChecked(
            load_settings_key(
                schemas.QgisConeforSettingsKey.USE_SELECTED,
                as_boolean=True,
                default_to=False
            )
        )
        self.use_selected_features_chb.stateChanged.connect(
            self.use_selected_features_toggled)
        self._layers = {}

    def use_selected_features_toggled(self, state: int):
        save_settings_key(
            schemas.QgisConeforSettingsKey.USE_SELECTED,
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
            usable_layers: dict[qgis.core.QgsVectorLayer, list[str]]
    ):
        if any(usable_layers):
            self._layers = usable_layers
            selected_in_toc = self.iface.layerTreeView().selectedLayers()
            selected_layers = [la for la in selected_in_toc if la in self._layers.keys()]
            if not any(selected_layers):
                selected_layers.append(self._layers.keys()[0])
            self.change_ui_availability(True)
            selected_layers: list[qgis.core.QgsVectorLayer]
            self.model = tablemodel.ProcessLayerTableModel(
                qgis_layers=self._layers,
                initial_layers_to_process=selected_layers,
                dialog=self
            )
            self.tableView.setModel(self.model)
            delegate = tablemodel.ProcessLayerDelegate(dialog=self, parent=self)
            self.tableView.setItemDelegate(delegate)
            self.add_row_btn.released.connect(self.add_conefor_input)
            self.remove_row_btn.released.connect(self.remove_conefor_input)
            # self.buttonBox.button(self.buttonBox.Ok).released.connect(self.run_queries)
            self.output_dir_btn.released.connect(self.get_output_dir)
            self.lock_layers_chb.toggled.connect(self.toggle_lock_layers)
            self.model.is_runnable_check.connect(self.toggle_run_button)
            if len(selected_layers) < 2:
                self.remove_row_btn.setEnabled(False)
            self.toggle_run_button()
            output_dir = load_settings_key(
                schemas.QgisConeforSettingsKey.OUTPUT_DIR, default_to=str(Path.home()))
            self.output_dir_le.setText(output_dir)
            self.create_distances_files_chb.setChecked(False)
        else:
            self.change_ui_availability(False)
            self.progress_la.setText(
                "No suitable layers found. Please load some vector layers and check "
                "out the plugin documentation"
            )
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Foreground, QtCore.Qt.GlobalColor.red)
            self.progress_la.setPalette(palette)

    def toggle_lock_layers(self, lock):
        index = self.model.index(0, 0)
        self.tableView.setFocus()

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
        initial_dir = load_settings_key(
            schemas.QgisConeforSettingsKey.OUTPUT_DIR,
            default_to=str(Path.home())
        )
        chosen_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select output directory", directory=initial_dir)
        final_dir = chosen_dir or initial_dir
        save_settings_key(schemas.QgisConeforSettingsKey.OUTPUT_DIR, final_dir)
        self.output_dir_le.setText(final_dir)

    def toggle_run_button(self):
        """
        Toggle the active state of the run button based on the availability
        of selected layers to process.
        """
        log("inside toggle_run_button")
        all_layers_runnable = True
        # for data_item in self.model.layers_to_process:
        #     has_attr = data_item.attribute_field_name != schemas.NONE_LABEL
        #     # has_area = data_item.calculate_area_as_node_attribute
        #     has_cent = data_item.calculate_centroid_distance
        #     has_edge = data_item.calculate_edge_distance
        #     if not any((has_attr, has_cent, has_edge)):
        #         all_layers_runnable = False
        #         break
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(all_layers_runnable)

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
            self.buttonBox.button(self.buttonBox.Ok),
        ]
        for widget in widgets:
            widget.setEnabled(enabled)


class NoUniqueFieldError(Exception):
    pass

