import shutil
from pathlib import Path

import qgis.core
import qgis.utils

from .schemas import QgisConeforSettingsKey


def log(message, level=qgis.core.Qgis.Info):
    """Helper function to facilitate using QGIS' logging system."""
    qgis.utils.QgsMessageLog.logMessage(message, "qgisconefor", level=level)


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
    if as_boolean and type(value) is not bool:
        result = True
        if value.lower() in ("false", "no", "0"):
            result = False
    else:
        result = value
    return result
