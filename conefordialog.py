#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time # to be deleted

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *
from qgis.utils import showPluginHelp

from ui_conefor_dlg import Ui_ConeforDialog
from ui_help_dlg import Ui_Dialog

LAYER, ID, ATTRIBUTE, CENTROID, EDGE, AREA = range(6)

class NoUniqueFieldError(Exception):
    pass

class ProcessLayer(object):

    def __init__(self, qgis_layer, processor):
        self.qgis_layer_name = qgis_layer.name()
        self.qgis_layer = qgis_layer
        provider = qgis_layer.dataProvider()
        unique_field_names = processor.get_unique_fields(qgis_layer)
        self.id_field_name = unique_field_names[0]
        self.attribute_field_name = '<None>'
        self.process_area = False
        self.process_centroid_distance = True
        self.process_edge_distance = False


class ProcessLayerTableModel(QAbstractTableModel):

    def __init__(self, qgis_layers, current_layer, processor):
        self.processor = processor
        self._header_labels = range(6)
        self._header_labels[LAYER] = 'Layer'
        self._header_labels[ID] = 'Unique\nattribute'
        self._header_labels[CENTROID] = 'Centroid\ndistance'
        self._header_labels[EDGE] = 'Edge\ndistance'
        self._header_labels[AREA] = 'Process\narea'
        self._header_labels[ATTRIBUTE] = 'Process\nattribute'
        super(ProcessLayerTableModel, self).__init__()
        self.dirty = False
        self.data_ = qgis_layers.values()
        self.layers = [ProcessLayer(current_layer, self.processor)]

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
            self.layers.insert(position + row, ProcessLayer(self.data_[0],
                               self.processor))
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
        # 2, 6 are QGIS types for integer and real
        the_fields = [f for f in provider.fields() if f.type() in (2, 6)]
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
        process_layers = [ProcessLayer(a, model.processor) for a in model.data_]
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
            unique_field_names = model.processor.get_unique_fields(layer)
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
            unique_field_names = model.processor.get_unique_fields(layer)
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


class HelpDialog(QDialog, Ui_Dialog):

    def __init__(self, parent=None):
        super(HelpDialog, self).__init__(parent)
        self.setupUi(self)
        self.webView.load(
            QUrl("qrc:/plugins/conefor_dev/help.html"),
        )

class LayerAnalyzerThread(QThread):

    def __init__(self, lock, parent=None):
        super(LayerAnalyzerThread, self).__init__(parent)
        self.lock = lock
        self.mutex = QMutex()
        self.stopped = False
        self.completed = False

    def initialize(self, loaded_layers):
        self.loaded_layers = loaded_layers

    def run(self):
        usable_layers = self.analyze_layers()
        self.stop()
        self.emit(SIGNAL('finished'), usable_layers)
        print('depois de emitir o sinal finished')

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True

    def is_stopped(self):
        result = False
        with QMutexLocker(self.mutex):
            if self.stopped:
                result = True
        return result

    def analyze_layers(self):
        usable_layers = dict()
        for layer_id, the_layer in self.loaded_layers.iteritems():
            if the_layer.type() == QgsMapLayer.VectorLayer:
                if the_layer.geometryType() in (QGis.Point, QGis.Polygon):
                    numeric_fields = []
                    for f in the_layer.dataProvider().fields():
                        if f.type() in (QVariant.Int, QVariant.Double):
                            numeric_fields.append(f)
                    unique_fields = numeric_fields[:]
                    all_ = set()
                    numeric_field_to_remove = None
                    for feat in the_layer.getFeatures():
                        if self.is_stopped():
                            return
                        if numeric_field_to_remove is not None:
                            numeric_fields.remove(numeric_field_to_remove)
                            numeric_field_to_remove = None
                        for field in numeric_fields:
                            previous_size = len(all_)
                            tup = (field.name(), feat.attribute(field.name()))
                            all_.add(tup)
                            if previous_size == len(all_): # latest add did not work
                                unique_fields.remove(field)
                                numeric_field_to_remove = field
                    if any(unique_fields):
                        usable_layers[layer_id] = the_layer
        return usable_layers


