import functools

try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from PyQt5 import uic


class Dock(QDockWidget):

    def __init__(self, widget, title):
        super(Dock, self).__init__()
        self.setWindowTitle(title)
        self.wrap_widget = QWidget()
        uic.loadUi("resources/ui/EditTableDock.ui", self.wrap_widget)
        layout = self.wrap_widget.layout()
        p = 2
        for i, text in enumerate(widget.COLUMN_NAMES):
            check_box = QCheckBox()
            check_box.setChecked(True)
            check_box.setToolTip(text)
            layout.addWidget(check_box, p, 0, 1, 1)
            check_box.toggled.connect(functools.partial(self.toggleColumn, i))
            p += 1
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer, p, 0, 1, 1)
        layout.addWidget(widget, 0, 1, p + 1, 1)
        self.wrap_widget.btn_add.setEnabled(widget.SUPPORTS_ADD)
        self.wrap_widget.btn_add.released.connect(widget.addRow)
        self.wrap_widget.btn_delete.released.connect(widget.deleteRows)
        self._widget = widget
        self.setWidget(self.wrap_widget)
        self.visibilityChanged.connect(self.updateTable)
        self.hide()

    def updateTable(self, value: bool):
        """load for the first time"""
        if value:
            self._widget.loadData(True)

    def closeEvent(self, a0):
        """unload table from memory"""
        self._widget.unload()

    def toggleColumn(self, column, value):
        if value:
            self._widget.showColumn(column)
        else:
            self._widget.hideColumn(column)


class TransferDock(QDockWidget):

    def __init__(self, widget):
        super(QDockWidget, self).__init__()
        self.setWindowTitle("Transfers Confirm")
        self.setWidget(widget)
        self._widget = widget
        self.visibilityChanged.connect(self.updateTable)
        self.hide()

    def updateTable(self, value: bool):
        """load for the first time"""
        if value:
            self._widget.loadData(True)

    def closeEvent(self, a0):
        """unload table from memory"""
        self._widget.unload()
