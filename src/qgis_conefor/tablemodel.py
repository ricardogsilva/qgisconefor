import enum
from qgis.PyQt import (
    QtCore,
    QtWidgets,
)

import qgis.core

from . import coneforinputsprocessor
from . import schemas
from .utilities import log


class ModelLabel(enum.Enum):

    LAYER = 0
    ID = 1
    ATTRIBUTE = 2
    # AREA = 3
    # EDGE = 4
    # CENTROID = 5
    # EDGE = 3
    # CENTROID = 4


UNAVAILABLE_LABEL = "<UNAVAILABLE>"


class ProcessLayerTableModel(QtCore.QAbstractTableModel):
    _header_labels = {
        ModelLabel.LAYER: "Layer",
        ModelLabel.ID: "Node ID\n(unique)",
        ModelLabel.ATTRIBUTE: "Node\nattribute",
        # ModelLabel.AREA: "Calculate area\nas the node\nattribute",
        # ModelLabel.EDGE: "Edge\ndistance",
        # ModelLabel.CENTROID: "Centroid\ndistance",
    }

    is_runnable_check = QtCore.pyqtSignal()

    data_: dict[qgis.core.QgsVectorLayer, list[str]]
    dialog: QtWidgets.QDialog
    dirty: bool
    layers_to_process: list[schemas.TableModelItem]
    processor: coneforinputsprocessor.InputsProcessor


    def __init__(
            self,
            *,
            qgis_layers: dict[qgis.core.QgsVectorLayer, list[str]],
            initial_layers_to_process: list[qgis.core.QgsVectorLayer],
            processor: coneforinputsprocessor.InputsProcessor,
            dialog: QtWidgets.QDialog
    ):
        self.processor = processor
        self.dialog = dialog
        super(ProcessLayerTableModel, self).__init__()
        self.dirty = False
        self.data_ = qgis_layers
        self.layers_to_process = []
        for la in initial_layers_to_process:
            self.layers_to_process.append(
                schemas.TableModelItem(
                    layer=la,
                    # calculate_centroid_distance=la.geometryType() == qgis.core.Qgis.GeometryType.Point,
                    # calculate_edge_distance=la.geometryType() == qgis.core.Qgis.GeometryType.Polygon,
                )
            )

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.layers_to_process)

    def columnCount(self, index=QtCore.QModelIndex):
        return len(self._header_labels)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.layers_to_process)):
            result = None
        else:
            data_item = self.layers_to_process[index.row()]
            locked_data_item = data_item
            column = ModelLabel(index.column())
            row = index.row()
            layer_geom = data_item.layer.geometryType()
            if row != 0 and self.dialog.lock_layers_chb.isChecked():
                data_item = locked_data_item
            if role == QtCore.Qt.DisplayRole:
                if column == ModelLabel.LAYER:
                    result = locked_data_item.layer.name()
                elif column == ModelLabel.ID:
                    result = data_item.id_attribute_field_name
                elif column == ModelLabel.ATTRIBUTE:
                    result = data_item.attribute_field_name
                # elif column == ModelLabel.AREA:
                #     if layer_geom == qgis.core.Qgis.GeometryType.Point:
                #         result = UNAVAILABLE_LABEL
                #     else:
                #         result = None
                # elif column == ModelLabel.EDGE:
                #     if layer_geom == qgis.core.Qgis.GeometryType.Point:
                #         result = UNAVAILABLE_LABEL
                #     else:
                #         result = None
                else:
                    result = None
            # elif role == QtCore.Qt.CheckStateRole:
                # if column == ModelLabel.AREA:
                #     if layer_geom == qgis.core.Qgis.GeometryType.Point:
                #         result = None
                #     else:
                #         result = (
                #             QtCore.Qt.Checked
                #             if data_item.calculate_area_as_node_attribute
                #             else QtCore.Qt.Unchecked
                #         )
                # elif column == ModelLabel.CENTROID:
                # if column == ModelLabel.CENTROID:
                #         result = (
                #         QtCore.Qt.Checked if data_item.calculate_centroid_distance
                #         else QtCore.Qt.Unchecked
                #     )
                # elif column == ModelLabel.EDGE:
                #     if layer_geom == qgis.core.Qgis.GeometryType.Point:
                #         result = None
                #     else:
                #         result = (
                #             QtCore.Qt.Checked if data_item.calculate_edge_distance
                #             else QtCore.Qt.Unchecked
                #         )
                # else:
                #     result = None
            # elif role == QtCore.Qt.TextAlignmentRole:
            #     if column in (
            #             # ModelLabel.AREA,
            #             ModelLabel.CENTROID,
            #             ModelLabel.EDGE
            #     ):
            #         result = int(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            #     else:
            #         result = None
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
        # checkable_column_labels = (
            # ModelLabel.AREA,
            # ModelLabel.CENTROID,
            # ModelLabel.EDGE,
        # )
        checkable_column_labels = []
        if self.dialog.lock_layers_chb.isChecked():
            column = ModelLabel(index.column())
            if index.row() == 0:
                if column in checkable_column_labels:
                    result = QtCore.Qt.ItemFlags(
                        QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                else:
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
                column = ModelLabel(index.column())
                if column in checkable_column_labels:
                    result = QtCore.Qt.ItemFlags(
                        QtCore.Qt.ItemIsEnabled |
                        QtCore.Qt.ItemIsUserCheckable
                    )
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
            # elif column == ModelLabel.AREA:
            #     try:
            #         if data_item.layer.geometryType() != qgis.core.Qgis.Point:
            #             data_item.calculate_area_as_node_attribute = value
            #         else:
            #             data_item.calculate_area_as_node_attribute = False
            #     except AttributeError:
            #         data_item.calculate_area_as_node_attribute = value
            # elif column == ModelLabel.CENTROID:
            #     data_item.calculate_centroid_distance = value
            # elif column == ModelLabel.EDGE:
            #     try:
            #         if data_item.layer.geometryType() != qgis.core.Qgis.Point:
            #             data_item.calculate_edge_distance = bool(value)
            #         else:
            #             data_item.calculate_edge_distance = False
            #     except AttributeError:
            #         data_item.calculate_edge_distance = value
            self.dirty = True
            #self.emit(SIGNAL('dataChanged(QModelIndex,QModelIndex)'),
            #          index, index)
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
        first_layer, unique_fields = next(iter(self.data_.items()))
        geom_type = first_layer.geometryType()
        for row in range(rows):
            self.layers_to_process.insert(
                position + row,
                schemas.TableModelItem(
                    layer=first_layer,
                    id_attribute_field_name=unique_fields[0],
                    # calculate_centroid_distance=(
                    #         geom_type == qgis.core.Qgis.GeometryType.Point),
                    # calculate_edge_distance=(
                    #         geom_type == qgis.core.Qgis.GeometryType.Polygon),
                )
            )
        self.endInsertRows()
        self.dirty = True
        return True

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        result = False
        if self.rowCount() > 1:
            self.beginRemoveRows(QtCore.QModelIndex(), position, position + rows - 1)
            self.layers_to_process = (
                    self.layers_to_process[:position] +
                    self.layers_to_process[position + rows:]
            )
            self.endRemoveRows()
            self.dirty = True
            result = True
        return result

    def get_field_names(self, layer_name: str) -> list[str]:
        layer = self.get_qgis_layer(layer_name)
        return self.data_[layer]


class ProcessLayerDelegate(QtWidgets.QItemDelegate):

    dialog: QtWidgets.QDialog

    def __init__(self, *, dialog, parent=None):
        super(ProcessLayerDelegate, self).__init__(parent)
        self.dialog = dialog

    def createEditor(self, parent, option, index):
        column = ModelLabel(index.column())
        if column in (ModelLabel.LAYER, ModelLabel.ID, ModelLabel.ATTRIBUTE):
            combo_box = QtWidgets.QComboBox(parent)
            combo_box.activated[int].connect(self.commitAndCloseEditor)
            result = combo_box
        else:
            result = QtWidgets.QItemDelegate.createEditor(
                self, parent, option, index)
        return result

    def setEditorData(self, editor, index):
        row = index.row()
        column = ModelLabel(index.column())
        model = index.model()
        model: ProcessLayerTableModel
        data_item = model.layers_to_process[row]
        log(f"{data_item.layer.name()=}")
        log(f"{data_item.id_attribute_field_name=}")
        selected_layer_name = data_item.layer.name()
        selected_id_field_name = data_item.id_attribute_field_name
        log(f"{selected_layer_name=}")
        log(f"{selected_id_field_name=}")
        selected_attribute_field_name = data_item.attribute_field_name
        if column == ModelLabel.LAYER:
            layer_names = [la.name() for la in model.data_.keys()]
            editor.addItems(layer_names)
            cmb_index = editor.findText(selected_layer_name)
            editor.setCurrentIndex(cmb_index)
        elif column == ModelLabel.ID:
            unique_field_names = (
                    [schemas.AUTOGENERATE_NODE_ID_LABEL] +
                    model.data_.get(data_item.layer)
            )
            editor.addItems(unique_field_names)
            cmb_index = editor.findText(
                selected_id_field_name or schemas.AUTOGENERATE_NODE_ID_LABEL)
            editor.setCurrentIndex(cmb_index)
        elif column == ModelLabel.ATTRIBUTE:
            field_names = model.get_field_names(selected_layer_name)
            editor.addItems([schemas.GENERATE_FROM_AREA_LABEL] + field_names)
            cmb_index = editor.findText(selected_attribute_field_name)
            editor.setCurrentIndex(cmb_index)
        else:
            QtWidgets.QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model: ProcessLayerTableModel, index):
        row = index.row()
        column = ModelLabel(index.column())
        if column == ModelLabel.LAYER:
            model.setData(index, editor.currentText())
            selected_layer_name = str(editor.currentText())
            layer = model.get_qgis_layer(selected_layer_name)
            unique_field_names = [schemas.AUTOGENERATE_NODE_ID_LABEL] + model.data_.get(layer)
            id_index = model.index(row, ModelLabel.ID.value)
            attr_index = model.index(row, ModelLabel.ATTRIBUTE.value)
            model.setData(id_index, unique_field_names[0])
            model.setData(attr_index, schemas.GENERATE_FROM_AREA_LABEL)
        elif column in (ModelLabel.ID, ModelLabel.ATTRIBUTE):
            model.setData(index, editor.currentText())
        else:
            QtWidgets.QItemDelegate.setModelData(self, editor, model, index)

    def commitAndCloseEditor(self):
        editor = self.sender()
        if isinstance(editor, QtWidgets.QComboBox):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QtWidgets.QAbstractItemDelegate.EditNextItem)
