# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PopulateAuthSystem
                                 A QGIS plugin
 Plugin to populate the authentication database
                              -------------------
        begin                : 2014-10-31
        git sha              : $Format:%H$
        copyright            : (C) 2014-15 by
                               Larry Shaffer/Boundless Spatial Inc.
        email                : lshaffer@boundlessgeo.com
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
import shutil

from qgis.core import QgsAuthManager
from qgis.gui import QgisInterface
from PyQt4.QtCore import QSettings, qVersion, QCoreApplication
from PyQt4.QtGui import QMainWindow, QAction, QIcon
# Initialize Qt resources from resources_rc.py (compiled from resources.qrc)
import resources_rc
# Import the code for the dialog
from populate_auth_system_dialog import PopulateAuthSystemDialog


class PopulateAuthSystem:
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
        """:type : QgsInterface"""
        self.mw = iface.mainWindow()
        """:type : QMainWindow"""

        try:
            from tests import testerplugin
            from qgistester.tests import addTestModule
            addTestModule(testerplugin, 'PopulateAuthSystem')
        except:
            pass

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'populateauthsystem_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            if qVersion() > '4.3.3':
                # noinspection PyArgumentList
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.title = self.tr(u'Populate Authentication System')
        self.action = None

        # Set up automated enacting of plugin at end of app launch
        self.iface.initializationCompleted.connect(self.app_initialized)

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
        return QCoreApplication.translate('PopulateAuthSystem', message)

    # noinspection PyPep8Naming
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/populateauthsystem/icon.png'
        icon = QIcon(icon_path)
        self.action = QAction(icon, self.tr(u'Manual run'),
                              self.iface.mainWindow())
        self.action.triggered.connect(self.run_gui)

        self.iface.addPluginToMenu(self.title, self.action)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginMenu(self.title, self.action)

        try:
            from tests import testerplugin
            from qgistester.tests import removeTestModule
            removeTestModule(testerplugin, 'PopulateAuthSystem')
        except:
            pass

    def app_initialized(self):
        """
        Semi-automated pre-population with minimal user interaction, but only at
        end of app launch, not after (like when loading via Plugin Manager).
        """
        # noinspection PyArgumentList
        if (not QgsAuthManager.instance().masterPasswordHashInDb()
                or not QgsAuthManager.instance().getCertIdentities()):
            authdlg = PopulateAuthSystemDialog(parent=self.mw,
                                               qgis_iface=self.iface,
                                               title=self.title,
                                               init_run=True)
            authdlg.exec_()

    def run_gui(self):
        """
        Pre-population with full user interaction.
        """
        authdlg = PopulateAuthSystemDialog(parent=self.mw,
                                           qgis_iface=self.iface,
                                           title=self.title,
                                           init_run=False)
        authdlg.exec_()
