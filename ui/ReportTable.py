import datetime
try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from PyQt5 import uic
from sql.EngineSQL import *
from tools import Tools


class IncomeReport(QWidget):

    def __init__(self):
        super(IncomeReport, self).__init__()
        self.resize(401, 621)
        self.setFixedWidth(401)
        self.ui = uic.loadUi("resources/ui/CreateReport.ui", self)
        self.ui.btn_run.released.connect(self.load)

    @Tools.connectionWithLock
    def open(self, *args):
        self.ui.cmb_users.clear()
        for user in Cache.get(Staff, where=lambda u: u.type != StaffTypeEnum.dismissed):
            self.ui.cmb_users.addItem(user.name, QVariant(user.id))
        self.ui.table_result.setColumnCount(2)
        self.ui.table_result.setHorizontalHeaderLabels(("date", "amount"))
        self.show()

    @Tools.connectionWithLock
    def load(self):
        if self.ui.cmb_users.currentIndex() == -1:
            return

        try:
            start_date = datetime.date.fromisoformat(self.ui.line_start.text())
            end_date = datetime.date.fromisoformat(self.ui.line_end.text())
        except ValueError:
            return

        user_id = self.ui.cmb_users.currentData()
        staff_wallets = {w.wallet.lower() for w in Cache.get(StaffWallets, where=lambda u: u.staff == user_id)}
        send_wallets = {w.wallet.lower() for w in Cache.get(TransferWallets)}
        amount = 0

        self.ui.table_result.setSortingEnabled(False)
        self.ui.table_result.clear()
        self.ui.table_result.setHorizontalHeaderLabels(("date", "amount"))
        self.ui.table_result.setRowCount(0)

        for tx in Cache.get(Transfers):
            if tx.sender.lower() not in send_wallets:
                continue
            if tx.receiver.lower() not in staff_wallets:
                continue
            if not start_date <= tx.date.date() <= end_date:
                continue

            y = self.ui.table_result.rowCount()
            self.ui.table_result.setRowCount(y + 1)
            self.ui.table_result.setItem(y, 0, QTableWidgetItem(tx.date.date().isoformat()))
            self.ui.table_result.setItem(y, 1, QTableWidgetItem(f"{tx.amount_tx:.3f}"))
            amount += tx.amount_tx
        self.ui.table_result.setSortingEnabled(True)
        self.ui.line_total.setText(f"{amount:.3f}")
