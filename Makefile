# Makefile for Conefor Inputs plugin

PLUGIN_NAME = qgisconefor

UI_FILES = ui_conefor_dlg.py ui_help_dlg.py

RESOURCE_FILES = resources_rc.py

CODE_FILES = \
conefordialog.py \
coneforinputsprocessor.py \
coneforthreads.py \
__init__.py \
processingconeforinputs.py \
processingconeforprocessor.py \
processingconeforprovider.py \
processlayer.py \
qgisconefor.py \
utilities.py \
resources_rc.py \
ui_conefor_dlg.py \
ui_help_dlg.py

OTHER_FILES = \
help_conefor.html \
help.html \
icon.png \
metadata.txt \
README.rst

PLUGIN_INSTALL_DIR = $(HOME)/.qgis2/python/plugins/$(PLUGIN_NAME)
MODELS_DIR = models
HELP_ASSETS_DIR = help_assets

# There should be no need to change anything below this line

default: deploy

compile: $(UI_FILES) $(RESOURCE_FILES)

%_rc.py : %.qrc
	pyrcc4 -o $@  $<

%.py : %.ui
	pyuic4 -o $@ $<

deploy: compile
	mkdir -p $(PLUGIN_INSTALL_DIR)
	mkdir -p $(PLUGIN_INSTALL_DIR)/$(MODELS_DIR)
	mkdir -p $(PLUGIN_INSTALL_DIR)/$(HELP_ASSETS_DIR)
	cp -vf $(CODE_FILES) $(PLUGIN_INSTALL_DIR)
	cp -vf $(UI_FILES) $(PLUGIN_INSTALL_DIR)
	cp -vf $(RESOURCE_FILES) $(PLUGIN_INSTALL_DIR)
	cp -vf $(OTHER_FILES) $(PLUGIN_INSTALL_DIR)
	cp -vf $(MODELS_DIR)/* $(PLUGIN_INSTALL_DIR)/$(MODELS_DIR)
	cp -vf $(HELP_ASSETS_DIR)/* $(PLUGIN_INSTALL_DIR)/$(HELP_ASSETS_DIR)
