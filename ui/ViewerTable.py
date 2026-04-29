import functools
import os
try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from blockchain import EngineWeb3
from sql import EngineSQL, Convert
from sql.Tables import *
from sql.Enumerators import *
from tools import Tools
from ui import HighlightTable, Application, TableItems


class SpendingView(HighlightTable.HighlightTable):

    TABLE = Spending
    COLUMN_NAMES = "confirm", "wallet", "ID", "purpose", "tags", "type", "date", "amount", "amount left"
    COLUMN_WIDTH = 100, 100, 50, 300, 200, 200, 200, 100, 100
    filter_text = ""
    filter_start_month = 0
    filter_end_month = 1e10

    def __init__(self, confirm_dialog):
        super(SpendingView, self).__init__()
        self.confirm_dialog = confirm_dialog
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().hide()
        self.loadData()
        for width in enumerate(self.COLUMN_WIDTH):
            self.setColumnWidth(*width)

    @Tools.connection
    def loadData(self) -> None:
        data = EngineSQL.Cache.get(Spending, lambda s: s.status == PaymentStatusEnum.unpaid, lambda s: s.date)
        onetime_spending = {s.id: s for s in EngineSQL.Cache.get(OneTimeSpending)}
        regular_spending = {s.id: s for s in EngineSQL.Cache.get(RegularSpending)}
        tags = {s.id: s.name for s in EngineSQL.Cache.get(Tags)}

        self.clear()
        self.setRowCount(len(data))
        self.setColumnCount(len(self.COLUMN_NAMES))
        self.setHorizontalHeaderLabels(self.COLUMN_NAMES)
        self.setSortingEnabled(False)
        self.fillTable()
        for row, block in enumerate(data):
            button = QPushButton("confirm")
            button.released.connect(functools.partial(self.confirm_dialog.open, block.id, block.left_amount))
            self.setCellWidget(row, 0, button)
            if block.tags[:1] == "1":
                button = QPushButton("copy wallet")
                button.released.connect(functools.partial(self.copyWallet, block))
                self.setCellWidget(row, 1, button)

            try:
                if block.spending_type == SpendingTypeEnum.regular:
                    purpose = regular_spending[block.spending_id].purpose
                else:
                    purpose = onetime_spending[block.spending_id].purpose
            except KeyError:
                purpose = ""

            for column, item in enumerate(Convert.asTupleView(block), 2):
                if column == 3:
                    self.setItem(row, column, TableItems.SpendingItem(purpose))
                elif column == 4:
                    tags_block = []
                    for i, letter in enumerate(item, 1):
                        if letter == "1" and i in tags:
                            tags_block.append(tags[i])
                    self.setItem(row, column, TableItems.SpendingItem(", ".join(tags_block)))
                elif column in (8, 7) and block.spending_type == SpendingTypeEnum.regular:
                    r_s = regular_spending[block.spending_id]
                    self.setItem(row, column, TableItems.SpendingItem("UPDT" if r_s.unpredictable else item))
                else:
                    self.setItem(row, column, TableItems.SpendingItem(item))
        self.setSortingEnabled(True)
        self.filterRows()

    def deletePaidRow(self, index):
        for row in range(self.rowCount()):
            try:
                tx_index = int(self.item(row, 1).text())
                if tx_index == index:
                    self.removeRow(row)
                    return
            except Exception as e:
                print(f"error in row {row + 1}")

    def setFilterRows(self, text: str, month_start: int, month_end: int) -> None:
        self.filter_text = text
        self.filter_start_month = month_start
        self.filter_end_month = month_end
        self.filterRows()

    def filterRows(self) -> None:
        """show/hide rows"""
        given_tags = {t.strip() for t in self.filter_text.lower().split(",") if t.strip()}
        for row in range(self.rowCount()):
            tags = {t.strip() for t in self.item(row, 4).text().lower().split(",") if t.strip()}
            try:
                year, month = self.item(row, 6).text().split("-")[:2]
                t = int(year) * 12 + int(month) - 1
            except:
                continue

            if given_tags == given_tags.intersection(tags) and self.filter_start_month <= t <= self.filter_end_month:
                self.showRow(row)
            else:
                self.hideRow(row)

    @Tools.connection
    def copyWallet(self, block: Spending):
        staff = EngineSQL.Cache.get(Staff, where=lambda t: t.salary_id == block.spending_id)[0].id
        wallets = EngineSQL.Cache.get(StaffWallets, where=lambda t: t.staff == staff)
        cb = Application.app.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText("\n".join([w.wallet for w in wallets]), mode=cb.Clipboard)


