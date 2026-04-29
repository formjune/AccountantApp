import datetime
import functools
try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from PyQt5 import uic
from tools import Tools
from sql import EngineSQL, Convert
from sql.Tables import *
from sql.Enumerators import *


def showMessage(text: str, make_break: bool = True):
    message = QMessageBox()
    message.setText(text)
    message.setWindowTitle("Warning")
    message.exec()
    if make_break:
        raise Tools.IncorrectInput


class Dialog(QWidget):

    SIZE = 1, 1
    UI = ""
    signal = pyqtSignal()

    def __init__(self):
        super(Dialog, self).__init__()
        self.ui = uic.loadUi(f"resources/ui/{self.UI}.ui", self)
        self.setFixedSize(*self.SIZE)
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.btn_run.released.connect(self.run)

    def open(self, *args):
        """open and reload dialog"""
        self.show()
        self.activateWindow()
        self.reloadCombo()

    def reloadCombo(self):
        """reload combo boxes with sql data"""
        pass

    def run(self):
        """upon clicking button"""
        pass

    def finish(self):
        """close window and emit signal"""
        self.close()
        self.signal.emit()


class ConfirmPayment(Dialog):

    SIZE = 401, 221
    UI = "ConfirmPayment"
    index: int = 0

    def __init__(self):
        super(ConfirmPayment, self).__init__()
        self.ui.chb_personal.toggled.connect(self.ui.cmb_users.setEnabled)
        self.ui.chb_fiat.toggled.connect(self.ui.line_tx.setDisabled)

    def open(self, index: int, amount: float) -> None:
        self.index = index
        self.ui.spin_amount.setValue(amount)
        self.line_tx.clear()
        self.line_comment.clear()
        self.ui.chb_personal.setChecked(False)
        self.ui.chb_fiat.setChecked(False)
        self.ui.line_date.setText(datetime.date.today().isoformat())
        Dialog.open(self)

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        users = EngineSQL.Cache.get(Staff, where=lambda s: s.type != StaffTypeEnum.dismissed)
        self.ui.cmb_users.clear()
        for user in users:
            self.ui.cmb_users.addItem(user.name, QVariant(user.id))

    @Tools.connectionWithLock
    def run(self) -> None:
        if self.ui.chb_fiat.isChecked():
            tx = "fiat"
        else:
            tx = self.ui.line_tx.text()
            if not tx:
                showMessage("transaction can't be empty")
        date = self.ui.line_date.text()
        if not date:
            showMessage("enter date")
        if self.ui.chb_personal.isChecked():
            if self.ui.cmb_users.currentIndex() == -1:
                showMessage("select user")
            user = self.ui.cmb_users.currentData()
        else:
            user = -1
        comment = self.ui.line_comment.text()
        amount = self.ui.spin_amount.value()
        EngineSQL.confirmSpending(self.index, tx, amount, comment, date, user)
        self.finish()


