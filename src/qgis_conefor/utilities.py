import qgis.core
import qgis.utils
from qgis.PyQt import QtCore

from .schemas import QgisConeforSettingsKey


def log(message, level=qgis.core.Qgis.Info):
    """Helper function to facilitate using QGIS' logging system."""
    qgis.utils.QgsMessageLog.logMessage(message, "qgisconefor", level=level)


def get_features(layer, use_selected, filter_id=None):
    """Return the features to process.

    Inputs:

        layer - A QgsVectorLayer

        use_selected - A boolean indicating if only the selected features
            should be used

        filter_id - The id of a feature to extract. If None (the default),
            the result will contain all the features (or all the selected
            features in case the use_selected argument isTrue)

    The output can be either a QgsFeatureIterator or a python list
    with the features. Both datatypes are suitable for using inside a
    for loop.

    If the use_selected argument is True but there are no features
    currently selected, all the features in the layer will be returned.
    """

    features = []
    if use_selected:
        features = layer.selectedFeatures()
        if filter_id is not None:
            features = [f for f in features if f.id() == filter_id]
    if not any(features):
        if filter_id is not None:
            request = qgis.core.QgsFeatureRequest(filter_id)
            features = layer.getFeatures(request)
        else:
            features = layer.getFeatures()
    return features


def get_all_values(layer, fields):
    result = []
    for feat in layer.getFeatures():
        for field in fields:
            result.append({
                "field" : field.name(),
                "value" : feat.attribute(field.name()),
            })
    return result


def exist_selected_features(qgis_layers):
    exist_selected = False
    for layer in qgis_layers:
        if layer.selectedFeatureCount() > 1:
            exist_selected = True
    return exist_selected


def extract_contents(path):
    """
    Extract a text file's contents.
    Assumes ASCII file and encoding
    """

    result = []
    with open(path) as fh:
        for line in fh:
            result.append(line)
    return result


def save_settings_key(key: QgisConeforSettingsKey, value):
    settings = qgis.core.QgsSettings()
    settings.setValue(key.value, value)
    settings.sync()


def load_settings_key(
        key: QgisConeforSettingsKey,
        as_boolean: bool = False,
        default_to=None
):
    settings = qgis.core.QgsSettings()
    value = settings.value(key.value, defaultValue=default_to)
    if as_boolean:
        result = True
        if value.lower() in ("false", "no", "0"):
            result = False
    else:
        result = value
    return result