class ConeforDialog(QDialog,  Ui_ConeforDialog):

    _settings_key = 'PythonPlugins/coneforinputs'

    def __init__(self, plugin_obj, parent=None):
        super(ConeforDialog, self).__init__(parent)
        self.setupUi(self)
        self.processor = plugin_obj.processor
        self.iface = plugin_obj.iface
        self.lock = QReadWriteLock()
        self.analyzer_thread = LayerAnalyzerThread(self.lock, self)
        self.connect(self.analyzer_thread, SIGNAL('finished'),
                     self.finished_analyzing_layers)
        self.analyzer_thread.initialize(plugin_obj.registry.mapLayers())
        self.change_ui_availability(False)
        self.progress_la.setText('Analyzing layers...')
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.analyzer_thread.start()

    def finished_analyzing_layers(self, usable_layers):
        self.analyzer_thread.wait()
        if any(usable_layers):
            self.layers = usable_layers
            current_layer = self.iface.mapCanvas().currentLayer()
            if current_layer not in self.layers.values():
                current_layer = self.layers.values()[0]
            self.change_ui_availability(True)
            if self.exist_selected_features():
                self.use_selected_features_chb.setEnabled(True)
                self.use_selected_features_chb.setChecked(True)
            else:
                self.use_selected_features_chb.setEnabled(False)
            self.model = ProcessLayerTableModel(self.layers, current_layer,
                                                self.processor)
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
            QObject.connect(self.help_btn, SIGNAL('released()'), self.show_help)
            self.connect(self.output_dir_btn, SIGNAL('released()'), self.get_output_dir)
            self.remove_row_btn.setEnabled(False)
            self.toggle_run_button()
            output_dir = self.load_settings('output_dir')
            if str(output_dir) == '':
                output_dir = os.path.expanduser('~')
            self.output_dir_le.setText(output_dir)
            self.create_distances_files_chb.setChecked(True)
            self.reset_progress_bar()
            self.progressBar.setValue(self.processor.global_progress)
            self.update_info('')
        else:
            self.reset_progress_bar()
            self.change_ui_availability(False)
            self.progress_la.setText('No suitable layers found. Please '
                                     'consult the plugin\'s Help page.')
            palette = QPalette()
            palette.setColor(QPalette.Foreground, Qt.red)
            self.progress_la.setPalette(palette)

    def reset_progress_bar(self):
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

    def get_usable_layers(self, map_layer_registry):
        self.progressBar.setMaximum(0)
        '''
        return a dictionary with layerid as key and layer as value.

        This plugin only works with vector layers of types Point and Polygon.
        '''

        usable_layers = dict()
        loaded_layers = map_layer_registry.mapLayers()
        for layer_id, the_layer in loaded_layers.iteritems():
            if the_layer.type() == QgsMapLayer.VectorLayer:
                if the_layer.geometryType() in (QGis.Point, QGis.Polygon):
                    unique_fields = self.processor.get_unique_fields(the_layer)
                    if any(unique_fields):
                        usable_layers[layer_id] = the_layer
        return usable_layers

    def exist_selected_features(self):
        exist_selected = False
        for layer in self.layers.values():
            if layer.selectedFeatureCount() > 1:
                exist_selected = True
        return exist_selected

    def show_help(self):
        dlg = HelpDialog(self)
        dlg.exec_()

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
                attribute_file_name =  None
            else:
                attribute_field_name = la.attribute_field_name
                attribute_file_name = 'nodes_%s_%s' % (attribute_field_name,
                                                       la.qgis_layer.name()) 
            if la.process_area:
                area_file_name = 'nodes_calculated_area_%s' % \
                                 la.qgis_layer.name()
            else:
                area_file_name = None
            if la.process_centroid_distance:
                centroid_file_name = 'distances_centroids_%s' % \
                                     la.qgis_layer.name()
            else:
                centroid_file_name = None
            if la.process_edge_distance:
                edge_file_name = 'distances_edges_%s' % la.qgis_layer.name()
            else:
                edge_file_name = None
            data = {
                'layer' : la.qgis_layer,
                'id_attribute' : la.id_field_name,
                'attribute' : attribute_field_name,
                'attribute_file_name' : attribute_file_name,
                'area_file_name' : area_file_name,
                'centroid_file_name' : centroid_file_name,
                'edge_file_name' : edge_file_name,
                'centroid_distance_name' : None,
                'edge_distance_name' : None,
            }
            if self.create_distances_files_chb.isChecked():
                data['centroid_distance_name'] = 'centroid_distances_%s' % \
                                                 la.qgis_layer.name()
                data['edge_distance_name'] = 'edge_distances_%s' % \
                                             la.qgis_layer.name()
            layers.append(data)
        output_dir = str(self.output_dir_le.text())

        only_selected_features = self.use_selected_features_chb.isChecked()
        self.processor.run_queries(layers, output_dir, only_selected_features)

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

    def change_ui_availability(self, boolean):
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
            widget.setEnabled(boolean)
