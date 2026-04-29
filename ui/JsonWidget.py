try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from PyQt5 import uic
from sql import JSON
from ui import Dialogs
from tools import Tools


class Widget(QWidget):

    def __init__(self):
        super(Widget, self).__init__()
        self.ui = uic.loadUi("resources/ui/JSON.ui", self)
        self.setFixedSize(401, 71)
        self.ui.btn_to_json.released.connect(self.toJson)
        self.ui.btn_from_json.released.connect(self.fromJson)

    @Tools.unsafe
    def toJson(self, *args):
        text = self.ui.line_file.text()
        if not text:
            Dialogs.showMessage("enter path")
            return
        JSON.toJson(text)

    @Tools.unsafe
    def fromJson(self, *args):
        text = self.ui.line_file.text()
        if not text:
            Dialogs.showMessage("enter path")
            return
        reply = QMessageBox.question(self, "confirm", f"current DB will be dropped", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            JSON.fromJson(text)
