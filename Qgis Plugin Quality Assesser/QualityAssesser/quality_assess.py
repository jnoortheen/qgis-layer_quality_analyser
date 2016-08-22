# -*- coding: utf-8 -*-
#!/usr/bin/python

"""
/***************************************************************************
 QualityAssesser
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
#importing the necessary files
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import resources
from quality_assess_dialog import QualityAssesserDialog
from prioritySettings import settingsDlg
from qualityIndicator import qualityIndicatorDlg
import os.path
import psycopg2

class QualityAssesser:
    """QGIS Plugin Implementation."""
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QualityAssesser_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = QualityAssesserDialog()
        self.indicatorDlg = qualityIndicatorDlg()
        self.settingDlg = settingsDlg()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Quality Assesser')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'QualityAssesser')
        self.toolbar.setObjectName(u'QualityAssesser')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QualityAssesser', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the InaSAFE toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/QualityAssesser/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u"Assess the layer's quality"),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Quality Assesser'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        self.dlg.layerComboBox.clear()

        self.getDirectory()
        self.resetInputFields()

        QObject.connect(self.dlg.buttonBox, SIGNAL("accepted()"), self.validate)
        QObject.connect(self.dlg.buttonBox.button(QDialogButtonBox.Reset), SIGNAL("clicked()"), self.resetInputFields)
        QObject.connect(self.dlg.buttonBox, SIGNAL("rejected()"), self.dlg.close)

        QObject.connect(self.settingDlg.buttonBox, SIGNAL("accepted()"), self.getPrioritySettings)
        QObject.connect(self.settingDlg.buttonBox, SIGNAL("rejected()"), self.settingDlg.close)

        QObject.connect(self.indicatorDlg.buttonBox, SIGNAL("rejected()"), self.indicatorDlg.close)

    def getDirectory(self):
        noOfLayers = self.iface.mapCanvas().layerCount()  #finding out the number of layers already opened in the mapcanvas

        if noOfLayers==0:
            QMessageBox.warning(self.dlg, "Add a layer","Add a layer and restart the plugin. \nThe plugin can function if atleast one layer is active.")
            self.dlg.close()
        else:
            listOfLayers = self.iface.mapCanvas().layers()
            #adding the list of layers to the combobox
            for layer in reversed(listOfLayers):
                self.dlg.layerComboBox.addItem(layer.name())

        #if the layer is changed then the other fields are going to be reset to blank
        QObject.connect(self.dlg.layerComboBox, SIGNAL("currentIndexChanged(int)"), self.resetInputFields)

    def validate(self):
        """Validating the user input"""
        #storing the input as variable
        usrPosAcc = self.dlg.posAccuracy.text()  # user's expected position accuracy
        usrDomain = self.dlg.domainConsist.text()
        usrMissingFeat = self.dlg.missingFeatNo.text()
        usrUndershoot = self.dlg.undershootNo.text()
        usrOvershoot = self.dlg.overshootNo.text()
        usrTemporal = self.dlg.temporalNo.text()
        usrCorrectness = self.dlg.correctNo.text()
        usrQuantitative = self.dlg.quantNo.text()
        usrNonQuantitative = self.dlg.nonQuantNo.text()

        self.count = 0

        #validating each input as it is positive and not None
        self.checkIfNone(usrPosAcc)  # user's expected position accuracy
        self.checkIfNone(usrDomain)
        self.checkIfNone(usrMissingFeat)
        self.checkIfNone(usrUndershoot)
        self.checkIfNone(usrOvershoot)
        self.checkIfNone(usrTemporal)
        self.checkIfNone(usrCorrectness)
        self.checkIfNone(usrQuantitative)
        self.checkIfNone(usrNonQuantitative)

        if self.count == 9:
            self.usrPosAcc = round(float(usrPosAcc), 4) #converting the string to a float number with 4 decimal values
            self.usrDomain = int(usrDomain)
            self.usrMissingFeatNo = int(usrMissingFeat)
            self.usrUndershoot = int(usrUndershoot)
            self.usrOvershoot = int(usrOvershoot)
            self.usrTemporal = int(usrTemporal)
            self.usrCorrectness = int(usrCorrectness)
            self.usrQuantitative = int(usrQuantitative)
            self.usrNonQuantitative = int(usrNonQuantitative)
            #opening the next window if all of the conditions are satisfied
            self.connectToDb()
        else:
            self.showMissingInfoMsg()

    def nextWindow(self):
        self.dlg.close()
        self.settingDlg.show()

    def getPrioritySettings(self):
        self.logicalGood = self.settingDlg.logicalGoodSpin.value()
        self.logicalTolerable = self.settingDlg.logicalTolerableSpin.value()
        self.logicalBad = self.settingDlg.logicalBadSpin.value()
        self.thematicGood = self.settingDlg.thematicGoodSpin.value()
        self.thematicTolerable = self.settingDlg.thematicTolerableSpin.value()
        self.thematicBad = self.settingDlg.thematicBadSpin.value()

        self.indicatorDlg.show()
        self.settingDlg.close()
        self.descriptionDashboard()
        self.posAccDashboard()
        self.temporalDashboard()
        self.thematicDashboard()
        self.logicalDashboard()
        self.completenessDashboard()

    def resetInputFields(self):
        self.dlg.posAccuracy.clear()
        self.dlg.domainConsist.clear()
        self.dlg.missingFeatNo.clear()
        self.dlg.undershootNo.clear()
        self.dlg.overshootNo.clear()
        self.dlg.temporalNo.clear()
        self.dlg.correctNo.clear()
        self.dlg.quantNo.clear()
        self.dlg.nonQuantNo.clear()

    def showMissingInfoMsg(self):
        QMessageBox.warning(self.dlg, "Missing information", "Fill the missing informations and try again.")

    def showIncorrectEntry(self):
        QMessageBox.warning(self.dlg, "Incorrect Entry", "The value for one or more fields entered wrongly.\n See the help file for more details.")
        self.resetInputFields()

    def showNotConnectingToDb(self):
        QMessageBox.warning(self.dlg, "Not able to connect", "The plugin can't connect to the database.")

    def showNoMetadata(self):
        QMessageBox.warning(self.dlg, "No Meta-data available", "There is no metadata for the selected layer.")

    def showNoOtherDataAvailable(self):
        QMessageBox.warning(self.dlg, "No other details exists", "There is no metadata for the selected layer.")

    def checkIfNone(self, check):
        if check == "":
            self.showMissingInfoMsg()
        elif int(check) < 0:
            self.showIncorrectEntry()
        elif int(check) >= 0:
            self.count+=1
        else:
            self.showIncorrectEntry()

    def connectToDb(self):
        try:
            conn = psycopg2.connect("dbname='testPlugin' user='postgres' host='localhost' password='njnoortheen' port='5432'")
        except:
            self.showNotConnectingToDb()
            self.dlg.close()
        self.cur = conn.cursor()
        self.getDataFromDb()

    def getDataFromDb(self):
        self.lyrName = self.dlg.layerComboBox.currentText()  # selected layers name
        self.checkLayerExistInDb()
        if self.count2 == 5:
            self.storeValueFromDb()
            self.nextWindow()

    def checkLayerExistInDb(self):
        self.count2 = 0
        sq = "SELECT layername FROM md_londonroad  WHERE layername = '" + str(self.lyrName) +"'"
        self.cur.execute(str(sq))
        check = ""

        try:
            check = self.cur.fetchone()[0]
        except:
            self.showNoMetadata()
            self.dlg.close()

        if check == self.lyrName:
            self.checkLayerDataExistInDb()

    def checkLayerDataExistInDb(self):
        for i in ["dq_lineage", "dq_logicalconsistency", "dq_posaccandcompleteness", "dq_temporalaccuracy", "dq_thematicaccuracy"]:
            self.checkExistence(i)

    def checkExistence(self, tablNameStr):
        sq = "SELECT layername FROM " + str(tablNameStr) + " WHERE layername = '" + str(self.lyrName) +"'"
        self.cur.execute(str(sq))
        check = self.cur.fetchone()[0]

        if check == self.lyrName:
            self.count2 += 1
        else:
            self.showNoMetadata()
            self.dlg.close()

    def storeValueFromDb(self):
        #storing for md_londonroad
        leftMdLondonRd = (
            'layername', 'projectsystem', 'eastboundlong', 'westboundlong',
            'northboundlat', 'southboundlat', 'extentdesc', 'mapunit', 'producername',
            'address', 'emailorwebsite')
        self.md_londonroadDict = {}
        self.cur.execute("SELECT * FROM md_londonroad WHERE layername='"+str(self.lyrName)+"'")
        rightMdLondonRd = self.cur.fetchall()[0]

        for i in range(len(leftMdLondonRd)):
            self.md_londonroadDict[leftMdLondonRd[i]] = rightMdLondonRd[i+1]

        #storing for dq_lineage
        leftDqLineage = (
            'layername', 'dateacquired', 'datepublished', 'updationfrequency',
            'lastupdate')
        self.dq_lineageDict = {}
        self.cur.execute("SELECT * FROM dq_lineage WHERE layername='"+str(self.lyrName)+"'")
        rightDqLineage = self.cur.fetchall()[0]

        for i in range(len(leftDqLineage)):
            self.dq_lineageDict[leftDqLineage[i]] = rightDqLineage[i+1]

        #storing for dq_logicalconsistency
        leftDqLogical = (
            'layername', 'domainconsistency', 'domainconsistdec', 'faultyconnection',
            'faultyconnectiondesc', 'errorduetoovershoot', 'overshootdesc', 'errorduetoundershoot',
            'undershootdesc')
        self.dq_logicalDict = {}
        self.cur.execute("SELECT * FROM dq_logicalconsistency WHERE layername='"+str(self.lyrName)+"'")
        rightDqLogical = self.cur.fetchall()[0]

        for i in range(len(leftDqLogical)):
            self.dq_logicalDict[leftDqLogical[i]] =rightDqLogical[i+1]

        #storing for dq_posaccandcompleteness
        leftPosComp = (
            'layername', 'posaccuracy', 'posaccuracydesc', 'commissionerror',
            'commissionerrordesc', 'ommissionerror', 'ommissionerrordesc')
        self.PosCompDict = {}
        self.cur.execute("SELECT * FROM dq_posaccandcompleteness WHERE layername='"+str(self.lyrName)+"'")
        rightPosComp = self.cur.fetchall()[0]

        for i in range(len(leftPosComp)):
            self.PosCompDict[leftPosComp[i]] =rightPosComp[i+1]

        #storing for dq_temporalaccuracy
        leftTemporal=        (
            'layername', 'temporalvalidityerror', 'temporalvaliditydesc')
        self.TemporalDict = {}
        self.cur.execute("SELECT * FROM dq_temporalaccuracy WHERE layername='"+str(self.lyrName)+"'")
        rightTemporal = self.cur.fetchall()[0]

        for i in range(len(leftTemporal)):
            self.TemporalDict[leftTemporal[i]] =rightTemporal[i+1]

        #storing for dq_thematicaccuracy
        leftThematic= (
            'layername', 'classcorrectnesserror', 'classcorrectnessdesc',
            'quantattributeerror', 'quantattributedesc', 'nonquantattributeerror',
            'nonquantattributedesc')
        self.ThematicDict = {}
        self.cur.execute("SELECT * FROM dq_thematicaccuracy WHERE layername='"+str(self.lyrName)+"'")
        rightThematic = self.cur.fetchall()[0]

        for i in range(len(leftThematic)):
            self.ThematicDict[leftThematic[i]] =rightThematic[i+1]

    def posAccDashboard(self):
        self.indicatorDlg.layerNameLabel_2.setText(str(self.lyrName))
        self.indicatorDlg.posAccuracyLabel.setText(str(self.PosCompDict['posaccuracy']))

        if len(self.PosCompDict['posaccuracydesc']) != 0:
            self.indicatorDlg.posDetilsLabel.setText(str(self.PosCompDict['posaccuracydesc']))
        else:
            self.indicatorDlg.posDetilsLabel.setText("No details available.")

        if self.usrPosAcc >= self.PosCompDict['posaccuracy']:
            self.indicatorDlg.posResultPic.setPixmap(QPixmap(':/plugins/QualityAssesser/good.jpg'))
            self.indicatorDlg.posResultlabel.setText("Good")
        else:
            self.indicatorDlg.posResultPic.setPixmap(QPixmap(':/plugins/QualityAssesser/bad.jpg'))
            self.indicatorDlg.posResultlabel.setText("Bad")

    def descriptionDashboard(self):
        self.indicatorDlg.layerNameLabel.setText(str(self.lyrName))
        self.indicatorDlg.northBound.setText(str(self.md_londonroadDict['northboundlat']))
        self.indicatorDlg.southBound.setText(str(self.md_londonroadDict['southboundlat']))
        self.indicatorDlg.eastBound.setText(str(self.md_londonroadDict['eastboundlong']))
        self.indicatorDlg.westBound.setText(str(self.md_londonroadDict['westboundlong']))
        self.indicatorDlg.projSystemTxtEdit.setText(str(self.md_londonroadDict['projectsystem']))
        self.indicatorDlg.unitDashBoard.setText(str(self.md_londonroadDict['mapunit']))
        self.indicatorDlg.datepublishedDB.setText(str(self.dq_lineageDict['datepublished']))
        self.indicatorDlg.dateacquired.setText(str(self.dq_lineageDict['dateacquired']))
        self.indicatorDlg.updationfrequency.setText(str(self.dq_lineageDict['updationfrequency']))
        self.indicatorDlg.lastupdate.setText(str(self.dq_lineageDict['lastupdate']))
        self.indicatorDlg.organisation.setText(str(self.md_londonroadDict['producername']))
        self.indicatorDlg.address.setText(str(self.md_londonroadDict['address']))
        self.indicatorDlg.contact.setText(str(self.md_londonroadDict['emailorwebsite']))

    def thematicDashboard(self):
        checkedConditions = 0
        self.indicatorDlg.layerNameLabel_3.setText(str(self.lyrName))

        self.indicatorDlg.classCorrectnessLabel.setText(str(self.ThematicDict['classcorrectnesserror']))
        self.indicatorDlg.classCorrLabelDetails.setText(str(self.ThematicDict['classcorrectnessdesc']))

        self.indicatorDlg.quantAttribLbl.setText(str(self.ThematicDict['quantattributeerror']))
        self.indicatorDlg.quantErrDetails.setText(str(self.ThematicDict['quantattributedesc']))

        self.indicatorDlg.quantAttribLbl_2.setText(str(self.ThematicDict['nonquantattributeerror']))
        self.indicatorDlg.quantErrDetails_2.setText(str(self.ThematicDict['nonquantattributedesc']))

        if int(self.usrCorrectness) >= int(self.ThematicDict['classcorrectnesserror']):
            checkedConditions += 1

        if int(self.usrQuantitative) >= int(self.ThematicDict['quantattributeerror']):
            checkedConditions += 1

        if int(self.usrNonQuantitative) >= int(self.ThematicDict['nonquantattributeerror']):
            checkedConditions += 1

        if checkedConditions == int(self.thematicGood):
            self.indicatorDlg.posResultPic_2.setPixmap(QPixmap(':/plugins/QualityAssesser/good.jpg'))
            self.indicatorDlg.posResultlabel_2.setText("Good")
        elif checkedConditions == int(self.thematicTolerable):
            self.indicatorDlg.posResultPic_2.setPixmap(QPixmap(':/plugins/QualityAssesser/tolerable.jpg'))
            self.indicatorDlg.posResultlabel_2.setText("Tolerable")
        else:
            self.indicatorDlg.posResultPic_2.setPixmap(QPixmap(':/plugins/QualityAssesser/bad.jpg'))
            self.indicatorDlg.posResultlabel_2.setText("Bad")

    def temporalDashboard(self):
        self.indicatorDlg.layerNameLabel_4.setText(str(self.lyrName))
        self.indicatorDlg.posAccuracyLabel_2.setText(str(self.TemporalDict['temporalvalidityerror']))

        if len(self.TemporalDict['temporalvaliditydesc']) != 0:
            self.indicatorDlg.posDetilsLabel_2.setText(str(self.TemporalDict['temporalvaliditydesc']))
        else:
            self.indicatorDlg.posDetilsLabel.setText("No details available.")

        if self.usrTemporal >= self.TemporalDict['temporalvalidityerror']:
            self.indicatorDlg.posResultPic_3.setPixmap(QPixmap(':/plugins/QualityAssesser/good.jpg'))
            self.indicatorDlg.label_18.setText("Good")
        else:
            self.indicatorDlg.posResultPic_3.setPixmap(QPixmap(':/plugins/QualityAssesser/bad.jpg'))
            self.indicatorDlg.label_18.setText("Bad")

    def logicalDashboard(self):
        checkedConditions = 0
        self.indicatorDlg.layerNameLabel_5.setText(str(self.lyrName))

        self.indicatorDlg.domainconsistency.setText(str(self.dq_logicalDict['domainconsistency']))
        self.indicatorDlg.domainconsistdec.setText(str(self.dq_logicalDict['domainconsistdec']))

        self.indicatorDlg.faultyconnection.setText(str(self.dq_logicalDict['faultyconnection']))
        self.indicatorDlg.faultyconnectiondesc.setText(str(self.dq_logicalDict['faultyconnectiondesc']))

        self.indicatorDlg.errorduetoovershoot.setText(str(self.dq_logicalDict['errorduetoovershoot']))
        self.indicatorDlg.overshootdesc.setText(str(self.dq_logicalDict['overshootdesc']))

        self.indicatorDlg.errorduetoundershoot.setText(str(self.dq_logicalDict['errorduetoundershoot']))
        self.indicatorDlg.undershootdesc.setText(str(self.dq_logicalDict['undershootdesc']))

        if int(self.usrDomain) >= int(self.dq_logicalDict['domainconsistency']):
            checkedConditions += 1

        if int(self.usrOvershoot) >= int(self.dq_logicalDict['errorduetoovershoot']):
            checkedConditions += 1

        if int(self.usrUndershoot) >= int(self.dq_logicalDict['errorduetoundershoot']):
            checkedConditions += 1

        if int(self.usrMissingFeatNo) >= int(self.dq_logicalDict['faultyconnection']):
            checkedConditions += 1

        if checkedConditions == int(self.logicalGood):
            self.indicatorDlg.posResultPic_4.setPixmap(QPixmap(':/plugins/QualityAssesser/good.jpg'))
            self.indicatorDlg.label_28.setText("Good")
        elif checkedConditions == int(self.logicalTolerable):
            self.indicatorDlg.posResultPic_4.setPixmap(QPixmap(':/plugins/QualityAssesser/tolerable.jpg'))
            self.indicatorDlg.label_28.setText("Tolerable")
        else:
            self.indicatorDlg.posResultPic_4.setPixmap(QPixmap(':/plugins/QualityAssesser/bad.jpg'))
            self.indicatorDlg.label_28.setText("Bad")

    def completenessDashboard(self):
        self.indicatorDlg.layerNameLabel_6.setText(str(self.lyrName))

        self.indicatorDlg.commissionerror.setText(str(self.PosCompDict['commissionerror']))
        self.indicatorDlg.commissionerrordesc.setText(str(self.PosCompDict['commissionerrordesc']))

        self.indicatorDlg.ommissionerror.setText(str(self.PosCompDict['ommissionerror']))
        self.indicatorDlg.ommissionerrordesc.setText(str(self.PosCompDict['ommissionerrordesc']))