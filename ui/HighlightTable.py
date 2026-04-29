try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from tools import Tools


class HighlightTable(QTableWidget):

    def __init__(self):
        super(HighlightTable, self).__init__()
        self.setMouseTracking(True)
        self.cellEntered.connect(self.highlightUnderMouseRow)
        self.currentCellChanged.connect(self.highlightRow)
        self.verticalHeader().hide()

    def highlightRow(self, current_row: int, current_column: int, previous_row: int, previous_column: int) -> None:
        """set background color for active row"""
        if current_row == previous_row:
            return
        color = QColor(151, 224, 255)
        for x in range(self.columnCount()):
            self.getItemNative(previous_row, x).setBackground(Qt.white)
            self.getItemNative(current_row, x).setBackground(color)

    @Tools.unsafe
    def highlightUnderMouseRow(self, row: int, column: int) -> None:
        try:
            last_row = self._last_item.row()
            if last_row != self.currentRow():
                for x in range(self.columnCount()):
                    self.getItemNative(last_row, x).setBackground(Qt.white)
        except:
            pass
        if row == -1 or column == -1 or row == self.currentRow():
            self._last_item = None
            return
        self._last_item = self.getItemNative(row, column)
        color = QColor(230, 230, 230)
        for x in range(self.columnCount()):
            self.getItemNative(row, x).setBackground(color)

    def getItemNative(self, y: int, x: int) -> QWidgetItem:
        """safe method to get item data"""
        item = self.item(y, x)
        if item is None:
            item = QTableWidgetItem()
            item.setData(Qt.DisplayRole, "")
            self.setItem(y, x, item)
        return item

    def fillTable(self) -> None:
        """fill table with empty values"""
        for row in range(self.rowCount()):
            for column in range(self.columnCount()):
                self.setItem(row, column, QTableWidgetItem())