class ConfirmTransfer(Dialog):

    UI = "ConfirmTransaction"
    SIZE = 401, 191
    _tx: Transfers
    _user: Staff

    def __init__(self):
        super(ConfirmTransfer, self).__init__()
        self.ui.rdb_salary.toggled.connect(self.ui.cmb_salary.setEnabled)
        self.ui.rdb_spending.toggled.connect(self.ui.cmb_spending.setEnabled)
        self.ui.btn_max.released.connect(self.setMaxAmount)

    def open(self, tx: Transfers, user: Staff = None):
        self._tx = tx
        self._user = user
        if user is None:
            self.ui.line_user.clear()
            self.ui.rdb_spending.setChecked(True)
            self.ui.rdb_salary.setDisabled(True)
        else:
            self.ui.line_user.setText(user.name)
            self.ui.rdb_salary.setChecked(True)
            self.ui.rdb_salary.setEnabled(True)
        self.ui.spin_amount.setMaximum(tx.amount)
        self.ui.spin_amount.setValue(tx.amount)
        self.ui.line_comment.clear()
        Dialog.open(self)

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        self.ui.cmb_salary.clear()
        self.ui.cmb_spending.clear()
        data = EngineSQL.Cache.get(Spending, where=lambda s: s.status == PaymentStatusEnum.unpaid, order=lambda s: s.id)
        onetime_spending = {s.id: s for s in EngineSQL.Cache.get(OneTimeSpending)}
        regular_spending = {s.id: s for s in EngineSQL.Cache.get(RegularSpending)}
        if self._user is not None:
            for item in data:
                if item.spending_type == SpendingTypeEnum.regular and item.spending_id == self._user.salary_id:
                    self.ui.cmb_salary.addItem(item.date.date().isoformat(), QVariant(item.id))
        for item in data:
            try:
                if item.spending_type == SpendingTypeEnum.regular:
                    rs = regular_spending[item.spending_id]
                    purpose = rs.purpose
                    amount = "UPDT" if rs.unpredictable else item.left_amount
                else:
                    purpose = onetime_spending[item.spending_id].purpose
                    amount = item.left_amount
            except KeyError:
                purpose = ""
                amount = item.left_amount
            self.ui.cmb_spending.addItem(f"{item.id}, {amount}, {purpose}", QVariant(item.id))

    @Tools.connectionWithLock
    def run(self):
        if self.ui.rdb_salary.isChecked():
            if self.ui.cmb_salary.currentIndex() == -1:
                showMessage("select salary")
            spending_id = self.ui.cmb_salary.currentData()
        else:
            if self.ui.cmb_spending.currentIndex() == -1:
                showMessage("select spending")
            spending_id = self.ui.cmb_spending.currentData()
        tx_id = self._tx.id
        comment = self.ui.line_comment.text()
        amount = self.ui.spin_amount.value()
        EngineSQL.confirmTransfer(tx_id, spending_id, amount, comment)
        self.finish()

    def setMaxAmount(self):
        self.ui.spin_amount.setValue(self.ui.spin_amount.maximum())


class CreateSpending(Dialog):

    SIZE = 401, 311
    UI = "CreateSpending"

    def __init__(self):
        super(CreateSpending, self).__init__()
        self.ui.cmb_type.currentIndexChanged.connect(self.toggle)
        self.ui.menu_tags = QMenu()
        self.ui.btn_tags.setMenu(self.ui.menu_tags)
        self.toggle(0)

    def open(self, *args):
        self.ui.cmb_type.setCurrentIndex(0)
        self.ui.line_purpose.clear()
        self.ui.line_date.setText(datetime.date.today().isoformat())
        self.ui.line_period.setText("0/0/0/1")
        self.ui.spin_amount.setValue(0)
        self.ui.spin_repeat.setValue(1)
        self.ui.chb_updt.setChecked(False)
        self.ui.line_tags.clear()
        Dialog.open(self)

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        self.ui.cmb_regular.clear()
        self.ui.cmb_onetime.clear()
        for item in EngineSQL.Cache.get(OneTimeSpending):
            self.ui.cmb_onetime.addItem(item.purpose, QVariant(item.id))
        for item in EngineSQL.Cache.get(RegularSpending):
            self.ui.cmb_regular.addItem(item.purpose, QVariant(item.id))
        self.ui.menu_tags.clear()
        for item in EngineSQL.Cache.get(Tags):
            self.ui.menu_tags.addAction(item.name, functools.partial(self.addTag, item.name))

    @Tools.connectionWithLock
    def run(self):
        index = self.ui.cmb_type.currentIndex()
        date = self.ui.line_date.text()
        amount = self.ui.spin_amount.value()
        if index in (0, 2):
            spending_type = SpendingTypeEnum.regular
        else:
            spending_type = SpendingTypeEnum.onetime
        tags = Convert.encodeTags(self.ui.line_tags.text())
        updt = self.ui.chb_updt.isChecked()
        if index in (0, 1):
            purpose = self.ui.line_purpose.text()
            period = self.ui.line_period.text()
            repeat = self.ui.spin_repeat.value()
            EngineSQL.createSpending(spending_type, date, amount, amount, tags, None, repeat, purpose, period,
                                     unpredictable=updt)
        elif index == 2:
            if self.ui.cmb_regular.currentIndex() == -1:
                showMessage("select regular spending")
            spending_id = self.ui.cmb_regular.currentData()
            EngineSQL.createSpending(spending_type, date, amount, amount, tags, spending_id, unpredictable=updt)
        else:
            if self.ui.cmb_onetime.currentIndex() == -1:
                showMessage("select onetime spending")
            spending_id = self.ui.cmb_onetime.currentData()
            EngineSQL.createSpending(spending_type, date, amount, amount, tags, spending_id, unpredictable=updt)
        self.finish()

    def addTag(self, tag):
        text = self.ui.line_tags.text()
        if text:
            self.ui.line_tags.setText(f"{text}, {tag}")
        else:
            self.ui.line_tags.setText(tag)

    def toggle(self, index):
        self.ui.cmb_regular.setEnabled(index == 2)
        self.ui.cmb_onetime.setEnabled(index == 3)
        self.ui.line_purpose.setEnabled(index in (0, 1))
        self.ui.line_period.setEnabled(index == 0)
        self.ui.spin_repeat.setEnabled(index == 0)


