# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QualityAssesserDialog
                                 A QGIS plugin
 This plugin assess the logical, thematic and temporal accuracy of the layers.
                             -------------------
        begin                : 2014-11-01
        git sha              : $Format:%H$
        copyright            : (C) 2014 by Project Ms
        email                : jnoortheen@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'quality_assess_dialog_base.ui'))


class QualityAssesserDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(QualityAssesserDialog, self).__init__(parent)
        self.setupUi(self)
