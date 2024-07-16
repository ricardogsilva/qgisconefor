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


def store_output_in_target_directory(
        intended_output_dir: Path,
        output: Path,
        append_if_exists: bool = False
) -> Path:
    contents = output.read_text()
    target = intended_output_dir / output.name
    if target.exists():
        if append_if_exists:
            with target.open(mode="a") as fh:
                fh.write(contents)
        else:
            shutil.move(output, target)
        output.unlink(missing_ok=True)
    elif contents:
        shutil.move(output, target)
    return target


def store_processing_outputs(
        intended_output_dir: Path,
        outputs: list[Path],
) -> list[Path]:
    stored = []
    for output in outputs:
        if output.name in (
                "results_all_overall_indices.txt",
                "results_all_EC(IIC).txt",
                "results_all_EC(PC).txt"
        ):
            stored.append(
                store_output_in_target_directory(
                    intended_output_dir, output, append_if_exists=True)
            )
        else:
            stored.append(
                store_output_in_target_directory(
                    intended_output_dir, output
                )
            )
    return stored
