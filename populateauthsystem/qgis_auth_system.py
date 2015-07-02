#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate QGIS authentication database with user config and (optionally)
generate OWS server configurations associated with it.

As it is coded, script will interact with the current user, asking for a master
authentication password, and pre-populate database with existing identity
credentials, which may be passphrase-protected, and optionally associate those
with OWS configurations.

NOTE: this script needs adjusted, or rewritten, relative to the desired result
and the existing authentication requirements for the network or user.

Some comments and syntax in this document are instructions to the PyCharm
Python IDE, e.g. # noinspection PyTypeChecker OR variable type definitions.

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
__author__ = 'Larry Shaffer'
__date__ = '2015/06/15'
__copyright__ = 'Copyright 2014-5, Boundless Spatial, Inc.'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import sys

from qgis.core import *
from qgis.gui import *
from qgis.utils import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *


class AuthSystem:

    # Title used in user messages and dialog title bars
    TITLE = 'Authentication System'

    # For semi-automated population, change these for PKCS#12 and CAs files
    # Supported file type extensions are:
    #   PKCS#12 = .p12 or .pfx
    #   CAs file = .pem or .der
    # NOTE: any CA cert chains contained in any PKCS#12 file will also be added;
    #       however, CA certs with identical signatures will not be duplicated
    PKI_DIR = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'test', 'pki-import')
    # Pre-formatted file names of identities/CAs, located in PKI_DIR
    PKCS_FILES = ['identity1.p12', 'identity2.p12']  # OR  = None
    # Extra Certifiate Authorities, if all CAs are not defined in PKCS file(s)
    CA_CERT_CHAIN = 'ca.pem'  # OR  = None

    # Whether PKCS files are always password-protected (triggers a prompt to
    # the user for their PKCS password during semi-automated population), unless
    # PKCS_PASS is set.
    PKCS_PROTECTED = True

    # If using a standard password for temporary PKCS files, set it here.
    # NOTE: this is not a wise strategy
    PKCS_PASS = 'password'

    # Whether to delete the PKI_DIR after successful semi-automated population
    # NOTE: recommended to delete, or else the PKI components might be loaded at
    #       every launching of QGIS application (depending upon implementation).
    DELETE_PKI_DIR = False

    # Whether server configs should be added during semi-automated population.
    # NOTE: the settings in populate_servers() MUST be reviewed/edited
    ADD_SSL_SERVERS = True

    # Whether OWS connections should be added during semi-automated population.
    # NOTE: the settings in config_ows_connections() MUST be reviewed/edited
    ADD_OWS_CONNECTIONS = True
    # File name of identity, whose related auth config is applied to OWS configs
    PKCS_OWS = 'identity1.p12'  # OR  = None

    def __init__(self, qgis_iface, messagebar=None):
        # note, this could be a mock iface implementation, as when testing
        self.iface = qgis_iface
        """:type : QgisInterface"""

        self.mw = None
        if self.iface is not None:
            self.mw = iface.mainWindow()
            """:type : QMainWindow"""

        self.in_plugin = True
        if self.mw is None:
            # we are running outside of a plugin
            self.in_plugin = False

        self.msgbar = None
        if self.in_plugin:
            if messagebar is not None:
                self.msgbar = messagebar
                """:type : QgsMessageBar"""
            else:
                self.msgbar = self.iface.messageBar()
                """:type : QgsMessageBar"""

        # Result caches
        # dictionary of identity cert sha and its related auth config ID:
        #   {'cert_sha': 'authcfg_id', ...}
        self.identity_configs = {}
        # string lists of results
        self.identities = []
        self.identity_ows_sha = ''
        self.authconfigs = []
        self.authorities = []
        self.servers = []
        self.connections = []

    def clear_results(self):
        self.identity_configs = {}
        self.identities = []
        self.identity_ows_sha = ''
        self.authconfigs = []
        self.authorities = []
        self.servers = []
        self.connections = []

    def msg(self, msg, kind='warn'):
        if kind == 'warn':
            if self.in_plugin:
                self.msgbar.pushWarning(self.TITLE, msg)
            else:
                # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
                QMessageBox.warning(self.mw, self.TITLE, msg)
        elif kind == 'info':
            if self.in_plugin:
                self.msgbar.pushInfo(self.TITLE, msg)
            else:
                # noinspection PyTypeChecker,PyArgumentList, PyCallByClass
                QMessageBox.information(self.mw, self.TITLE, msg)

    def master_pass_set(self):
        """
        Set master password or check master password is set.
        Asks user for authentication master password and stores it in
        qgis-auth.db. This also verifies the set password by comparing password
        against its derived hash stored in auth db.

        :return: bool Whether it is set or verifies
        """
        # noinspection PyArgumentList
        res = QgsAuthManager.instance().setMasterPassword(True)
        if not res:
            self.msg("Master password not defined or does not match existing. "
                     "Canceling operation.")
        return res

    def populate_identities(self, multiple=False, from_filesys=False):
        """
        Import certificate-based identities into authentication database.
        Any CA cert chains contained in any PKCS#12 file will also be added.

        :param multiple: bool Whether to offer import multiple times
        :param from_filesys: bool Skip user interaction and load from filesystem
        :return: bool Whether operation was successful
        """
        if not self.master_pass_set():
            return False

        pkibundles = []
        if from_filesys and self.PKCS_FILES is not None:
            for pkcs_name in self.PKCS_FILES:
                pkcs_path = os.path.join(self.PKI_DIR, pkcs_name)
                if not os.path.exists(pkcs_path):
                    continue
                psswd = self.PKCS_PASS
                if self.PKCS_PROTECTED and self.PKCS_PASS != '':
                    # noinspection PyCallByClass,PyTypeChecker
                    psswd, ok = QInputDialog.getText(
                        self.mw,
                        "Client Certificate Key",
                        "'{0}' password:".format(pkcs_name), QLineEdit.Normal)
                    if not ok:
                        continue
                # noinspection PyCallByClass,PyTypeChecker
                bundle = QgsPkiBundle.fromPkcs12Paths(pkcs_path, psswd)
                if not bundle.isNull():
                    pkibundles.append(bundle)
                    if self.PKCS_OWS is not None and self.PKCS_OWS == pkcs_name:
                            self.identity_ows_sha = bundle.certId()
                else:
                    self.msg("Could not load identity file, continuing ({0})"
                             .format(pkcs_name))
        else:
            def import_identity(parent):
                dlg = QgsAuthImportIdentityDialog(
                    QgsAuthImportIdentityDialog.CertIdentity, parent)
                dlg.setWindowModality(Qt.WindowModal)
                dlg.resize(400, 250)
                if dlg.exec_():
                    bndle = dlg.pkiBundleToImport()
                    if bndle.isNull():
                        self.msg("Could not load identity file")
                        return None, True
                    return bndle, True
                return None, False

            while True:
                pkibundle, imprt_res = import_identity(self.mw)
                if pkibundle is not None:
                    pkibundles.append(pkibundle)
                if multiple and imprt_res:
                    continue
                break

        if not pkibundles:
            return False

        # Now try to store identities in the database
        for bundle in pkibundles:
            bundle_cert = bundle.clientCert()
            bundle_key = bundle.clientKey()
            bundle_cert_sha = bundle.certId()
            bundle_ca_chain = bundle.caChain()

            # noinspection PyArgumentList
            if QgsAuthManager.instance().existsCertIdentity(bundle_cert_sha):
                continue

            # noinspection PyArgumentList
            if not QgsAuthManager.instance().\
                    storeCertIdentity(bundle_cert, bundle_key):
                self.msg("Could not store identity in auth database")
                return False

            # noinspection PyArgumentList
            subj_issu = "{0} (issued by: {1})".format(
                QgsAuthCertUtils.resolvedCertName(bundle_cert),
                QgsAuthCertUtils.resolvedCertName(bundle_cert, True)
            )
            self.identities.append(subj_issu)

            # Now try to assign the identity to an auth config
            # noinspection PyArgumentList
            config_name = 'Identity - {0}'.format(
                QgsAuthCertUtils.resolvedCertName(bundle_cert))
            bundle_config = QgsAuthConfigIdentityCert()
            bundle_config.setName(config_name)
            bundle_config.setCertId(bundle_cert_sha)

            # noinspection PyArgumentList
            if not QgsAuthManager.instance().\
                    storeAuthenticationConfig(bundle_config):
                self.msg("Could not store bundle identity config")
                return False

            bundle_configid = bundle_config.id()
            if not bundle_configid:
                self.msg("Could not retrieve identity config id from database")
                return False

            self.authconfigs.append("{0} (authcfg: {1})"
                                    .format(config_name, bundle_configid))

            self.identity_configs[bundle_cert_sha] = bundle_configid

            if bundle_ca_chain:  # this can fail (user is notified)
                self.populate_ca_certs(bundle_ca_chain)

        return True

    def populate_ca_certs(self, ca_certs=None, from_filesys=False):
        """
        Import Certificate Authorities into authentication database.
        Certs with identical signatures will not be duplicated.

        :param ca_certs: [QSslCertificate] Certs to add
        :param from_filesys: bool Skip user interaction and load from filesystem
        :return: bool Whether operation was successful
        """
        if not self.master_pass_set():
            return False

        if from_filesys:
            if self.CA_CERT_CHAIN is not None:
                ca_certs_path = os.path.join(self.PKI_DIR, self.CA_CERT_CHAIN)
                if os.path.exists(ca_certs_path):
                    # noinspection PyArgumentList,PyTypeChecker,PyCallByClass
                    ca_certs = QgsAuthCertUtils.certsFromFile(ca_certs_path)
        elif ca_certs is None:
            dlg = QgsAuthImportCertDialog(self.mw,
                                          QgsAuthImportCertDialog.CaFilter,
                                          QgsAuthImportCertDialog.FileInput)
            dlg.setWindowModality(Qt.WindowModal)
            dlg.resize(400, 250)
            if dlg.exec_():
                ca_certs = dlg.certificatesToImport()

        if ca_certs is not None:
            # noinspection PyArgumentList
            if not QgsAuthManager.instance().storeCertAuthorities(ca_certs):
                self.msg(
                    "Could not store Certificate Authorities in auth database")
                return False
            # noinspection PyArgumentList
            QgsAuthManager.instance().rebuildCaCertsCache()
            # noinspection PyArgumentList
            QgsAuthManager.instance().rebuildTrustedCaCertsCache()

            for ca_cert in ca_certs:
                # noinspection PyArgumentList
                subj_issu = "{0} ({1})".format(
                    QgsAuthCertUtils.resolvedCertName(ca_cert),
                    QgsAuthCertUtils.resolvedCertName(ca_cert, True)
                )
                self.authorities.append(subj_issu)

        return True

    def populate_servers(self, from_filesys=False):
        """
        Populate SSL server configurations. This should be done *once* on semi-
        automated population. After that, the SSL Errors dialog offers users the
        ability to auto-configure an SSL server's cert exception upon connection
        to the server (example: users who have erased the auth database).

        :param from_filesys: bool Skip user interaction and load from filesystem
        :return: bool Whether operation was successful
        """
        if not from_filesys or not self.ADD_SSL_SERVERS:
            return False

        if not self.master_pass_set():
            return False

        # NOTE: copy/paste this block to add another server config
        ssl_cert_name = 'server.pem'
        ssl_cert_path = os.path.join(self.PKI_DIR, ssl_cert_name)
        if os.path.exists(ssl_cert_path):
            # noinspection PyTypeChecker,PyArgumentList
            ssl_cert = QgsAuthCertUtils.certFromFile(ssl_cert_path)
            if ssl_cert.isNull():
                self.msg("SSL server certificate is null for '{0}'"
                         .format(ssl_cert_name))
            else:
                hostport = 'localhost:8443'
                config = QgsAuthConfigSslServer()
                config.setSslCertificate(ssl_cert)
                config.setSslHostPort(hostport)
                # http://doc.qt.io/qt-4.8/qsslerror.html#SslError-enum
                config.setSslIgnoredErrorEnums(
                    [QSslError.SelfSignedCertificate])
                # http://doc.qt.io/qt-4.8/qsslsocket.html#PeerVerifyMode-enum
                config.setSslPeerVerifyMode(QSslSocket.VerifyPeer)
                # http://doc.qt.io/qt-4.8/qsslsocket.html#peerVerifyDepth
                config.setSslPeerVerifyDepth(0)
                # http://doc.qt.io/qt-4.8/qssl.html#SslProtocol-enum
                config.setSslProtocol(QSsl.TlsV1)

                if not config.isNull():
                    # noinspection PyArgumentList
                    if not QgsAuthManager.instance().storeSslCertCustomConfig(
                            config):
                        self.msg("Could not store SSL config for '{0}'"
                                 .format(hostport))

        return True

    def config_ows_connections(self, authcfg=None, from_filesys=False):
        """
        If the user does not have the OWS connection(s) that this auth config is
        meant to connect to, define now.

        NOTE: this assumes the individual connections do not already exist.
        If the connection settings do exist, this will OVERWRITE them.

        :param authcfg: str The auth config ID to associate connections with
        :param from_filesys: bool Skip user interaction and load from filesystem
        :return: bool Whether operation was successful
        """
        if not self.identity_configs:
            self.msg("No authentication configs for imported identities exists")
            return False

        if from_filesys and not self.ADD_OWS_CONNECTIONS:
            return False

        configid = authcfg
        if from_filesys and self.identity_ows_sha \
                and self.identity_ows_sha in self.identity_configs:
            configid = self.identity_configs[self.identity_ows_sha]

        if not configid or configid is None:
            self.msg("No authentication config ID defined for OWS connections")
            return False

        settings = QSettings()  # get application's settings object

        # qDebug('settings.fileName(): {0}'.format(settings.fileName()))
        # qDebug('settings.organizationName(): {0}'
        #        .format(settings.organizationName()))
        # qDebug('settings.applicationName(): {0}'
        #        .format(settings.applicationName()))

        self.connections = []

        # WMS
        connkind = 'WMS'
        connname = 'My {0} SSL Server'.format(connkind)
        self.connections.append("{0} (authcfg: {1})".format(connname, configid))
        credskey = '/Qgis/{0}/{1}'.format(connkind, connname)
        connkey = '/Qgis/connections-{0}/{1}'.format(connkind.lower(), connname)

        settings.setValue(credskey + '/authcfg',
                          configid)  # link to auth config
        settings.setValue(credskey + '/username', '')  # deprecated; use config
        settings.setValue(credskey + '/password', '')  # deprecated; use config

        settings.setValue(connkey + '/url',
                          'https://localhost:8443/geoserver/wms')

        # Optional settings for WMS (these are the defaults)
        # dpiMode: 0=Off, 1=QGIS, 2=UMN, 4=GeoServer, 7=All (default)
        settings.setValue(connkey + '/dpiMode', 7)
        settings.setValue(connkey + '/ignoreAxisOrientation', False)
        settings.setValue(connkey + '/ignoreGetFeatureInfoURI', False)
        settings.setValue(connkey + '/ignoreGetMapURI', False)
        settings.setValue(connkey + '/invertAxisOrientation', False)
        settings.setValue(connkey + '/referer', '')
        settings.setValue(connkey + '/smoothPixmapTransform', False)

        # WCS
        connkind = 'WCS'
        connname = 'My {0} SSL Server'.format(connkind)
        self.connections.append("{0} (authcfg: {1})".format(connname, configid))
        credskey = '/Qgis/{0}/{1}'.format(connkind, connname)
        connkey = '/Qgis/connections-{0}/{1}'.format(connkind.lower(), connname)

        settings.setValue(credskey + '/authcfg',
                          configid)  # link to auth config
        settings.setValue(credskey + '/username', '')  # deprecated; use config
        settings.setValue(credskey + '/password', '')  # deprecated; use config

        settings.setValue(connkey + '/url',
                          'https://localhost:8443/geoserver/wcs')

        # Optional settings for WCS (these are the defaults)
        # dpiMode: 0=Off, 1=QGIS, 2=UMN, 4=GeoServer, 7=All (default)
        settings.setValue(connkey + '/dpiMode', 7)
        settings.setValue(connkey + '/ignoreAxisOrientation', False)
        settings.setValue(connkey + '/ignoreGetMapURI', False)
        settings.setValue(connkey + '/invertAxisOrientation', False)
        settings.setValue(connkey + '/referer', '')
        settings.setValue(connkey + '/smoothPixmapTransform', False)

        # WFS
        connkind = 'WFS'
        connname = 'My {0} SSL Server'.format(connkind)
        self.connections.append("{0} (authcfg: {1})".format(connname, configid))
        credskey = '/Qgis/{0}/{1}'.format(connkind, connname)
        connkey = '/Qgis/connections-{0}/{1}'.format(connkind.lower(), connname)

        settings.setValue(credskey + '/authcfg',
                          configid)  # link to auth config
        settings.setValue(credskey + '/username', '')  # deprecated; use config
        settings.setValue(credskey + '/password', '')  # deprecated; use config

        settings.setValue(connkey + '/url',
                          'https://localhost:8443/geoserver/wfs')

        # Optional settings for WFS (these are the defaults)
        settings.setValue(connkey + '/referer', '')

        return True

    def population_results(self):
        res = ""
        if self.identities:
            res += "Personal identities imported:\n{0}\n\n".format(
                "\n".join(["  " + i for i in self.identities]))
        if self.authconfigs:
            res += "Authentication configurations created:\n{0}\n\n".format(
                "\n".join(["  " + a for a in self.authconfigs]))
        if self.authorities:
            res += "Certificate Authorities imported:\n{0}\n\n".format(
                "\n".join(["  " + a for a in self.authorities]))
        if self.servers:
            res += "SSL server configs created:\n{0}\n\n".format(
                "\n".join(["  " + s for s in self.servers]))
        if self.connections:
            res += "OWS connection configs created:\n{0}\n\n".format(
                "\n".join(["  " + c for c in self.connections]))

        return res