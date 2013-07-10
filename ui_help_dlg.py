# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'help_dlg.ui'
#
# Created: Wed Jul 10 23:42:51 2013
#      by: PyQt4 UI code generator 4.9.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(564, 524)
        self.webView = QtWebKit.QWebView(Dialog)
        self.webView.setGeometry(QtCore.QRect(9, 9, 546, 506))
        self.webView.setUrl(QtCore.QUrl(_fromUtf8("qrc:/plugins/conefor_dev/help.html")))
        self.webView.setObjectName(_fromUtf8("webView"))

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Dialog", None, QtGui.QApplication.UnicodeUTF8))

from PyQt4 import QtWebKit
import resources_rc
