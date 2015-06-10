# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'conefor_dlg.ui'
#
# Created: Wed Jun 10 14:50:54 2015
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_ConeforDialog(object):
    def setupUi(self, ConeforDialog):
        ConeforDialog.setObjectName(_fromUtf8("ConeforDialog"))
        ConeforDialog.resize(640, 598)
        self.verticalLayout = QtGui.QVBoxLayout(ConeforDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_7 = QtGui.QHBoxLayout()
        self.horizontalLayout_7.setObjectName(_fromUtf8("horizontalLayout_7"))
        self.lock_layers_chb = QtGui.QCheckBox(ConeforDialog)
        self.lock_layers_chb.setObjectName(_fromUtf8("lock_layers_chb"))
        self.horizontalLayout_7.addWidget(self.lock_layers_chb)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.layers_la = QtGui.QLabel(ConeforDialog)
        self.layers_la.setObjectName(_fromUtf8("layers_la"))
        self.horizontalLayout_3.addWidget(self.layers_la)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.tableView = QtGui.QTableView(ConeforDialog)
        self.tableView.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)
        self.tableView.setAlternatingRowColors(True)
        self.tableView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tableView.setTextElideMode(QtCore.Qt.ElideRight)
        self.tableView.setObjectName(_fromUtf8("tableView"))
        self.tableView.horizontalHeader().setDefaultSectionSize(102)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.verticalHeader().setVisible(False)
        self.verticalLayout.addWidget(self.tableView)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        spacerItem2 = QtGui.QSpacerItem(268, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem2)
        self.remove_row_btn = QtGui.QPushButton(ConeforDialog)
        self.remove_row_btn.setObjectName(_fromUtf8("remove_row_btn"))
        self.horizontalLayout_4.addWidget(self.remove_row_btn)
        self.add_row_btn = QtGui.QPushButton(ConeforDialog)
        self.add_row_btn.setObjectName(_fromUtf8("add_row_btn"))
        self.horizontalLayout_4.addWidget(self.add_row_btn)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_6 = QtGui.QHBoxLayout()
        self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        self.use_selected_features_chb = QtGui.QCheckBox(ConeforDialog)
        self.use_selected_features_chb.setObjectName(_fromUtf8("use_selected_features_chb"))
        self.horizontalLayout_6.addWidget(self.use_selected_features_chb)
        spacerItem3 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem3)
        self.verticalLayout.addLayout(self.horizontalLayout_6)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.create_distances_files_chb = QtGui.QCheckBox(ConeforDialog)
        self.create_distances_files_chb.setObjectName(_fromUtf8("create_distances_files_chb"))
        self.horizontalLayout.addWidget(self.create_distances_files_chb)
        spacerItem4 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.output_la = QtGui.QLabel(ConeforDialog)
        self.output_la.setObjectName(_fromUtf8("output_la"))
        self.verticalLayout.addWidget(self.output_la)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.output_dir_le = QtGui.QLineEdit(ConeforDialog)
        self.output_dir_le.setObjectName(_fromUtf8("output_dir_le"))
        self.horizontalLayout_2.addWidget(self.output_dir_le)
        self.output_dir_btn = QtGui.QPushButton(ConeforDialog)
        self.output_dir_btn.setObjectName(_fromUtf8("output_dir_btn"))
        self.horizontalLayout_2.addWidget(self.output_dir_btn)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.line = QtGui.QFrame(ConeforDialog)
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.verticalLayout.addWidget(self.line)
        self.progress_la = QtGui.QLabel(ConeforDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progress_la.sizePolicy().hasHeightForWidth())
        self.progress_la.setSizePolicy(sizePolicy)
        self.progress_la.setObjectName(_fromUtf8("progress_la"))
        self.verticalLayout.addWidget(self.progress_la)
        self.progressBar = QtGui.QProgressBar(ConeforDialog)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.verticalLayout.addWidget(self.progressBar)
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        self.help_btn = QtGui.QPushButton(ConeforDialog)
        self.help_btn.setObjectName(_fromUtf8("help_btn"))
        self.horizontalLayout_5.addWidget(self.help_btn)
        spacerItem5 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem5)
        self.run_btn = QtGui.QPushButton(ConeforDialog)
        self.run_btn.setObjectName(_fromUtf8("run_btn"))
        self.horizontalLayout_5.addWidget(self.run_btn)
        self.verticalLayout.addLayout(self.horizontalLayout_5)
        self.output_la.setBuddy(self.output_dir_le)

        self.retranslateUi(ConeforDialog)
        QtCore.QMetaObject.connectSlotsByName(ConeforDialog)
        ConeforDialog.setTabOrder(self.add_row_btn, self.remove_row_btn)
        ConeforDialog.setTabOrder(self.remove_row_btn, self.create_distances_files_chb)
        ConeforDialog.setTabOrder(self.create_distances_files_chb, self.output_dir_btn)
        ConeforDialog.setTabOrder(self.output_dir_btn, self.output_dir_le)
        ConeforDialog.setTabOrder(self.output_dir_le, self.run_btn)
        ConeforDialog.setTabOrder(self.run_btn, self.help_btn)

    def retranslateUi(self, ConeforDialog):
        ConeforDialog.setWindowTitle(_translate("ConeforDialog", "Conefor Inputs", None))
        self.lock_layers_chb.setText(_translate("ConeforDialog", "Lock field names to first layer", None))
        self.layers_la.setText(_translate("ConeforDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Select layers and queries to perform</span></p></body></html>", None))
        self.remove_row_btn.setText(_translate("ConeforDialog", "Remove row", None))
        self.add_row_btn.setText(_translate("ConeforDialog", "Add row", None))
        self.use_selected_features_chb.setText(_translate("ConeforDialog", "Only use selected features", None))
        self.create_distances_files_chb.setText(_translate("ConeforDialog", "Create link vector layer (Slower and works only with valid geometries)", None))
        self.output_la.setText(_translate("ConeforDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Output directory</span></p></body></html>", None))
        self.output_dir_btn.setText(_translate("ConeforDialog", "Browse...", None))
        self.progress_la.setText(_translate("ConeforDialog", "Label", None))
        self.help_btn.setText(_translate("ConeforDialog", "Help", None))
        self.run_btn.setText(_translate("ConeforDialog", "Run", None))

import resources_rc
