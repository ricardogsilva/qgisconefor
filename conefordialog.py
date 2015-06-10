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

class ConeforDialog(QDialog,  Ui_ConeforDialog):

    _settings_key = 'PythonPlugins/qgisconefor'

    def __init__(self, plugin_obj, parent=None):
        super(ConeforDialog, self).__init__(parent)
        self.setupUi(self)
        self.processor = plugin_obj.processor
        self.iface = plugin_obj.iface
        self.lock = QReadWriteLock()
        self.analyzer_thread = LayerAnalyzerThread(self.lock, self)
        self.processing_thread = LayerProcessingThread(self.lock,
                                                       self.processor, self)
        self.connect(self.help_btn, SIGNAL('released()'), self.show_help)
        self.connect(self.analyzer_thread, SIGNAL('finished'),
                     self.finished_analyzing_layers)
        self.connect(self.analyzer_thread, SIGNAL('analyzing_layer'),
                     self.analyzing_layer)
        self.connect(self.processing_thread, SIGNAL('finished'),
                     self.finished_processing_layers)
        self.analyzer_thread.initialize(plugin_obj.registry.mapLayers())
        self.change_ui_availability(False)
        self.progress_la.setText('Analyzing layers...')
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.analyzer_thread.start()

    def analyzing_layer(self, layer_name):
        utilities.log("analyzing layer: {}".format(layer_name))
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
            current_layers = self.iface.legendInterface().selectedLayers()
            valid = [la for la in current_layers if la in usable_layers.keys()]
            if not any(valid):
                valid.append(self.layers.keys()[0])
            selected = utilities.exist_selected_features(self.layers.keys())
            self.change_ui_availability(True, selected)
            if utilities.exist_selected_features(self.layers.keys()):
                self.use_selected_features_chb.setEnabled(True)
                self.use_selected_features_chb.setChecked(True)
            else:
                self.use_selected_features_chb.setEnabled(False)
            self.model = ProcessLayerTableModel(self.layers, valid,
                                                self.processor, self)
            self.tableView.setModel(self.model)
            delegate = ProcessLayerDelegate(self, self)
            self.tableView.setItemDelegate(delegate)
            self.add_row_btn.released.connect(self.add_row)
            self.remove_row_btn.released.connect(self.remove_row)
            self.run_btn.released.connect(self.run_queries)
            self.output_dir_btn.released.connect(self.get_output_dir)
            self.lock_layers_chb.toggled.connect(self.toggle_lock_layers)
            self.processor.progress_changed.connect(self.update_progress)
            self.processor.update_info.connect(self.update_info)
            self.model.is_runnable_check.connect(self.toggle_run_button)
            if len(current_layers) < 2:
                self.remove_row_btn.setEnabled(False)
            self.toggle_run_button()
            output_dir = self.load_settings('output_dir',
                                            default_to=os.path.expanduser('~'))
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

    def toggle_lock_layers(self, lock):
        index = self.model.index(0, 0)
        self.tableView.setFocus()

    def reset_progress_bar(self):
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

    def show_help(self):
        plugin_dir = os.path.dirname(__file__)
        url = "file:///{}/assets/help.html".format(plugin_dir)
        self.iface.openURL(url, False)

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
        last_row = self.model.rowCount() - 1
        self.model.removeRows(last_row)
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

    def load_settings(self, key, type_hint=str, default_to=None):
        settings = QSettings()
        full_key = '%s/%s' % (self._settings_key, key)
        try:
            value = settings.value(full_key, type=type_hint)
        except TypeError:
            value = default_to
        return value

    def run_queries(self):
        self.update_progress()
        layers = []
        load_to_canvas = self.create_distances_files_chb.isChecked()
        output_dir = str(self.output_dir_le.text())
        only_selected_features = self.use_selected_features_chb.isChecked()
        for layer_number, la in enumerate(self.model.layers):
            id_ = la.id_field_name
            attribute = la.attribute_field_name
            area = la.process_area
            centroid = la.process_centroid_distance
            edge = la.process_edge_distance
            if self.lock_layers_chb.isChecked() and layer_number > 0:
                id_ = self.model.layers[0].id_field_name
                attribute = self.model.layers[0].attribute_field_name
                area = self.model.layers[0].process_area
                centroid = self.model.layers[0].process_centroid_distance
                edge = self.model.layers[0].process_edge_distance
            if id_ == '<None>':
                raise NoUniqueFieldError
            if str(attribute) == '<None>':
                attribute = None
                attribute_file_name =  None
            else:
                attribute_file_name = 'nodes_%s_%s' % (attribute,
                                                        la.qgis_layer.name()) 
            if area:
                area_file_name = 'nodes_calculated_area_%s' % \
                                    la.qgis_layer.name()
            else:
                area_file_name = None
            if centroid:
                centroid_file_name = 'distances_centroids_%s' % \
                                        la.qgis_layer.name()
            else:
                centroid_file_name = None
            if edge:
                edge_file_name = 'distances_edges_%s' % la.qgis_layer.name()
            else:
                edge_file_name = None
            data = {
                'layer' : la.qgis_layer,
                'id_attribute' : id_,
                'attribute' : attribute,
                'attribute_file_name' : attribute_file_name,
                'area_file_name' : area_file_name,
                'centroid_file_name' : centroid_file_name,
                'edge_file_name' : edge_file_name,
                'centroid_distance_name' : None,
                'edge_distance_name' : None,
            }
            if load_to_canvas:
                if centroid:
                    data['centroid_distance_name'] = 'Centroid_links_%s' %\
                                                        la.qgis_layer.name()
                if edge:
                    data['edge_distance_name'] = 'Edge_links_%s' % \
                                                    la.qgis_layer.name()
            layers.append(data)
        self.change_ui_availability(False)
        self.processing_thread.initialize(layers, output_dir,
                                          only_selected_features)
        self.processing_thread.start()

    def update_progress(self):
        self.progressBar.setValue(self.processor.global_progress)

    def update_info(self, info, section=0):
        '''
        Update the progress label with the input info string.

        The information displayed in the progress label is a string composed
        of three sections:

        * section 0
        * section 1
        * section 2

        Inputs:

            info - a string with the information to display in the progress
                   label
            section - an integer specifying where in the displayed string
                      should the 'info' argument be placed.
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
        if 'ERROR' in info:
            palette = QPalette()
            palette.setColor(QPalette.Foreground, Qt.red)
            self.progress_la.setPalette(palette)

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
