#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *
from qgis.utils import showPluginHelp

from ui_conefor_dlg import Ui_ConeforDialog
from ui_help_dlg import Ui_Dialog

import utilities
from coneforthreads import LayerAnalyzerThread, LayerProcessingThread
from processlayer import ProcessLayerTableModel, ProcessLayerDelegate

class NoUniqueFieldError(Exception):
    pass


class HelpDialog(QDialog, Ui_Dialog):

    def __init__(self, parent=None):
        super(HelpDialog, self).__init__(parent)
        self.setupUi(self)
        self.webView.load(
            QUrl("qrc:/plugins/conefor_dev/help.html"),
        )


class ConeforDialog(QDialog,  Ui_ConeforDialog):

    _settings_key = 'PythonPlugins/coneforinputs'

    def __init__(self, plugin_obj, parent=None):
        super(ConeforDialog, self).__init__(parent)
        self.setupUi(self)
        self.processor = plugin_obj.processor
        self.iface = plugin_obj.iface
        self.lock = QReadWriteLock()
        self.analyzer_thread = LayerAnalyzerThread(self.lock, self)
        self.processing_thread = LayerProcessingThread(self.lock,
                                                       self.processor, self)
        self.connect(self.analyzer_thread, SIGNAL('finished'),
                     self.finished_analyzing_layers)
        self.connect(self.analyzer_thread, SIGNAL('analyzing_layer'),
                     self.analyzing_layer)
        self.connect(self.processing_thread, SIGNAL('finished'),
                     self.finished_processing_layers)
        self.analyzer_thread.initialize(plugin_obj.registry.mapLayers(),
                                        self.unique_features_chb.isChecked())
        self.change_ui_availability(False)
        self.progress_la.setText('Analyzing layers...')
        find_unique_features = self.load_settings('analyze_unique_features',
                                                  type_hint=bool)
        if find_unique_features is None:
            find_unique_features = False
        if not isinstance(find_unique_features, bool):
            find_unique_features = False
        self.unique_features_chb.setChecked(find_unique_features)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.analyzer_thread.start()

    def analyzing_layer(self, layer_name):
        self.progress_la.setText('Analyzing layers: %s...' % layer_name)

    def finished_processing_layers(self, layers, new_files=[]):
        self.processing_thread.wait()
        exist_selected = utilities.exist_selected_features(layers)
        self.change_ui_availability(True, exist_selected)
        registry = QgsMapLayerRegistry.instance()
        if self.create_distances_files_chb.isChecked():
            for new_layer_path in new_files:
                if new_layer_path.endswith('.shp'):
                    layer_name = os.path.basename(new_layer_path)
                    new_layer = QgsVectorLayer(new_layer_path, layer_name,
                                               'ogr')
                    registry.addMapLayer(new_layer)

    def finished_analyzing_layers(self, usable_layers):
        self.analyzer_thread.wait()
        if any(usable_layers):
            self.layers = usable_layers
            #current_layer = self.iface.mapCanvas().currentLayer()
            #if current_layer not in self.layers.keys():
            #    current_layer = self.layers.keys()[0]

            # aqui
            current_layers = self.iface.legendInterface().selectedLayers()
            if not any(current_layers):
                current_layers.append(self.layers.keys()[0])


            selected = utilities.exist_selected_features(self.layers.keys())
            self.change_ui_availability(True, selected)
            if utilities.exist_selected_features(self.layers.keys()):
                self.use_selected_features_chb.setEnabled(True)
                self.use_selected_features_chb.setChecked(True)
            else:
                self.use_selected_features_chb.setEnabled(False)
            self.model = ProcessLayerTableModel(self.layers, current_layers,
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
            self.create_distances_files_chb.setChecked(False)
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

    def load_settings(self, key, type_hint=str):
        settings = QSettings()
        full_key = '%s/%s' % (self._settings_key, key)
        value = settings.value(full_key, type=type_hint)
        return value

    def run_queries(self):
        self.update_progress()
        layers = []
        load_to_canvas = self.create_distances_files_chb.isChecked()
        output_dir = str(self.output_dir_le.text())
        only_selected_features = self.use_selected_features_chb.isChecked()
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
            if load_to_canvas:
                if la.process_centroid_distance:
                    data['centroid_distance_name'] = 'Centroid_links_%s' %\
                                                        la.qgis_layer.name()
                if la.process_edge_distance:
                    data['edge_distance_name'] = 'Edge_links_%s' % \
                                                    la.qgis_layer.name()
            layers.append(data)

        self.change_ui_availability(False)
        self.processing_thread.initialize(layers, output_dir,
                                            load_to_canvas,
                                            only_selected_features)
        self.processing_thread.start()

    def update_progress(self):
        self.progressBar.setValue(self.processor.global_progress)

    def closeEvent(self, event=None):
        self.save_settings('%s/analyze_unique_features' % self._settings_key,
                           self.unique_features_chb.isChecked())

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

    def change_ui_availability(self, boolean, selected_features=False):
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
        if boolean:
            self.use_selected_features_chb.setEnabled(selected_features)
