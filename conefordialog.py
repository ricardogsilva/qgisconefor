#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from ui_conefor_dlg import Ui_ConeforDialog

LAYER, ID, ATTRIBUTE, CENTROID, EDGE, AREA = range(6)

class NoUniqueFieldError(Exception):
    pass

class ProcessLayer(object):

    def __init__(self, qgis_layer):
        self.qgis_layer_name = qgis_layer.name()
        self.qgis_layer = qgis_layer
        provider = qgis_layer.dataProvider()
        self.field_names = [f.name() for f in provider.fields()]
        if any(self.field_names):
            self.id_field_name = self.field_names[0]
        else:
            self.id_field_name = None
        self.attribute_field_name = '<None>'
        self.process_area = False
        self.process_centroid_distance = True
        self.process_edge_distance = False


class ProcessLayerTableModel(QAbstractTableModel):

    def __init__(self, qgis_layers, current_layer, use_selected=False):
        self._header_labels = range(6)
        self._header_labels[LAYER] = 'Layer'
        self._header_labels[ID] = 'Unique\nattribute'
        self._header_labels[CENTROID] = 'Centroid\ndistance'
        self._header_labels[EDGE] = 'Edge\ndistance'
        self._header_labels[AREA] = 'Process\narea'
        self._header_labels[ATTRIBUTE] = 'Process\nattribute'
        super(ProcessLayerTableModel, self).__init__()
        self.dirty = False
        self.data_ = []
        for layer in qgis_layers.values():
            unique_fields = self._get_unique_fields(layer, use_selected)
            if any(unique_fields):
                self.data_.append(layer)
        self.layers = []
        if current_layer in self.data_:
            self.layers.append(ProcessLayer(current_layer))
        else:
            self.layers.append(ProcessLayer(self.data_[0]))

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

    def _get_unique_fields(self, layer, use_selected):
        '''
        Return the names of the attributes that contain unique values only.

        Inputs:

            layer_name - A string with the name of the layer to check

            use_selected - A boolean indicating if the currently selected
                features are the only ones to consider when looking for unique
                values.

        Returns a list of strings with the names of the fields that have only
        unique values.
        '''

        result = []
        fields = layer.dataProvider().fields()
        all_ = self._get_all_values(layer, use_selected)
        for f in fields:
            the_values = [v['value'] for v in all_ if v['field'] == f.name()]
            unique_values = set(the_values)
            if len(the_values) == len(unique_values):
                result.append(f.name())
        return result

    def _get_all_values(self, layer, use_selected):
        result = []
        fields = layer.dataProvider().fields()
        if use_selected:
            features = layer.selectedFeatures()
        else:
            features = layer.getFeatures()
        for feat in features:
            for field in fields:
                result.append({
                    'field' : field.name(),
                    'value' : feat.attribute(field.name()),
                })
        return result


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
        process_layers = [ProcessLayer(a) for a in model.data_]
        selected_layer_name = model.layers[row].qgis_layer_name
        layer = model._get_qgis_layer(selected_layer_name)
        if column == LAYER:
            layer_names = [pl.qgis_layer_name for pl in process_layers]
            editor.addItems(layer_names)
            cmb_index = editor.findText(selected_layer_name)
            editor.setCurrentIndex(cmb_index)
        elif column == ID:
            use_selected = self.dialog.use_selected_features_chb.isChecked()
            unique_field_names = model._get_unique_fields(layer, use_selected)
            if not any(unique_field_names):
                unique_field_names = ['<None>']
            editor.addItems(unique_field_names)
        elif column == ATTRIBUTE:
            field_names = model.get_field_names(selected_layer_name)
            editor.addItems(['<None>'] + field_names)
        else:
            QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        column = index.column()
        if column == LAYER:
            model.setData(index, editor.currentText())
            selected_layer_name = str(editor.currentText())
            layer = model._get_qgis_layer(selected_layer_name)
            use_selected = self.dialog.use_selected_features_chb.isChecked()
            unique_field_names = model._get_unique_fields(layer, use_selected)
            if not any(unique_field_names):
                unique_field_names = ['<None>']
            id_index = model.index(index.row(), ID)
            attr_index = model.index(index.row(), ATTRIBUTE)
            model.setData(id_index, unique_field_names[0])
            model.setData(attr_index, '<None>')
        else:
            QItemDelegate.setModelData(self, editor, model, index)

    def commitAndCloseEditor(self):
        editor = self.sender()
        if isinstance(editor, QComboBox):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QAbstractItemDelegate.EditNextItem)


class ConeforDialog(QDialog,  Ui_ConeforDialog):

    _settings_key = 'PythonPlugins/coneforinputs'

    def __init__(self, layers_dict, current_layer, processor, parent=None):
        super(ConeforDialog, self).__init__(parent)
        self.setupUi(self)
        self.layers = layers_dict
        if self.exist_selected_features():
            self.use_selected_features_chb.setEnabled(True)
            self.use_selected_features_chb.setChecked(True)
        else:
            self.use_selected_features_chb.setEnabled(False)
        use_selected = self.use_selected_features_chb.isChecked()
        self.processor = processor
        self.model = ProcessLayerTableModel(self.layers, current_layer,
                                            use_selected)
        self.tableView.setModel(self.model)
        delegate = ProcessLayerDelegate(self, self)
        self.tableView.setItemDelegate(delegate)
        QObject.connect(self.add_row_btn, SIGNAL('released()'), self.add_row)
        QObject.connect(self.remove_row_btn, SIGNAL('released()'),
                        self.remove_row)
        QObject.connect(self.run_btn, SIGNAL('released()'), self.run_queries)
        QObject.connect(self.processor, SIGNAL('progress_changed'),
                        self.update_progress)
        QObject.connect(self.processor, SIGNAL('update_info'),
                        self.update_info)
        QObject.connect(self.model, SIGNAL('is_runnable_check'),
                        self.toggle_run_button)
        self.connect(self.output_dir_btn, SIGNAL('released()'), self.get_output_dir)
        self.remove_row_btn.setEnabled(False)
        self.toggle_run_button()
        output_dir = self.load_settings('output_dir')
        if str(output_dir) == '':
            output_dir = os.path.expanduser('~')
        self.output_dir_le.setText(output_dir)
        self.create_distances_files_chb.setChecked(True)
        self.progressBar.setValue(self.processor.global_progress)
        self.update_info('')

    def exist_selected_features(self):
        exist_selected = False
        for layer in self.layers.values():
            if layer.selectedFeatureCount() > 1:
                exist_selected = True
        return exist_selected

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
        self.save_settings('%s/output_dir' % self._settings_key, output_dir)

    def save_settings(self, key, value):
        settings = QSettings()
        settings.setValue(key, value)
        settings.sync()

    def load_settings(self, key):
        settings = QSettings()
        return settings.value('%s/%s' % (self._settings_key ,key))

    def run_queries(self):
        self.update_progress()
        layers = []
        for la in self.model.layers:
            if la.id_field_name == '<None>':
                raise NoUniqueFieldError
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
        only_selected_features = self.use_selected_features_chb.isChecked()
        self.processor.run_queries(layers, output_dir, create_distance_files,
                                   only_selected_features)

    def update_progress(self):
        self.progressBar.setValue(self.processor.global_progress)

    def update_info(self, info, section=0):
        '''
        Update the progess label with the input info string.
        '''

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

    def toggle_run_button(self):
        '''
        Toggle the active state of the run button based on the availability
        of selected layers to process.
        '''

        all_layers_runnable = []
        for la in self.model.layers:
            runnable = False
            if la.id_field_name != '<None>':
                has_attr = la.attribute_field_name != '<None>'
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