class CreateIncome(Dialog):

    SIZE = 401, 341
    UI = "CreateIncome"
    _tx = -1

    def __init__(self):
        super(CreateIncome, self).__init__()
        self.ui.spin_commission.valueChanged.connect(self.percentChanged)
        self.ui.spin_amount.valueChanged.connect(self.percentChanged)
        self.ui.rdb_type_exist.toggled.connect(self.incomeTypeChanged)
        self.percentChanged()
        self.incomeTypeChanged()

    def open(self, *args, tx=None):
        if tx is None:
            self.ui.line_hash.clear()
            self.ui.spin_amount.setValue(0)
            self.ui.line_date.setText(datetime.date.today().isoformat())
            self._tx = -1
        else:
            self.ui.line_hash.setText(tx.tx_hash)
            self.ui.spin_amount.setValue(tx.amount)
            self.ui.line_date.setText(tx.date.isoformat())
            self._tx = tx.id
        self.ui.spin_commission.setValue(0)
        self.ui.spin_tokens.setValue(0)
        self.ui.line_name.clear()
        self.ui.line_comment.clear()
        self.ui.rdb_type_exist.setChecked(True)
        Dialog.open(self)

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        self.ui.cmb_type.clear()
        for income in EngineSQL.Cache.get(IncomeType):
            self.ui.cmb_type.addItem(income.name, QVariant(income.id))
        self.ui.cmb_recipient.clear()
        for pr in EngineSQL.Cache.get(PromotionSource):
            self.ui.cmb_recipient.addItem(pr.name, QVariant(pr.id))

    @Tools.connectionWithLock
    def run(self):
        if self.rdb_type_exist.isChecked():
            if self.ui.cmb_type.currentIndex() == -1:
                showMessage("select income type")
            income_type = self.ui.cmb_type.currentData()
        else:
            income_type = self.ui.line_type.text()
            if not income_type:
                showMessage("give a name to income type")
        name = self.ui.line_name.text()
        if not name:
            showMessage("enter name")
        amount = self.ui.spin_amount.value()
        commission = self.ui.spin_commission.value()
        tokens = self.ui.spin_tokens.value()
        date = self.ui.line_date.text()
        comment = self.ui.line_comment.text()
        if commission:
            if self.ui.cmb_recipient.currentIndex() == -1:
                showMessage("select recipient")
            recipient = self.ui.cmb_recipient.currentData()
            EngineSQL.createIncome(name, income_type, amount, commission, tokens, date, comment, self._tx, recipient)
        else:
            EngineSQL.createIncome(name, income_type, amount, commission, tokens, date, comment, self._tx)
        self.finish()

    def percentChanged(self):
        percent = self.ui.spin_commission.value()
        amount = self.ui.spin_amount.value()
        self.ui.line_comission.setText(f"{amount * percent / 100:.2f}")
        self.ui.cmb_recipient.setEnabled(bool(percent))

    def incomeTypeChanged(self):
        self.ui.cmb_type.setEnabled(self.ui.rdb_type_exist.isChecked())
        self.ui.line_type.setEnabled(self.ui.rdb_type_new.isChecked())