class TransfersView(HighlightTable.HighlightTable):

    TABLE = Transfers
    COLUMN_NAMES = "action", "from", "to", "amount", "amount tx", "token", "network", "date"
    COLUMN_WIDTH = 100, 300, 300, 200, 200, 100, 100, 200

    def __init__(self, dialog_spending, dialog_income):
        super(TransfersView, self).__init__()
        self.dialog_spending = dialog_spending
        self.dialog_income = dialog_income
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().hide()
        self.loadData()
        for width in enumerate(self.COLUMN_WIDTH):
            self.setColumnWidth(*width)

    @Tools.connection
    def loadData(self):
        self.clear()

        staff_id = {t.id: t for t in EngineSQL.Cache.get(Staff)}
        wallets = {t.wallet.lower(): staff_id[t.staff].name for t in EngineSQL.Cache.get(StaffWallets)}
        wallets.update({w.wallet.lower(): w.name for w in EngineSQL.Cache.get(TransferWallets)})
        transfers = [s for s in EngineSQL.Cache.get(Transfers) if not s.complete]
        staff = {w.wallet.lower(): staff_id[w.staff] for w in EngineSQL.Cache.get(StaffWallets)}

        self.setRowCount(len(transfers))
        self.setColumnCount(len(self.COLUMN_NAMES))
        self.setHorizontalHeaderLabels(self.COLUMN_NAMES)
        self.setSortingEnabled(False)
        self.fillTable()
        for row, tx in enumerate(transfers):
            button = QPushButton("confirm")
            menu = QMenu()
            button.setMenu(menu)
            tx = Convert.copyItem(tx)
            if tx.receiver.lower() in staff:
                user = staff[tx.receiver.lower()]
                tx.receiver = user.name
                menu.addAction("salary", functools.partial(self.dialog_spending.open, tx, user))
            menu.addAction("spending", functools.partial(self.dialog_spending.open, tx))
            menu.addAction("income", functools.partial(self.dialog_income.open, tx=tx))
            menu.addSeparator()
            menu.addAction("copy link", functools.partial(self.copyLink, tx))
            menu.addAction("open in browser", functools.partial(self.openBrowser, tx))
            menu.addSeparator()
            menu.addAction("hide", functools.partial(self.hideTransfer, tx.id))
            if tx.sender.lower() in staff:
                tx.sender = staff[tx.sender.lower()].name
            self.setCellWidget(row, 0, button)
            amount = round(tx.amount, 2)
            for column, item in enumerate(Convert.asTupleView(tx), 1):
                if column in (1, 2) and item.lower() in wallets:
                    self.setItem(row, column, TableItems.TransfersItem(wallets[item.lower()]))
                elif column == 3:
                    self.setItem(row, column, TableItems.TransfersItem(str(amount)))
                else:
                    self.setItem(row, column, TableItems.TransfersItem(item))
        self.setSortingEnabled(True)

    def hideTransfer(self, tx_id: int) -> None:
        reply = QMessageBox.question(self, "confirm", f"transfer ID: {tx_id}", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            EngineSQL.discardTransfer(tx_id)
            self.loadData()

    def copyLink(self, tx: Transfers) -> None:
        cb = Application.app.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(EngineWeb3.getUrl(tx.tx_hash, tx.network), mode=cb.Clipboard)

    def openBrowser(self, tx: Transfers):
        os.system("start chrome " + EngineWeb3.getUrl(tx.tx_hash, tx.network))
