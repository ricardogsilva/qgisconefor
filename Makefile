# Makefile for Conefor Inputs plugin

PLUGIN_NAME = qgisconefor

RESOURCE_FILES = resources_rc.py

CODE_FILES = \
conefordialog.py \
coneforinputsprocessor.py \
coneforthreads.py \
__init__.py \
processlayer.py \
qgisconefor.py \
utilities.py \
resources_rc.py

PROCESSING_DIR = processing

PROCESSING_FILES = \
$(PROCESSING_DIR)/__init__.py \
$(PROCESSING_DIR)/processingconeforinputs.py \
$(PROCESSING_DIR)/processingconeforprocessor.py \
$(PROCESSING_DIR)/coneforprovider.py

OTHER_FILES = \
metadata.txt \
README.rst \
conefor_dlg.ui \
LICENSE.txt

PLUGIN_INSTALL_DIR = $(HOME)/.qgis2/python/plugins/$(PLUGIN_NAME)
MODELS_DIR = models
ASSETS_DIR = assets

# There should be no need to change anything below this line

default: deploy

compile: $(RESOURCE_FILES)

%_rc.py : %.qrc
	pyrcc4 -o $@  $<

deploy: compile
	mkdir -p $(PLUGIN_INSTALL_DIR)
	mkdir -p $(PLUGIN_INSTALL_DIR)/$(PROCESSING_DIR)
	mkdir -p $(PLUGIN_INSTALL_DIR)/$(MODELS_DIR)
	mkdir -p $(PLUGIN_INSTALL_DIR)/$(ASSETS_DIR)
	cp -vf $(CODE_FILES) $(PLUGIN_INSTALL_DIR)
	cp -vf $(PROCESSING_FILES) $(PLUGIN_INSTALL_DIR)/$(PROCESSING_DIR)
	cp -vf $(RESOURCE_FILES) $(PLUGIN_INSTALL_DIR)
	cp -vf $(OTHER_FILES) $(PLUGIN_INSTALL_DIR)
	cp -vf $(MODELS_DIR)/* $(PLUGIN_INSTALL_DIR)/$(MODELS_DIR)
	cp -vf $(ASSETS_DIR)/* $(PLUGIN_INSTALL_DIR)/$(ASSETS_DIR)