class CreateStaff(Dialog):

    SIZE = 401, 251
    UI = "CreateStaff"

    def open(self, *args):
        self.ui.line_name.clear()
        self.ui.line_position.clear()
        self.ui.line_hire.setText(datetime.date.today().isoformat())
        self.ui.line_wallet.clear()
        self.ui.line_comment.clear()
        self.ui.spin_salary.setValue(0)
        self.show()
        self.activateWindow()

    @Tools.connectionWithLock
    def run(self):
        name = self.ui.line_name.text()
        if not name:
            showMessage("enter name")
        position = self.ui.line_position.text()
        if not position:
            showMessage("enter position")
        wallet = self.ui.line_wallet.text()
        hire_date = self.ui.line_hire.text()
        comment = self.ui.line_comment.text()
        salary = self.ui.spin_salary.value()
        if self.ui.rdb_insource.isChecked():
            staff_type = StaffTypeEnum.insource
            unpredictable = False
        elif self.ui.rdb_outsource.isChecked():
            staff_type = StaffTypeEnum.outsource
            unpredictable = True
        else:
            staff_type = StaffTypeEnum.outsource
            unpredictable = False
        EngineSQL.createStaff(name, position, staff_type, wallet, salary, hire_date, unpredictable, comment)
        self.finish()


class DismissStaff(Dialog):

    SIZE = 401, 71
    UI = "DismissStaff"

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        users = EngineSQL.Cache.get(Staff, where=lambda s: s.type != StaffTypeEnum.dismissed)
        self.ui.cmb_users.clear()
        for user in users:
            self.ui.cmb_users.addItem(user.name, QVariant(user.id))

    @Tools.connectionWithLock
    def run(self):
        if self.ui. cmb_users.currentIndex() == -1:
            showMessage("select staff member")
        user_id = self.ui.cmb_users.currentData()
        EngineSQL.dismissStaff(user_id)
        self.finish()


class SetNewSalary(Dialog):

    SIZE = 401, 101
    UI = "SetNewSalary"

    def open(self, *args):
        # устанавливаем дату заново перед каждым показом
        self.ui.date_effective.setDate(QDate.currentDate())
        super().open(*args)


    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        users = EngineSQL.Cache.get(Staff, where=lambda s: s.type != StaffTypeEnum.dismissed)
        self.ui.cmb_users.clear()
        for user in users:
            self.ui.cmb_users.addItem(user.name, QVariant(user.id))

    @Tools.connectionWithLock
    def run(self):
        if self.ui.cmb_users.currentIndex() == -1:
            showMessage("select staff member")
        user_id = self.ui.cmb_users.currentData()
        salary = self.ui.spin_amount.value()
        EngineSQL.setNewSalary(user_id, salary)
        self.finish()


class CreateCommission(Dialog):
    SIZE = 401, 221
    UI = "CreateCommission"

    def __init__(self):
        super(CreateCommission, self).__init__()
        self.ui.rdb_percent.toggled.connect(self.ui.spin_commission.setEnabled)
        self.ui.rdb_percent.toggled.connect(self.ui.spin_amount.setDisabled)
        self.ui.spin_amount.valueChanged.connect(self.recalculate)
        self.ui.spin_commission.valueChanged.connect(self.recalculate)
        self.ui.cmb_income.currentIndexChanged.connect(self.recalculate)
        self.recalculate()

    def open(self, *args):
        self.ui.rdb_percent.setChecked(True)
        self.ui.line_date.setText(datetime.date.today().isoformat())
        self.ui.line_comment.clear()
        Dialog.open(self)

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        self.ui.cmb_income.clear()
        income_data = EngineSQL.Cache.get(Income)
        for item in income_data:
            self.ui.cmb_income.addItem(item.source, QVariant((item.id, item.amount)))
        self.ui.cmb_recipient.clear()
        recipients = EngineSQL.Cache.get(PromotionSource)
        for item in recipients:
            self.ui.cmb_recipient.addItem(item.name, QVariant(item.id))

    @Tools.connectionWithLock
    def run(self) -> None:
        if self.ui.cmb_income.currentIndex() == -1:
            showMessage("select income")
        if self.ui.cmb_recipient.currentIndex() == -1:
            showMessage("select recipient")
        income_id, income_amount = self.ui.cmb_income.currentData()
        commission, amount = self.getValues(income_amount)
        recipient = self.ui.cmb_recipient.currentData()
        date = self.ui.line_date.text()
        comment = self.ui.line_comment.text()
        EngineSQL.createCommission(income_id, recipient, commission, amount, date, comment)
        self.finish()

    def recalculate(self) -> None:
        """recalculate commission and amount"""
        if self.ui.cmb_income.currentIndex() == -1:
            self.ui.line_info.clear()
            return
        commission, amount = self.getValues(self.ui.cmb_income.currentData()[1])
        self.ui.line_info.setText(f"{round(amount, 2)}, {round(commission, 2)}%")

    def getValues(self, income_amount: float) -> tuple:
        """get commission and amount"""
        if self.ui.rdb_amount.isChecked():
            amount = self.ui.spin_amount.value()
            commission = amount / income_amount * 100
        else:
            commission = self.ui.spin_commission.value()
            amount = income_amount * commission / 100
        return commission, amount


