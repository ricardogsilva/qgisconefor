#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from ui_conefor_dlg import Ui_ConeforDialog

LAYER, ID, ATTRIBUTE, CENTROID, EDGE, AREA = range(6)

class ProcessLayer(object):

    def __init__(self, qgis_layer):
        self.qgis_layer_name = QString(qgis_layer.name())
        self.qgis_layer = qgis_layer
        provider = qgis_layer.dataProvider()
        self.field_names = [f.name() for f in provider.fields()]
        if any(self.field_names):
            self.id_field_name = QString(self.field_names[0])
        else:
            self.id_field_name = None
        self.attribute_field_name = QString('<None>')
        self.process_area = False
        self.process_centroid_distance = True
        self.process_edge_distance = False


class ProcessLayerTableModel(QAbstractTableModel):

    def __init__(self, qgis_layers, current_layer):
        self._header_labels = range(6)
        self._header_labels[LAYER] = 'Layer'
        self._header_labels[ID] = 'Unique\nattribute'
        self._header_labels[CENTROID] = 'Centroid\ndistance'
        self._header_labels[EDGE] = 'Edge\ndistance'
        self._header_labels[AREA] = 'Process\narea'
        self._header_labels[ATTRIBUTE] = 'Process\nattribute'
        super(ProcessLayerTableModel, self).__init__()
        self.dirty = False
        self.layers = [ProcessLayer(current_layer)]
        self.data_ = [la for la in qgis_layers.values()]

    def rowCount(self, index=QModelIndex()):
        return len(self.layers)

    def columnCount(self, index=QModelIndex):
        return 6

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.layers)):
            result = QVariant()
        else:
            layer = self.layers[index.row()]
            column = index.column()
            if role == Qt.DisplayRole:
                if column == LAYER:
                    result = QVariant(layer.qgis_layer_name)
                elif column == ID:
                    result = QVariant(layer.id_field_name)
                elif column == ATTRIBUTE:
                    result = QVariant(layer.attribute_field_name)
                elif column == AREA:
                    if layer.qgis_layer.geometryType() == QGis.Point:
                        result = QVariant('<Unavailable>')
                    else:
                        result = QVariant()
                elif column == EDGE:
                    if layer.qgis_layer.geometryType() == QGis.Point:
                        result = QVariant('<Unavailable>')
                    else:
                        result = QVariant()
                else:
                    result = QVariant()
            elif role == Qt.CheckStateRole:
                if column == AREA:
                    if layer.qgis_layer.geometryType() == QGis.Point:
                        result = QVariant()
                    else:
                        if layer.process_area:
                            result = QVariant(Qt.Checked)
                        else:
                            result = QVariant(Qt.Unchecked)
                elif column == CENTROID:
                    if layer.process_centroid_distance:
                        result = QVariant(Qt.Checked)
                    else:
                        result = QVariant(Qt.Unchecked)
                elif column == EDGE:
                    if layer.qgis_layer.geometryType() == QGis.Point:
                        result = QVariant()
                    else:
                        if layer.process_edge_distance:
                            result = QVariant(Qt.Checked)
                        else:
                            result = QVariant(Qt.Unchecked)
                else:
                    result = QVariant()
            else:
                result = QVariant()
        return result

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            result = QVariant(self._header_labels[section])
        else:
            result = QAbstractTableModel.headerData(self, section, orientation,
                                                    role)
        return result

    def flags(self, index):
        if not index.isValid():
            result = Qt.ItemIsEnabled()
        else:
            if index.column() in (AREA, CENTROID, EDGE):
                #result = Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                #                      Qt.ItemIsUserCheckable)
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
                layer.qgis_layer_name = value.toString()
                layer.qgis_layer = self._get_qgis_layer(value.toString())
            elif column == ID:
                layer.id_field_name = value.toString()
            elif column == ATTRIBUTE:
                layer.attribute_field_name = value.toString()
            elif column == AREA:
                if layer.qgis_layer.geometryType() != QGis.Point:
                    layer.process_area = value.toBool()
                else:
                    layer.process_area = False
            elif column == CENTROID:
                layer.process_centroid_distance = value.toBool()
            elif column == EDGE:
                if layer.qgis_layer.geometryType() != QGis.Point:
                    layer.process_edge_distance = value.toBool()
                else:
                    layer.process_edge_distance = False
            self.dirty = True
            self.emit(SIGNAL('dataChanged(QModelIndex,QModelIndex)'),
                      index, index)
            result = True
        return result

    def _get_qgis_layer(self, layer_name):
        qgis_layer = None
        for la in self.data_:
            if str(la.name()) == str(layer_name):
                qgis_layer = la
        return qgis_layer

    def insertRows(self, position, rows=1, index=QModelIndex()):
        self.beginInsertRows(QModelIndex(), position, position + rows - 1)
        for row in range(rows):
            self.layers.insert(position + row, ProcessLayer(self.data_[0]))
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
        for layer in self.data_:
            if str(layer.name()) == str(layer_name):
                the_layer = layer
        provider = the_layer.dataProvider()
        the_fields = provider.fields()
        return [f.name() for f in the_fields]


