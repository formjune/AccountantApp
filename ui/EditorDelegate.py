try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from tools import Tools


class Income(QItemDelegate):

    income_type: dict = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        data = index.data()
        num = index.column()
        if num != 2 or data not in self.income_type:
            QItemDelegate.paint(self, painter, option, index)
            return
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.income_type[data])


class PersonalSpending(QItemDelegate):

    user_id: dict = {}
    spending: dict = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        data = index.data()
        num = index.column()
        if num not in (1, 2):
            QItemDelegate.paint(self, painter, option, index)
            return
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        try:
            data_int = int(data)
            if num == 1:
                painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.user_id[data_int])
            else:
                painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.spending[data_int])
        except (KeyError, ValueError):
            painter.fillRect(option.rect, QColor(255, 128, 128))
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, data)


class RegularSpending(QItemDelegate):

    period_format: dict = {}
    PERIOD = "years", "months", "weeks", "days"

    @Tools.unsafe
    def paint(self, painter, option, index):
        num = index.column()

        if num != 3:
            QItemDelegate.paint(self, painter, option, index)
            return
        try:
            text = []
            data = index.data().split("/")
            assert len(data) == 4
            for p, l in zip(self.PERIOD, data):
                l = int(l)
                assert l >= 0
                if int(l):
                    text.append(f"{l} {p}")
            text = ", ".join(text)
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, text)
        except:
            painter.fillRect(option.rect, QColor(255, 128, 128))
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, "ERROR")


class Spending(QItemDelegate):

    tags = {}
    widget_table: QTableWidget
    regular_spending = {}
    onetime_spending = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        data = index.data()
        num = index.column()
        if num == 5:
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            elif data == "complete":
                painter.fillRect(option.rect, QColor(180, 220, 163))
            elif data == "partial":
                painter.fillRect(option.rect, QColor(153, 217, 234))
            else:
                painter.fillRect(option.rect, QColor(255, 128, 128))
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, data)

        elif num == 1:
            tags = []
            for i, symbol in enumerate(data, 1):
                if symbol == "1" and i in self.tags:
                    tags.append(self.tags[i])

            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, ", ".join(tags))

        elif num == 3:
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            try:
                if self.widget_table.item(index.row(), 2).text() == "regular":
                    text = self.regular_spending[int(data)]
                else:
                    text = self.onetime_spending[int(data)]
                painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, text)
            except (KeyError, ValueError):
                painter.fillRect(option.rect, QColor(255, 128, 128))
                painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, data)

        else:
            QItemDelegate.paint(self, painter, option, index)


class PromotionCommission(QItemDelegate):

    income_source: dict = {}
    income_type: dict = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        data = index.data()
        num = index.column()
        if num == 1 and data in self.income_source:
            data = self.income_source[data]
        elif num == 2 and data in self.income_type:
            data = self.income_type[data]
        else:
            QItemDelegate.paint(self, painter, option, index)
            return
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, data)


class Transfers(QItemDelegate):

    wallets: dict = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        data = index.data().lower()
        num = index.column()
        if num not in (3, 4) or data not in self.wallets:
            QItemDelegate.paint(self, painter, option, index)
            return

        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.wallets[data])


class Department(QItemDelegate):

    departments = {}
    staff = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        data = index.data().lower()
        num = index.column()
        if num < 2:
            QItemDelegate.paint(self, painter, option, index)
            return
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        data = int(data)
        if num == 2 and data in self.departments:
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.departments[data])
        elif num == 3 and data != -1 and data in self.staff:
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.staff[data])


class Staff(QItemDelegate):

    department = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        num = index.column()
        if num != 4:
            QItemDelegate.paint(self, painter, option, index)
            return
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        data = index.data().lower()
        data = int(data)
        if data in self.department:
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.department[data])


class OffDaysPercent(QItemDelegate):

    staff = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        num = index.column()
        if num != 1:
            QItemDelegate.paint(self, painter, option, index)
            return
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        data = int(index.data())
        if data in self.staff:
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.staff[data])
        elif data == 0:
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, "DEFAULT")
        else:
            painter.fillRect(option.rect, QColor(255, 128, 128))
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, str(data))


class StaffWallet(QItemDelegate):

    staff = {}

    @Tools.unsafe
    def paint(self, painter, option, index):
        num = index.column()
        if num != 1:
            QItemDelegate.paint(self, painter, option, index)
            return
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        data = int(index.data())
        if data in self.staff:
            painter.drawText(option.rect, Qt.AlignVCenter | Qt.AlignLeft, self.staff[data])