class CreatePersonalSpending(Dialog):
    SIZE = 401, 191
    UI = "CreatePersonalSpending"

    def open(self, *args):
        self.ui.spin_amount.setValue(0)
        self.ui.line_date.setText(datetime.date.today().isoformat())
        self.ui.line_comment.clear()
        Dialog.open(self)

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        users = EngineSQL.Cache.get(Staff, where=lambda s: s.type != StaffTypeEnum.dismissed)
        self.ui.cmb_users.clear()
        for user in users:
            self.ui.cmb_users.addItem(user.name, QVariant(user.id))

        self.ui.cmb_spending.clear()
        data = EngineSQL.Cache.get(Spending, where=lambda s: s.status == PaymentStatusEnum.unpaid)
        onetime_spending = {s.id: s for s in EngineSQL.Cache.get(OneTimeSpending)}
        regular_spending = {s.id: s for s in EngineSQL.Cache.get(RegularSpending)}
        for item in data:
            try:
                if item.spending_type == SpendingTypeEnum.regular:
                    purpose = regular_spending[item.spending_id].purpose
                else:
                    purpose = onetime_spending[item.spending_id].purpose
            except KeyError:
                purpose = ""
            self.ui.cmb_spending.addItem(f"{item.id}, {purpose}", QVariant(item.id))

    @Tools.connectionWithLock
    def run(self) -> None:
        if self.ui.cmb_users.currentIndex() == -1:
            showMessage("select staff")
        user_id = self.ui.cmb_users.currentData()
        if self.ui.cmb_spending.currentIndex() == -1:
            showMessage("select spending")
        spending_id = self.ui.cmb_spending.currentData()
        amount = self.ui.spin_amount.value()
        date = self.ui.line_date.text()
        comment = self.ui.line_comment.text()
        EngineSQL.confirmSpending(spending_id, "personal", amount, comment, date, user_id)
        self.finish()


class CreateReward(Dialog):

    SIZE = 401, 131
    UI = "CreateReward"

    def __init__(self):
        super(CreateReward, self).__init__()
        self._amount = 0
        self.ui.rdb_amount.toggled.connect(self.recalculateAmount)
        self.ui.cmb_staff.currentIndexChanged.connect(self.recalculateAmount)
        self.ui.spin_value.valueChanged.connect(self.recalculateAmount)

    def open(self, *args):
        self.ui.rdb_amount.setChecked(True)
        self.ui.spin_value.setValue(0)
        self.ui.line_date.setText(datetime.date.today().isoformat())
        self.ui.line_result.clear()
        Dialog.open(self)

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        staff = EngineSQL.Cache.get(Staff)
        salaries = {s.id: s for s in EngineSQL.Cache.get(RegularSpending)}
        self.ui.cmb_staff.clear()
        for user in staff:
            amount = salaries[user.salary_id].amount
            self.ui.cmb_staff.addItem(user.name, QVariant((user.id, amount)))

    @Tools.connectionWithLock
    def run(self):
        if self.ui.cmb_staff.currentIndex() == -1:
            showMessage("select staff")
        user_id = self.ui.cmb_staff.currentData()[0]
        date = datetime.datetime.fromisoformat(self.ui.line_date.text()).date()
        if not EngineSQL.createReward(user_id, self._amount, date):
            showMessage("select another date")
        self.finish()

    def recalculateAmount(self):
        if self.ui.cmb_staff.currentIndex() == -1:
            self.ui.line_result.clear()
            return
        if self.ui.rdb_amount.isChecked():
            self._amount = self.ui.spin_value.value()
        else:
            self._amount = self.ui.cmb_staff.currentData()[1] * self.ui.spin_value.value() / 100
        self.ui.line_result.setText(f"{self._amount:.2f}")


