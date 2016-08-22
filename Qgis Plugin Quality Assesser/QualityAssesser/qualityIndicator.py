# -*- coding: utf-8 -*-
import os
from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qualityIndicator.ui'))

class qualityIndicatorDlg(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        #constructor
        super(qualityIndicatorDlg, self).__init__(parent)
        self.setupUi(self)