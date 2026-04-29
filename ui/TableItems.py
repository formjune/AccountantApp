from PyQt5.Qt import *
from sqlalchemy import Integer, Float


class EditorItem(QTableWidgetItem):

    def __lt__(self, other):
        column = self.column()
        data_type = self.tableWidget().TABLE.types[column]
        if data_type in (Float, Integer):
            return float(self.text()) > float(other.text())
        return self.text() > other.text()


class ViewerItem(QTableWidgetItem):

    INDICES: set

    def __lt__(self, other):
        column = self.column()
        if column in self.INDICES:
            text_1 = self.text()
            value_1 = 0 if text_1 == "UPDT" else float(text_1)
            text_2 = other.text()
            value_2 = 0 if text_2 == "UPDT" else float(text_2)
            return value_1 > value_2
        return self.text() > other.text()


class TransfersItem(ViewerItem):

    INDICES = {3, 4}


class SpendingItem(ViewerItem):

    INDICES = {2, 7, 8}
