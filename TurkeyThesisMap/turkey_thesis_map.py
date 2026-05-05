import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .turkey_thesis_map_dialog import TurkeyThesisMapDialog


class TurkeyThesisMap:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.action = QAction(QIcon(icon_path), "TurkeyThesisMap", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&TurkeyThesisMap", self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&TurkeyThesisMap", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = TurkeyThesisMapDialog(self.iface, self.plugin_dir)
        self.dialog.refresh_cache_label()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
