import dataclasses
import enum
from typing import Optional

from qgis.PyQt import (
    QtCore,
    QtWidgets,
)

import qgis.core

from . import schemas


class ModelLabel(enum.Enum):

    LAYER = 0
    ID = 1
    ATTRIBUTE = 2
    NODES_TO_ADD = 3


class TableModelLabel(enum.Enum):
    AUTOGENERATE = "<AUTOGENERATE>"
    GENERATE_FROM_AREA = "<GENERATE_FROM_AREA>"
    UNAVAILABLE = "<UNAVAILABLE>"
    NONE = "<NONE>"


@dataclasses.dataclass
class TableModelItem:
    layer: qgis.core.QgsVectorLayer
    id_attribute_field_name: str = TableModelLabel.AUTOGENERATE.value
    attribute_field_name: str = TableModelLabel.GENERATE_FROM_AREA.value
    nodes_to_add_field_name: str = TableModelLabel.NONE.value


class ProcessLayerTableModel(QtCore.QAbstractTableModel):
    _header_labels = {
        ModelLabel.LAYER: "Layer",
        ModelLabel.ID: "Node ID\n(unique)",
        ModelLabel.ATTRIBUTE: "Node\nattribute",
        ModelLabel.NODES_TO_ADD: "Nodes\nto add",
    }

    is_runnable_check = QtCore.pyqtSignal()

    lock_layers: bool
    data_: dict[qgis.core.QgsVectorLayer, schemas.LayerRelevantFields]
    dialog: QtWidgets.QDialog
    dirty: bool
    layers_to_process: list[TableModelItem]

    def __init__(
            self,
            *,
            qgis_layers: dict[qgis.core.QgsVectorLayer, schemas.LayerRelevantFields],
            initial_layers_to_process: list[qgis.core.QgsVectorLayer],
            dialog: QtWidgets.QDialog,
            lock_layers: bool = False,
    ):
        self.dialog = dialog
        super(ProcessLayerTableModel, self).__init__()
        self.dirty = False
        self.data_ = qgis_layers
        self.lock_layers = lock_layers
        self.layers_to_process = []
        for la in initial_layers_to_process:
            self.layers_to_process.append(TableModelItem(layer=la))

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.layers_to_process)

    def columnCount(self, index=QtCore.QModelIndex):
        return len(self._header_labels)

    def data(self, index, role=QtCore.Qt.DisplayRole) -> Optional[str]:
        if not index.isValid() or not (0 <= index.row() < len(self.layers_to_process)):
            result = None
        else:
            data_item = self.layers_to_process[index.row()]
            locked_data_item = data_item
            column = ModelLabel(index.column())
            row = index.row()
            if row != 0 and self.lock_layers:
                data_item = locked_data_item
            if role == QtCore.Qt.DisplayRole:
                if column == ModelLabel.LAYER:
                    result = locked_data_item.layer.name()
                elif column == ModelLabel.ID:
                    result = data_item.id_attribute_field_name
                elif column == ModelLabel.ATTRIBUTE:
                    result = data_item.attribute_field_name
                elif column == ModelLabel.NODES_TO_ADD:
                    result = data_item.nodes_to_add_field_name
                else:
                    result = None
            else:
                result = None
        return result

    def headerData(self, section: int, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            model_label = ModelLabel(section)
            result = self._header_labels[model_label]
        else:
            result = QtCore.QAbstractTableModel.headerData(
                self, section, orientation, role)
        return result

    def flags(self, index):
        if self.lock_layers:
            if index.row() == 0 or index.column() == 0:
                result = QtCore.Qt.ItemFlags(
                    QtCore.QAbstractTableModel.flags(self, index) |
                    QtCore.Qt.ItemIsEditable
                )
            else:
                result = QtCore.Qt.NoItemFlags
        else:
            if not index.isValid():
                result = QtCore.Qt.ItemIsEnabled()
            else:
                result = QtCore.Qt.ItemFlags(
                    QtCore.QAbstractTableModel.flags(self, index) |
                    QtCore.Qt.ItemIsEditable
                )
        return result

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        result = False
        if index.isValid() and 0 <= index.row() < len(self.layers_to_process):
            data_item = self.layers_to_process[index.row()]
            column = ModelLabel(index.column())
            if column == ModelLabel.LAYER:
                data_item.layer = self.get_qgis_layer(value)
            elif column == ModelLabel.ID:
                data_item.id_attribute_field_name = value
            elif column == ModelLabel.ATTRIBUTE:
                data_item.attribute_field_name = value
            elif column == ModelLabel.NODES_TO_ADD:
                data_item.nodes_to_add_field_name = value
            self.dirty = True
            self.dataChanged.emit(index, index)
            result = True
        self.is_runnable_check.emit()
        return result

    def get_qgis_layer(self, layer_name: str) -> qgis.core.QgsVectorLayer:
        for layer in self.data_.keys():
            if layer.name() == layer_name:
                return layer
        else:
            raise RuntimeError(f"Could not find QGIS layer from name {layer_name!r}")

    def insertRows(self, position, rows=1, index=QtCore.QModelIndex()):
        self.beginInsertRows(QtCore.QModelIndex(), position, position + rows - 1)
        first_layer = next(iter(self.data_.keys()))
        if len(self.data_[first_layer].binary_value_field_names) > 0:
            nodes_to_add_field_name = TableModelLabel.NONE.value
        else:
            nodes_to_add_field_name = TableModelLabel.UNAVAILABLE.value
        for row in range(rows):
            self.layers_to_process.insert(
                position + row,
                TableModelItem(
                    layer=first_layer, nodes_to_add_field_name=nodes_to_add_field_name)
            )
        self.endInsertRows()
        self.dirty = True
        return True

    def add_layers(self, layers: list[qgis.core.QgsVectorLayer]):
        position = 0
        self.beginInsertRows(QtCore.QModelIndex(), position, position + len(layers) - 1)
        for idx, layer in enumerate(layers):
            is_known_layer = bool(self.data_.get(layer, False))
            if is_known_layer:
                if len(self.data_[layer].binary_value_field_names) > 0:
                    nodes_to_add_field_name = TableModelLabel.NONE.value
                else:
                    nodes_to_add_field_name = TableModelLabel.UNAVAILABLE.value
                self.layers_to_process.insert(
                    position + idx,
                    TableModelItem(
                        layer=layer,
                        nodes_to_add_field_name=nodes_to_add_field_name
                    )
                )
        self.endInsertRows()

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        result = False
        if self.rowCount() > 0:
            self.beginRemoveRows(QtCore.QModelIndex(), position, position + rows - 1)
            self.layers_to_process = (
                    self.layers_to_process[:position] +
                    self.layers_to_process[position + rows:]
            )
            self.endRemoveRows()
            self.dirty = True
            result = True
        return result

    def get_field_names(self, layer_name: str) -> schemas.LayerRelevantFields:
        layer = self.get_qgis_layer(layer_name)
        return self.data_[layer]


class ProcessLayerDelegate(QtWidgets.QItemDelegate):

    def __init__(self, *, parent=None):
        super(ProcessLayerDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        column = ModelLabel(index.column())
        combo_box_columns = (
            ModelLabel.LAYER,
            ModelLabel.ID,
            ModelLabel.ATTRIBUTE,
            ModelLabel.NODES_TO_ADD,
        )
        if column in combo_box_columns:
            combo_box = QtWidgets.QComboBox(parent)
            combo_box.activated[int].connect(self.commitAndCloseEditor)
            result = combo_box
        else:
            result = QtWidgets.QItemDelegate.createEditor(
                self, parent, option, index)
        return result

    def setEditorData(self, editor, index: QtCore.QModelIndex):
        row = index.row()
        column = ModelLabel(index.column())
        model = index.model()
        model: ProcessLayerTableModel
        data_item = model.layers_to_process[row]
        selected_layer_name = data_item.layer.name()
        selected_id_field_name = data_item.id_attribute_field_name
        selected_attribute_field_name = data_item.attribute_field_name
        if column == ModelLabel.LAYER:
            layer_names = [la.name() for la in model.data_.keys()]
            editor.addItems(layer_names)
            cmb_index = editor.findText(selected_layer_name)
            editor.setCurrentIndex(cmb_index)
        elif column == ModelLabel.ID:
            relevant_field_names = model.data_.get(data_item.layer)
            unique_field_names = (
                    [TableModelLabel.AUTOGENERATE.value] +
                    relevant_field_names.unique_field_names
            )
            editor.addItems(unique_field_names)
            cmb_index = editor.findText(
                selected_id_field_name or TableModelLabel.AUTOGENERATE.value)
            editor.setCurrentIndex(cmb_index)
        elif column == ModelLabel.ATTRIBUTE:
            relevant_field_names = model.get_field_names(selected_layer_name)
            editor.addItems(
                [TableModelLabel.GENERATE_FROM_AREA.value] +
                relevant_field_names.numerical_field_names
            )
            cmb_index = editor.findText(selected_attribute_field_name)
            editor.setCurrentIndex(cmb_index)
        elif column == ModelLabel.NODES_TO_ADD:
            relevant_field_names = (
                model.get_field_names(selected_layer_name).binary_value_field_names)
            if len(relevant_field_names) == 0:
                editor.addItems([TableModelLabel.UNAVAILABLE.value])
            else:
                editor.addItems(
                    [TableModelLabel.NONE.value] + relevant_field_names)
        else:
            QtWidgets.QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model: ProcessLayerTableModel, index):
        row = index.row()
        column = ModelLabel(index.column())
        if column == ModelLabel.LAYER:
            previous_name = model.layers_to_process[index.row()].layer.name()
            layer_name = editor.currentText()
            if previous_name != layer_name:
                model.setData(index, layer_name)
                id_index = model.index(row, ModelLabel.ID.value)
                attr_index = model.index(row, ModelLabel.ATTRIBUTE.value)
                nodes_to_add_index = model.index(row, ModelLabel.NODES_TO_ADD.value)
                model.setData(id_index, TableModelLabel.AUTOGENERATE.value)
                model.setData(attr_index, TableModelLabel.GENERATE_FROM_AREA.value)
                layer = model.get_qgis_layer(layer_name)
                if len(model.data_[layer].binary_value_field_names) > 0:
                    model.setData(nodes_to_add_index, TableModelLabel.NONE.value)
                else:
                    model.setData(nodes_to_add_index, TableModelLabel.UNAVAILABLE.value)
        elif column in (ModelLabel.ID, ModelLabel.ATTRIBUTE, ModelLabel.NODES_TO_ADD):
            model.setData(index, editor.currentText())
        else:
            QtWidgets.QItemDelegate.setModelData(self, editor, model, index)

    def commitAndCloseEditor(self):
        editor = self.sender()
        if isinstance(editor, QtWidgets.QComboBox):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QtWidgets.QAbstractItemDelegate.EditNextItem)
