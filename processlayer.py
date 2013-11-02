from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

LAYER, ID, ATTRIBUTE, AREA, EDGE, CENTROID = range(6)

class ProcessLayer(object):

    def __init__(self, qgis_layer, processor, unique_fields):
        self.qgis_layer_name = qgis_layer.name()
        self.qgis_layer = qgis_layer
        provider = qgis_layer.dataProvider()
        self.id_field_name = unique_fields[0]
        self.attribute_field_name = '<None>'
        self.process_area = False
        self.process_centroid_distance = False
        self.process_edge_distance = True


class ProcessLayerTableModel(QAbstractTableModel):

    def __init__(self, qgis_layers, current_layer, processor):
        self.processor = processor
        self._header_labels = range(6)
        self._header_labels[LAYER] = 'Layer'
        self._header_labels[ID] = 'Node ID\n(unique)'
        self._header_labels[CENTROID] = 'Centroid\ndistance'
        self._header_labels[EDGE] = 'Edge\ndistance'
        self._header_labels[AREA] = 'Calculate area\nas the node\nattribute'
        self._header_labels[ATTRIBUTE] = 'Node\nattribute'
        super(ProcessLayerTableModel, self).__init__()
        self.dirty = False
        self.data_ = qgis_layers
        current_fields = qgis_layers[current_layer]
        self.layers = [ProcessLayer(current_layer, self.processor,
                                    current_fields)]

    def rowCount(self, index=QModelIndex()):
        return len(self.layers)

    def columnCount(self, index=QModelIndex):
        return 6

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.layers)):
            result = None
        else:
            layer = self.layers[index.row()]
            column = index.column()
            if role == Qt.DisplayRole:
                if column == LAYER:
                    result = layer.qgis_layer_name
                elif column == ID:
                    result = layer.id_field_name
                elif column == ATTRIBUTE:
                    result = layer.attribute_field_name
                elif column == AREA:
                    if layer.qgis_layer.geometryType() == QGis.Point:
                        result = '<Unavailable>'
                    else:
                        result = None
                elif column == EDGE:
                    if layer.qgis_layer.geometryType() == QGis.Point:
                        result = '<Unavailable>'
                    else:
                        result = None
                else:
                    result = None
            elif role == Qt.CheckStateRole:
                if column == AREA:
                    if layer.qgis_layer.geometryType() == QGis.Point:
                        result = None
                    else:
                        if layer.process_area:
                            result = Qt.Checked
                        else:
                            result = Qt.Unchecked
                elif column == CENTROID:
                    if layer.process_centroid_distance:
                        result = Qt.Checked
                    else:
                        result = Qt.Unchecked
                elif column == EDGE:
                    if layer.qgis_layer.geometryType() == QGis.Point:
                        result = None
                    else:
                        if layer.process_edge_distance:
                            result = Qt.Checked
                        else:
                            result = Qt.Unchecked
                else:
                    result = None
            elif role == Qt.TextAlignmentRole:
                if column in (AREA, CENTROID, EDGE):
                    result = int(Qt.AlignHCenter|Qt.AlignVCenter)
                else:
                    result = None
            else:
                result = None
        return result

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            result = self._header_labels[section]
        else:
            result = QAbstractTableModel.headerData(self, section, orientation,
                                                    role)
        return result

    def flags(self, index):
        if not index.isValid():
            result = Qt.ItemIsEnabled()
        else:
            if index.column() in (AREA, CENTROID, EDGE):
                result = Qt.ItemFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable)
            else:
                result = Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                                      Qt.ItemIsEditable)
        return result

    def setData(self, index, value, role=Qt.EditRole):
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
                if layer.qgis_layer.geometryType() != QGis.Point:
                    layer.process_area = value
                else:
                    layer.process_area = False
            elif column == CENTROID:
                layer.process_centroid_distance = bool(value)
            elif column == EDGE:
                if layer.qgis_layer.geometryType() != QGis.Point:
                    layer.process_edge_distance = bool(value)
                else:
                    layer.process_edge_distance = False
            self.dirty = True
            self.emit(SIGNAL('dataChanged(QModelIndex,QModelIndex)'),
                      index, index)
            result = True
        self.emit(SIGNAL('is_runnable_check'))
        return result

    def _get_qgis_layer(self, layer_name):
        qgis_layer = None
        for la, unique_fields in self.data_.iteritems():
            if str(la.name()) == str(layer_name):
                qgis_layer = la
        return qgis_layer

    def insertRows(self, position, rows=1, index=QModelIndex()):
        self.beginInsertRows(QModelIndex(), position, position + rows - 1)
        a_layer = self.data_.keys()[0]
        unique_fields = self.data_[a_layer]
        for row in range(rows):
            self.layers.insert(position + row, ProcessLayer(a_layer,
                               self.processor, unique_fields))
        self.endInsertRows()
        self.dirty = True
        return True

    def removeRows(self, position, rows=1, index=QModelIndex()):
        result = False
        if self.rowCount() > 1:
            self.beginRemoveRows(QModelIndex(), position, position + rows - 1)
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
            if f.type() in (QVariant.Int, QVariant.Double)]
        return [f.name() for f in the_fields]


class ProcessLayerDelegate(QItemDelegate):

    def __init__(self, dialog, parent=None):
        super(ProcessLayerDelegate, self).__init__(parent)
        self.dialog = dialog

    def createEditor(self, parent, option, index):
        result = QItemDelegate.createEditor(self, parent, option, index)
        column = index.column()
        if column in (LAYER, ID, ATTRIBUTE):
            combo_box = QComboBox(parent)
            self.connect(combo_box, SIGNAL('currentIndexChanged(int)'),
                         self.commitAndCloseEditor)
            result = combo_box
        return result

    def setEditorData(self, editor, index):
        row = index.row()
        column = index.column()
        model = index.model()
        process_layers = []
        for qgis_layer, unique_fields in model.data_.iteritems():
            process_layers.append(ProcessLayer(qgis_layer, model.processor,
                                               unique_fields))
        selected_layer_name = model.layers[row].qgis_layer_name
        selected_id_field_name = model.layers[row].id_field_name
        selected_attribute_field_name = model.layers[row].attribute_field_name
        layer = model._get_qgis_layer(selected_layer_name)
        if column == LAYER:
            layer_names = [pl.qgis_layer_name for pl in process_layers]
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
            QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
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
            QItemDelegate.setModelData(self, editor, model, index)

    def commitAndCloseEditor(self):
        editor = self.sender()
        if isinstance(editor, QComboBox):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QAbstractItemDelegate.EditNextItem)
