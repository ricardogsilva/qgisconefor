import qgis.core
from qgis.PyQt import (
    QtCore,
    QtGui,
)

from ...schemas import ICON_RESOURCE_PATH


class Base(qgis.core.QgsProcessingAlgorithm):

    def group(self):
        return None

    def groupId(self):
        return None

    def tr(self, string: str):
        return QtCore.QCoreApplication.translate("Processing", string)

    def icon(self):
        return QtGui.QIcon(ICON_RESOURCE_PATH)

    @staticmethod
    def _update_progress(feedback_obj, processor):
        feedback_obj.setPercentage(processor.global_progress)

    @staticmethod
    def _update_info(feedback_obj, info, section=0):
        feedback_obj.setInfo(info)
