from qgis.gui import QgisInterface


def classFactory(iface: QgisInterface):
    from .main import QgisConefor

    return QgisConefor(iface)