class ProcessLayerDelegate(QItemDelegate):

    def createEditor(self, parent, option, index):
        result = QItemDelegate.createEditor(self, parent, option, index)
        column = index.column()
        if column in (LAYER, ID, ATTRIBUTE):
            combo_box = QComboBox(parent)
            result = combo_box
        return result

    def setEditorData(self, editor, index):
        row = index.row()
        column = index.column()
        model = index.model()
        process_layers = [ProcessLayer(a) for a in model.data_]
        selected_layer_name = model.layers[row].qgis_layer_name
        if column == LAYER:
            layer_names = [pl.qgis_layer_name for pl in process_layers]
            editor.addItems(layer_names)
            cmb_index = editor.findText(selected_layer_name)
            editor.setCurrentIndex(cmb_index)
        elif column == ID:
            field_names = model.get_field_names(selected_layer_name)
            editor.addItems(field_names)
        elif column == ATTRIBUTE:
            field_names = model.get_field_names(selected_layer_name)
            editor.addItems(['<None>'] + field_names)
        else:
            QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        column = index.column()
        if column == LAYER:
            model.setData(index, QVariant(editor.currentText()))
            selected_layer_name = str(editor.currentText())
            field_names = model.get_field_names(selected_layer_name)
            #id_index = model.index(index.row(), index.column() + 1)
            #attr_index = model.index(index.row(), index.column() + 2)
            id_index = model.index(index.row(), ID)
            attr_index = model.index(index.row(), ATTRIBUTE)
            model.setData(id_index, QVariant(field_names[0]))
            model.setData(attr_index, QVariant('<None>'))
        else:
            QItemDelegate.setModelData(self, editor, model, index)


class ConeforDialog(QDialog,  Ui_ConeforDialog):

    def __init__(self, layers_dict, current_layer, processor, parent=None):
        super(ConeforDialog, self).__init__(parent)
        self.layers = layers_dict
        self.processor = processor
        self.model = ProcessLayerTableModel(self.layers, current_layer)
        self.setupUi(self)
        self.tableView.setModel(self.model)
        delegate = ProcessLayerDelegate(self)
        self.tableView.setItemDelegate(delegate)
        QObject.connect(self.add_row_btn, SIGNAL('released()'), self.add_row)
        QObject.connect(self.remove_row_btn, SIGNAL('released()'),
                        self.remove_row)
        QObject.connect(self.run_btn, SIGNAL('released()'), self.run_queries)
        self.connect(self.output_dir_btn, SIGNAL('released()'), self.get_output_dir)
        self.remove_row_btn.setEnabled(False)
        self.output_dir_le.setText(os.path.expanduser('~'))

    def add_row(self):
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

    def remove_row(self):
        index = self.tableView.currentIndex()
        row = index.row()
        self.model.removeRows(row)
        if self.model.rowCount() == 1:
            self.remove_row_btn.setEnabled(False)

    def get_output_dir(self):
        home_dir = os.path.expanduser('~')
        output_dir = QFileDialog.getExistingDirectory(self, 'Select output ' \
                'directory', directory=home_dir)
        if output_dir == '':
            output_dir = home_dir
        self.output_dir_le.setText(output_dir)

    def run_queries(self):
        layers = []
        for la in self.model.layers:
            if str(la.attribute_field_name) == '<None>':
                attribute_field_name = None
            else:
                attribute_field_name = la.attribute_field_name
            the_data = {
                'layer' : la.qgis_layer,
                'id_attribute' : la.id_field_name,
                'attribute' : attribute_field_name,
                'area' : la.process_area,
                'centroid_distance' : la.process_centroid_distance,
                'edge_distance' : la.process_edge_distance,
            }
            layers.append(the_data)
        output_dir = str(self.output_dir_le.text())
        create_distance_files = self.create_distances_files_chb.isChecked()
        self.processor.run_queries(layers, output_dir, create_distance_files)
