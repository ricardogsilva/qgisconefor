QGIS Conefor
============

A QGIS plugin for working with the [Conefor][] application.

This plugin provides a bridge between QGIS and Conefor, allowing you to run all
of Conefor's landscape connectivity analysis algorithms from inside QGIS,
through the Processing framework. This provides a very convenient environment
for landscape and habitat analysis. Conefor algorithms can be directly
integrated in more complex workflows through models and scripts and use all of
the other GIS algorithms included in the processing framework.

The plugin also includes a GUI window which can be used solely for preparing
inputs to use by Conefor as a separate application.

[Conefor]: http://conefor.org "Conefor"

Installation
------------

1.  This plugin is only useful when the Conefor application is already
    installed and available. Conefor has both GUI and CLI applications, 
    both are free to install. In order to use this plugin you must install 
    the Conefor CLI application. At the moment, Conefor CLI is free to install,
    but you have to send an e-mail to its authors to request your copy of the
    software.

    Conefor is only available for Microsoft Windows. However, it works on 
    Linux (and possibly other operating systems as well) using wine. If you are
    not using Windows, be sure to install wine as well.

2.  The plugin should be available in the official QGIS plugins repository. 
    It can be searched and installed directly from within QGIS using the plugin
    installer.

    If you wish to install directly from this respository and are using Linux:

    *   Checkout any of the tagged versions (or the master branch) into some
        directory

    *   Execute the Makefile that comes with the source code. It will compile
        the PyQt related stuff (GUI dialog and resources) and place the 
        plugin in QGIS's plugin path.

    *   Open QGIS and enable the Conefor Inputs plugin using the plugin manager

3. In QGIS, open the Processing options and configuration dialogue. Search for
   'Conefor' in the providers section. Be sure to enable the 'Activate' switch
   and input the path to where you have the Conefor CLI application.

Usage
-----

1.  Using the standalone window
2.  Using the Processing framework
