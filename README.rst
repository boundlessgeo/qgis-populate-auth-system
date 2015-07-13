Populate Authentication System - QGIS Plugin
============================================

A plugin to populate and configure the authentication system in QGIS. Can be set
up for semi-automated population at QGIS application initialization completion
(e.g. new master password, import PKI components and set up SSL server and OWS
configurations), or can be manually run after population to import new PKI
components with the option to replace an existing one, e.g. which may no longer
be valid.

Plugin Usage
------------

Upon app initialization completion (semi-automated population), user will be
prompted to enter a NEW  authentication master password, or enter their CURRENT
one. See ``populateauthsystem/qgis_auth_system.py`` comments for details on
setting variables for automation.

User can manually run plugin selecting the following menu: ``Plugins -> Populate Authentication System -> Manual run``. This allows for new PKI components to be
populated, optionally replacing existing ones.

Contents of directory
---------------------

- ``pavement.py`` A build script for installing, packaging plugin and building
  its documentation. Uses the `Paver`_ build tool, which must be installed first.

  Tasks from ``pavement.py`` (run with ``paver <task name>``, e.g.
  ``paver html``)::

    html               - build documentation and install it into plugin/help
    install            - install plugin to qgis
    package            - create filtered package for plugin release
    package_with_tests - create filtered package for plugin that includes the test suite
    qrcs               - run all .qrc files through pyrcc4 to generate resource modules
    upload             - upload the package to the server


- ``doc`` Documentation for the plugin (incomplete), built using the `Sphinx`_
  Python documentaion tool. Use ``paver html`` command.

- ``populateauthsystem`` The plugin directory. Installed in normal PyQGIS
  location as defined in `QGIS documentation`_. Use the ``paver install``
  command during development.

  - ``metadata.txt`` Plugin information used by QGIS.

  - ``populate_auth_system.py`` Main plugin file that runs at application
    initialization completion, and also loads a GUI menu item, under Plugins
    menu, for manually running plugin later.

  - ``populate_auth_system_dialog.py`` Main GUI module that contains all logic
    for communicating with user.

  - ``populate_auth_system_dialog.ui`` Qt Designer user interface file. This is
    automatically loaded by the ``populate_auth_system_dialog.py`` module.

  - ``qgis_auth_system.py`` Interface module to the QGIS authentication system
    with a focus on populating PKI credentials, CA certificates, authentication
    configurations and, optionally, network and SSL configurations.

    .. note::
       **This module MUST be reviewed and edited** to set up the parameters for
       semi-automated pre-population of the authentication database, relative to
       the desired result and the existing authentication requirements for the
       network or user.

  - ``resources.qrc|py`` Qt resource file and 'compiled' Python module. Use the
    ``paver qrcs`` command to generate the ``resources.py`` module, if you have
    edited the ``resources.qrc`` file.

  - ``scripts`` Population scripts that work as standalone utilities, meant to
    be run from a Terminal/Console environment. See ``README.txt`` in folder.

  - ``test`` Unit and integration tests (incomplete).

    - ``certs-keys`` Sample PKI components. The default password used in all
      protected files is ``password``.

    - ``pki-import`` Sample PKI components used by default in population
      semi-automated run (could be deleted, if set to be). The default password 
      used in all identities is ``password``.

- ``README.rst`` This file.

.. _Paver: http://paver.github.io/paver/
.. _Sphinx: http://sphinx-doc.org/
.. _QGIS documentation:
   http://docs.qgis.org/2.8/en/docs/pyqgis_developer_cookbook/plugins.html#developing-plugins
