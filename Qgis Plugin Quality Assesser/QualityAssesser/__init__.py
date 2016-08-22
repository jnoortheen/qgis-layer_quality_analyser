# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QualityAssesser
                                 A QGIS plugin
 This plugin assess the logical, thematic and temporal accuracy of the layers.
                             -------------------
        begin                : 2014-11-01
        copyright            : (C) 2014 by Project Ms
        email                : jnoortheen@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):
    from quality_assess import QualityAssesser
    return QualityAssesser(iface)
