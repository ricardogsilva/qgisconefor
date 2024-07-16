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
    save_settings_key,
)

UI_DIR = Path(__file__).parent / "ui"
FORM_CLASS, _ = uic.loadUiType(str(UI_DIR / "conefor_dlg.ui"))


class ConeforDialog(QtWidgets.QDialog, FORM_CLASS):

    _layers: dict[qgis.core.QgsVectorLayer, list[str]]
    iface: qgis.gui.QgisInterface
    model: tablemodel.ProcessLayerTableModel

    # UI controls
    add_row_btn: QtWidgets.QPushButton
    buttonBox: QtWidgets.QDialogButtonBox
    centroid_distance_rb: QtWidgets.QRadioButton
    create_distances_file_chb: QtWidgets.QCheckBox
    edge_distance_rb: QtWidgets.QRadioButton
    layers_la: QtWidgets.QLabel
    lock_layers_chb: QtWidgets.QCheckBox
    output_la: QtWidgets.QLabel
    output_dir_le: QtWidgets.QLineEdit
    output_dir_btn: QtWidgets.QPushButton
    remove_row_btn: QtWidgets.QPushButton
    tableView: QtWidgets.QTableView
    use_selected_features_chb: QtWidgets.QCheckBox

    def __init__(
            self,
            plugin_obj,
            model: tablemodel.ProcessLayerTableModel,
            parent=None
    ):
        super(ConeforDialog, self).__init__(parent)
        self.setupUi(self)
        self.edge_distance_rb.setChecked(True)
        self.model = model
        self.tableView.setModel(self.model)
        self.tableView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.iface = plugin_obj.iface
        self.lock = QtCore.QReadWriteLock()
        self.buttonBox.button(self.buttonBox.Help).released.connect(self.show_help)
        self.buttonBox.button(self.buttonBox.Cancel).released.connect(self.reject)
        self.buttonBox.button(self.buttonBox.Ok).released.connect(self.accept)
        self.add_row_btn.released.connect(self.add_conefor_input)
        self.remove_row_btn.released.connect(self.remove_conefor_input)
        self.output_dir_btn.released.connect(self.get_output_dir)
        self.lock_layers_chb.toggled.connect(self.toggle_lock_layers)
        output_dir = load_settings_key(
            schemas.QgisConeforSettingsKey.OUTPUT_DIR, default_to=str(Path.home()))
        self.output_dir_le.setText(output_dir)
        self.create_distances_file_chb.setChecked(False)

        self.use_selected_features_chb.setChecked(
            load_settings_key(
                schemas.QgisConeforSettingsKey.USE_SELECTED,
                as_boolean=True,
                default_to=False
            )
        )
        self.use_selected_features_chb.stateChanged.connect(
            self.use_selected_features_toggled)
        self.remove_row_btn.setEnabled(self.model.rowCount() > 1)
        self._layers = {}

    def use_selected_features_toggled(self, state: int):
        save_settings_key(
            schemas.QgisConeforSettingsKey.USE_SELECTED,
            True if state == QtCore.Qt.CheckState.Checked else False
        )

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


class NoUniqueFieldError(Exception):
    pass

