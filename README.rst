QGIS Conefor
============

A QGIS plugin for working with the `Conefor`_ application.

This plugin provides a bridge between QGIS and Conefor, allowing you to run all
of Conefor's landscape connectivity analysis algorithms from inside QGIS,
through the Processing framework. This provides a very convenient environment
for landscape and habitat analysis. Conefor algorithms can be directly
integrated in more complex workflows through models and scripts and use all of
the other GIS algorithms included in the processing framework.

The plugin also includes a GUI window which can be used solely for preparing
inputs to use by Conefor as a separate application.

.. _Conefor: http://conefor.org

Conefor authors are Santiago Saura (santiago.saura@upm.es) and Josep Torné. 
This plugin was developed by Ricardo Garcia Silva (ricardo.garcia.silva@gmail.com) 
with funding from ETSI Montes, Universidad Politécnica de Madrid. 
The plugin is released under a GPL license.

Installation
------------

#. This plugin is only useful when the Conefor application is already
   installed and available. Conefor has both GUI and CLI applications,
   both are free to install. In order to use this plugin you must install
   the *Conefor CLI* application. Get it from

   http://conefor.org

#.  The plugin should be available in the official QGIS plugins repository.
    It can be searched and installed directly from within QGIS using the plugin
    installer.

    If you wish to install directly from this repository and are using Linux:

    * Checkout any of the tagged versions (or the master branch) into some
      directory

    *  Execute the Makefile that comes with the source code. It will compile
       the PyQt related stuff (GUI dialog and resources) and place the
       plugin in QGIS's plugin path.

    *  Open QGIS and enable the Conefor Inputs plugin using the plugin manager

#. In QGIS, open the Processing options and configuration dialogue. Search for
   'Conefor' in the providers section. Be sure to enable the 'Activate' switch
   and input the path to where you have the Conefor CLI application.

Usage
-----

#.  `Using the standalone window`_
#.  `Using the Processing framework`_

.. _Using the standalone window: https://github.com/ricardogsilva/qgisconefor/blob/master/docs/manual.rst

.. _Using the Processing framework: https://github.com/ricardogsilva/qgisconefor/blob/master/docs/manual.rst

Issues and feature requests
---------------------------

Please use the bug tracker at

http://hub.qgis.org/projects/qgisconefor/issues