class CreateStaffWallet(Dialog):
    SIZE = 401, 131
    UI = "CreateStaffWallet"

    def open(self, *args):
        self.ui.line_wallet.clear()
        self.ui.line_comment.clear()
        Dialog.open(self)

    @Tools.connection
    def reloadCombo(self):
        if not self.isVisible():
            return
        self.ui.cmb_staff.clear()
        for user in EngineSQL.Cache.get(Staff, where=lambda u: u.type != StaffTypeEnum.dismissed):
            self.ui.cmb_staff.addItem(user.name, QVariant(user.id))

    @Tools.connectionWithLock
    def run(self):
        if self.ui.cmb_staff.currentIndex() == -1:
            showMessage("select staff")
        wallet = self.ui.line_wallet.text()
        if not wallet:
            showMessage("enter wallet")
        user_id = self.ui.cmb_staff.currentData()
        comment = self.ui.line_comment.text()
        EngineSQL.createStaffWallet(user_id, wallet, comment)
        self.finish()


class MonthlyReportDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monthly Report for Open Loot")
        self.resize(700, 500)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Верхняя панель выбора месяца
        form_layout = QHBoxLayout()
        self.cmb_year = QComboBox()
        self.cmb_month = QComboBox()
        for y in range(2024, 2031):
            self.cmb_year.addItem(str(y))
        for m in range(1, 13):
            self.cmb_month.addItem(str(m))

        form_layout.addWidget(QLabel("Year:"))
        form_layout.addWidget(self.cmb_year)
        form_layout.addWidget(QLabel("Month:"))
        form_layout.addWidget(self.cmb_month)

        btn_load = QPushButton("Load Transactions")
        btn_load.clicked.connect(self.loadTransactions)
        form_layout.addWidget(btn_load)

        main_layout.addLayout(form_layout)

        # Таблица для просмотра/редактирования
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Direction", "Date", "Counterparty", "Amount", "Hash"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # чтобы не меняли числа вручную
        main_layout.addWidget(self.table)

        # Кнопка удаления
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self.removeSelectedRows)
        main_layout.addWidget(btn_remove)

        # Кнопка "Сформировать текст отчёта"
        btn_generate = QPushButton("Generate Report")
        btn_generate.clicked.connect(self.generateReport)
        main_layout.addWidget(btn_generate)

        # Поле вывода
        self.txt_report = QTextEdit()
        main_layout.addWidget(self.txt_report)

        # Кнопка "Сохранить в файл"
        btn_save = QPushButton("Save to file...")
        btn_save.clicked.connect(self.saveToFile)
        main_layout.addWidget(btn_save)

        # Список всех транзакций (храним в памяти)
        self.all_transactions = []

    @Tools.connection
    def loadTransactions(self, *args):
        """Загружаем список incoming/outgoing за указанные год-месяц в таблицу."""
        print(args)
        self.all_transactions.clear()
        self.table.setRowCount(0)

        year = int(self.cmb_year.currentText())
        month = int(self.cmb_month.currentText())

        incoming, outgoing = EngineSQL.getMonthlyIncomingOutgoing(year, month)
        # incoming -> direction='IN'
        for tx in incoming:
            self.all_transactions.append( (tx.id, 'IN', tx.date, tx.sender, tx.amount_tx, tx.tx_hash) )
        # outgoing -> direction='OUT'
        for tx in outgoing:
            self.all_transactions.append( (tx.id, 'OUT', tx.date, tx.receiver, tx.amount_tx, tx.tx_hash) )

        # Заполним таблицу
        self.table.setRowCount(len(self.all_transactions))
        for row, (tx_id, direction, dt, cp, amt, hsh) in enumerate(self.all_transactions):
            self.table.setItem(row, 0, QTableWidgetItem(str(tx_id)))
            self.table.setItem(row, 1, QTableWidgetItem(direction))
            self.table.setItem(row, 2, QTableWidgetItem(dt.strftime("%Y-%m-%d")))
            self.table.setItem(row, 3, QTableWidgetItem(cp))
            self.table.setItem(row, 4, QTableWidgetItem(f"{amt:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(hsh))

        # После загрузки таблица пустой текст отчёта
        self.txt_report.clear()

    def removeSelectedRows(self):
        """Удаляем выбранные строки из таблицы self.table и из self.all_transactions."""
        selected_rows = list({i.row() for i in self.table.selectedIndexes()})
        selected_rows.sort(reverse=True)
        for row in selected_rows:
            if row < 0 or row >= len(self.all_transactions):
                continue
            # удаляем из списка
            del self.all_transactions[row]
            # удаляем из таблицы
            self.table.removeRow(row)

    def generateReport(self):
        """Формируем финальный текст отчёта, исключая удалённые транзакции."""
        # Собираем ID-шники исключаемых транзакций из all_in_out, которые вообще не попали в таблицу.
        # Но проще наоборот: имеем полный список incoming/outgoing, а user удалил некие строки = exclude.
        # Однако в примере мы начинаем с исходного массива, и "removeSelectedRows" их реально вырезает.
        # Тогда, чтобы получить set exclude_ids, нам нужно сравнить с initialIncoming, initialOutgoing?
        # Или мы, наоборот, просто соберём ID, которые остались — и всё. Но нам нужно ID исключённых...
        #
        # Проще всего можно сделать так: сначала получим полный список ID (исходный) -> full_ids,
        # затем смотрим, какие у нас остались -> kept_ids. И тогда exclude = full_ids - kept_ids.

        # Но в данном демонстрационном фрагменте удобнее прямо вызвать makeMonthlyReport,
        # передавая туда те транзакции, которые ОСТАЛИСЬ (kept). So, compile exclude из diff.
        # Здесь, чтобы не усложнять, соберём те, что остались, затем всё равно нужны "year, month".
        # Let's do it.

        year = int(self.cmb_year.currentText())
        month = int(self.cmb_month.currentText())

        # Возьмём заново все транзакции (incoming, outgoing) и посмотрим, какие id там вообще бывают
        all_in, all_out = EngineSQL.getMonthlyIncomingOutgoing(year, month)
        full_ids = {tx.id for tx in all_in} | {tx.id for tx in all_out}

        # Соберём id, которые остались в таблице
        kept_ids = set()
        for (tx_id, _, _, _, _, _) in self.all_transactions:
            kept_ids.add(tx_id)

        # всё, чего нет в kept, считаем исключённым
        exclude = full_ids - kept_ids

        # Теперь вызываем нашу обновлённую makeMonthlyReport
        text_report = EngineSQL.makeMonthlyReport(year, month, exclude_ids=exclude)
        self.txt_report.setPlainText(text_report)

    def saveToFile(self):
        text = self.txt_report.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Warning", "Report is empty. Generate it first.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save Report", "report.txt", "Text Files (*.txt)")
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "Saved", f"Report saved to {filename}")


class SalaryHistory(Dialog):
    SIZE = 500, 500
    UI   = "SalaryHistory"

    def __init__(self):
        self.btn_run = QPushButton()          
        super().__init__()                    
        self.btn_run.hide() 
        self.ui.cmb_users.currentIndexChanged.connect(self.loadHistory)
        self.ui.btn_edit_date.clicked.connect(self.editDate)


    @Tools.connection
    def reloadCombo(self):
        staff = EngineSQL.Cache.get(Staff)
        self.ui.cmb_users.clear()
        for s in staff:
            self.ui.cmb_users.addItem(s.name, QVariant(s.id))

    @Tools.connection
    def loadHistory(self, *_):
        staff_id = self.ui.cmb_users.currentData()
        model = QStandardItemModel(self)
        model.setHorizontalHeaderLabels(["id", "amount", "changed_at", "comment"])
        for rec in EngineSQL.getSalaryHistory(staff_id):           # новая обёртка
            row = [QStandardItem(str(rec.id)),
                   QStandardItem(f"{rec.amount:.2f}"),
                   QStandardItem(rec.changed_at.date().isoformat()),
                   QStandardItem(rec.comment or "")]
            model.appendRow(row)
        self.ui.tbl_history.setModel(model)

    @Tools.connectionWithLock
    def editDate(self, *_):
        sel = self.ui.tbl_history.selectionModel().selectedRows()
        if not sel:
            showMessage("select history row")
            return
        hist_id = int(sel[0].data())
        old_dt  = datetime.datetime.fromisoformat(sel[0].siblingAtColumn(2).data())
        new_qd, ok = QInputDialog.getText(
            self, "Edit date", "YYYY-MM-DD:", text=old_dt.date().isoformat())
        if not ok:
            return
        try:
            new_dt = datetime.date.fromisoformat(new_qd)
            EngineSQL.updateSalaryChangeDate(hist_id, new_dt)
            self.loadHistory()
        except ValueError as e:
            showMessage(str(e))
