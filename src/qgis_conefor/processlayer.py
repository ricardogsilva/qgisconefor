from qgis.PyQt import (
    QtCore,
    QtWidgets,
)

import qgis.core

from . import coneforinputsprocessor
from .utilities import log

LAYER, ID, ATTRIBUTE, AREA, EDGE, CENTROID = range(6)


class ProcessLayer:

    def __init__(
            self,
            qgis_layer: qgis.core.QgsVectorLayer,
            processor,
            unique_fields
    ):
        self.qgis_layer_name = qgis_layer.name()
        self.qgis_layer = qgis_layer
        provider = qgis_layer.dataProvider()
        self.id_field_name = unique_fields[0]
        self.attribute_field_name = '<None>'
        self.process_area = False
        self.process_centroid_distance = False
        self.process_edge_distance = True
        if qgis_layer.wkbType() == qgis.core.QgsWkbTypes.Point:  # noqa
            self.process_centroid_distance = True
            self.process_edge_distance = False


class ProcessLayerTableModel(QtCore.QAbstractTableModel):

    is_runnable_check = QtCore.pyqtSignal()

    def __init__(
            self,
            *,
            qgis_layers: dict[qgis.core.QgsVectorLayer, list[str]],
            current_layers: list[qgis.core.QgsVectorLayer],
            processor: coneforinputsprocessor.InputsProcessor,
            dialog: QtWidgets.QDialog
    ):
        self.processor = processor
        self.dialog = dialog
        self._header_labels = list(range(6))
        self._header_labels[LAYER] = 'Layer'
        self._header_labels[ID] = 'Node ID\n(unique)'
        self._header_labels[CENTROID] = 'Centroid\ndistance'
        self._header_labels[EDGE] = 'Edge\ndistance'
        self._header_labels[AREA] = 'Calculate area\nas the node\nattribute'
        self._header_labels[ATTRIBUTE] = 'Node\nattribute'
        super(ProcessLayerTableModel, self).__init__()
        self.dirty = False
        self.data_ = qgis_layers
        self.layers = []
        for la in current_layers:
            fields = qgis_layers[la]
            self.layers.append(ProcessLayer(la, self.processor, fields))

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.layers)

    def columnCount(self, index=QtCore.QModelIndex):
        return 6

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.layers)):
            result = None
        else:
            layer = self.layers[index.row()]
            locked_layer = layer
            column = index.column()
            row = index.row()
            if row != 0 and self.dialog.lock_layers_chb.isChecked():
                layer = self.layers[0]
            if role == QtCore.Qt.DisplayRole:
                if column == LAYER:
                    result = locked_layer.qgis_layer_name
                elif column == ID:
                    result = layer.id_field_name
                elif column == ATTRIBUTE:
                    result = layer.attribute_field_name
                elif column == AREA:
                    if layer.qgis_layer.wkbType() == qgis.core.QgsWkbTypes.Point:
                        result = '<Unavailable>'
                    else:
                        result = None
                elif column == EDGE:
                    if layer.qgis_layer.wkbType() == qgis.core.QgsWkbTypes.Point:
                        result = '<Unavailable>'
                    else:
                        result = None
                else:
                    result = None
            elif role == QtCore.Qt.CheckStateRole:
                if column == AREA:
                    if layer.qgis_layer.wkbType() == qgis.core.QgsWkbTypes.Point:
                        result = None
                    else:
                        if layer.process_area:
                            result = QtCore.Qt.Checked
                        else:
                            result = QtCore.Qt.Unchecked
                elif column == CENTROID:
                    if layer.process_centroid_distance:
                        result = QtCore.Qt.Checked
                    else:
                        result = QtCore.Qt.Unchecked
                elif column == EDGE:
                    if layer.qgis_layer.wkbType() == qgis.core.QgsWkbTypes.Point:
                        result = None
                    else:
                        if layer.process_edge_distance:
                            result = QtCore.Qt.Checked
                        else:
                            result = QtCore.Qt.Unchecked
                else:
                    result = None
            elif role == QtCore.Qt.TextAlignmentRole:
                if column in (AREA, CENTROID, EDGE):
                    result = int(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
                else:
                    result = None
            else:
                result = None
        return result

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            result = self._header_labels[section]
        else:
            result = QtCore.QAbstractTableModel.headerData(
                self, section, orientation, role)
        return result

    def flags(self, index):
        if self.dialog.lock_layers_chb.isChecked():
            if index.row() == 0:
                if index.column() in (AREA, CENTROID, EDGE):
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
                if index.column() in (AREA, CENTROID, EDGE):
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
        if index.isValid() and 0 <= index.row() < len(self.layers):
            layer = self.layers[index.row()]
            column = index.column()
            if column == LAYER:
                layer.qgis_layer_name = value
                layer.qgis_layer = self._get_qgis_layer(value)
            elif column == ID:
                layer.id_field_name = value
            elif column == ATTRIBUTE:
                layer.attribute_field_name = value
            elif column == AREA:
                try:
                    if layer.qgis_layer.wkbType() != qgis.core.QgsWkbTypes.Point:
                        layer.process_area = value
                    else:
                        layer.process_area = False
                except AttributeError:
                    layer.process_area = value
            elif column == CENTROID:
                layer.process_centroid_distance = value
            elif column == EDGE:
                try:
                    if layer.qgis_layer.wkbType() != qgis.core.QgsWkbTypes.Point:
                        layer.process_edge_distance = bool(value)
                    else:
                        layer.process_edge_distance = False
                except AttributeError:
                    layer.process_edge_distance = value
            self.dirty = True
            #self.emit(SIGNAL('dataChanged(QModelIndex,QModelIndex)'),
            #          index, index)
            self.dataChanged.emit(index, index)
            result = True
        self.is_runnable_check.emit()
        return result

    def _get_qgis_layer(self, layer_name):
        qgis_layer = None
        for la, unique_fields in self.data_.items():
            if str(la.name()) == str(layer_name):
                qgis_layer = la
        return qgis_layer

    def insertRows(self, position, rows=1, index=QtCore.QModelIndex()):
        self.beginInsertRows(QtCore.QModelIndex(), position, position + rows - 1)
        first_layer = next(iter(self.data_.keys()))
        unique_fields = self.data_[first_layer]
        for row in range(rows):
            self.layers.insert(
                position + row,
                ProcessLayer(first_layer, self.processor, unique_fields)
            )
        self.endInsertRows()
        self.dirty = True
        return True

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        result = False
        if self.rowCount() > 1:
            self.beginRemoveRows(QtCore.QModelIndex(), position, position + rows - 1)
            self.layers = self.layers[:position] + self.layers[position + rows:]
            self.endRemoveRows()
            self.dirty = True
            result = True
        return result

    def get_field_names(self, layer_name):
        the_layer = None
        for layer in self.data_.keys():
            if str(layer.name()) == str(layer_name):
                the_layer = layer
        provider = the_layer.dataProvider()
        the_fields = [f for f in provider.fields() \
            if f.type() in (QtCore.QVariant.Int, QtCore.QVariant.Double)]
        return [f.name() for f in the_fields]


class ProcessLayerDelegate(QtWidgets.QItemDelegate):

    def __init__(self, *, dialog, parent=None):
        super(ProcessLayerDelegate, self).__init__(parent)
        self.dialog = dialog

    def createEditor(self, parent, option, index):
        column = index.column()
        row = index.row()
        if column in (LAYER, ID, ATTRIBUTE):
            combo_box = QtWidgets.QComboBox(parent)
            combo_box.activated[int].connect(self.commitAndCloseEditor)
            result = combo_box
        else:
            result = QtWidgets.QItemDelegate.createEditor(
                self, parent, option, index)
        return result

    def setEditorData(self, editor, index):
        row = index.row()
        column = index.column()
        model = index.model()
        selected_layer_name = model.layers[row].qgis_layer_name
        selected_id_field_name = model.layers[row].id_field_name
        selected_attribute_field_name = model.layers[row].attribute_field_name
        layer = model._get_qgis_layer(selected_layer_name)
        if column == LAYER:
            layer_names = [la.name() for la in model.data_.keys()]
            editor.addItems(layer_names)
            cmb_index = editor.findText(selected_layer_name)
            editor.setCurrentIndex(cmb_index)
        elif column == ID:
            unique_field_names = model.data_.get(layer)
            editor.addItems(unique_field_names)
            cmb_index = editor.findText(selected_id_field_name)
            editor.setCurrentIndex(cmb_index)
        elif column == ATTRIBUTE:
            field_names = model.get_field_names(selected_layer_name)
            editor.addItems(['<None>'] + field_names)
            cmb_index = editor.findText(selected_attribute_field_name)
            editor.setCurrentIndex(cmb_index)
        else:
            QtWidgets.QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        row = index.row()
        column = index.column()
        if column == LAYER:
            model.setData(index, editor.currentText())
            selected_layer_name = str(editor.currentText())
            layer = model._get_qgis_layer(selected_layer_name)
            unique_field_names = model.data_.get(layer)
            id_index = model.index(index.row(), ID)
            attr_index = model.index(index.row(), ATTRIBUTE)
            model.setData(id_index, unique_field_names[0])
            model.setData(attr_index, '<None>')
        elif column in (ID, ATTRIBUTE):
            model.setData(index, editor.currentText())
        else:
            QtWidgets.QItemDelegate.setModelData(self, editor, model, index)

    def commitAndCloseEditor(self):
        editor = self.sender()
        if isinstance(editor, QtWidgets.QComboBox):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QtWidgets.QAbstractItemDelegate.EditNextItem)
