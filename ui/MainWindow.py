import datetime
import functools
import calendar

from sqlalchemy import extract
from sql.EngineSQL import Cache

try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from PyQt5 import uic
from tools import Tools
from ui import EditorTable, ViewerTable, Dialogs, DockWidget, ReportTable
from sql import EngineSQL, Tables, Enumerators


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        EngineSQL.createTables()
        EngineSQL.startTask()
        self.ui = uic.loadUi("resources/ui/MainWindow.ui", self)

        # dialogs
        self.create_reward = Dialogs.CreateReward()
        self.confirm_spending = Dialogs.ConfirmPayment()
        self.confirm_transfer = Dialogs.ConfirmTransfer()
        self.dialog_spending = Dialogs.CreateSpending()
        self.dialog_income = Dialogs.CreateIncome()
        self.dialog_staff = Dialogs.CreateStaff()
        self.dialog_wallet = Dialogs.CreateStaffWallet()
        self.dialog_staff_dismiss = Dialogs.DismissStaff()
        self.dialog_salary = Dialogs.SetNewSalary()
        self.dialog_commission = Dialogs.CreateCommission()
        self.dialog_personal_spending = Dialogs.CreatePersonalSpending()
        self.dlg_salary_history = Dialogs.SalaryHistory()
        self.dialogs = (
            self.confirm_spending, self.confirm_transfer, self.dialog_spending, self.dialog_income, self.dialog_staff,
            self.dialog_staff_dismiss, self.dialog_salary, self.dialog_commission, self.dialog_personal_spending,
            self.create_reward, self.dialog_wallet, self.dlg_salary_history
        )
        self.monthly_report_dialog = Dialogs.MonthlyReportDialog()

        # view table
        self.transfers_view = ViewerTable.TransfersView(self.confirm_transfer, self.dialog_income)
        self.spending_view = ViewerTable.SpendingView(self.confirm_spending)
        self.ui.wdg_transfer.layout().addWidget(self.transfers_view)
        self.ui.wdg_spending.layout().addWidget(self.spending_view)

        self.win_report = ReportTable.IncomeReport()

        # splitter = QSplitter(Qt.Vertical)# , self.ui.wdg_tables)
        # splitter.addWidget(self.spending_view)
        # splitter.addWidget(self.transfers_view)
        # splitter.show()
        #
        # self.sp = splitter

        # self.centralWidget().layout().addWidget(self.ui.spending_view, 1, 0, 1, 7)

        # edit table
        self.reward_e = EditorTable.RewardEdit()
        self.income_type_e = EditorTable.IncomeTypeEdit()
        self.income_e = EditorTable.IncomeEdit()
        self.promotion_source_e = EditorTable.PromotionSourceEdit()
        self.promotion_commission_e = EditorTable.PromotionCommissionEdit()
        self.department_e = EditorTable.DepartmentEdit()
        self.staff_e = EditorTable.StaffEdit()
        self.spending_e = EditorTable.SpendingEdit()
        self.personal_spending_e = EditorTable.PersonalSpendingEdit()
        self.regular_spending_e = EditorTable.RegularSpendingEdit()
        self.onetime_spending_e = EditorTable.OneTimeSpendingEdit()
        self.tags_e = EditorTable.TagsEdit()
        self.transfers_e = EditorTable.TransfersEdit()
        self.transfer_pair_e = EditorTable.TransferWalletsEdit()
        self.staff_wallets_e = EditorTable.StaffWalletsEdit()
        self.off_days_percent_e = EditorTable.OffDaysPercentEdit()
        self.date_ranges_e = EditorTable.DateRangesEdit()
        self.edit_tables = (
            self.income_type_e, self.income_e, self.promotion_source_e, self.promotion_commission_e, self.staff_e,
            self.spending_e, self.personal_spending_e, self.regular_spending_e,  self.onetime_spending_e, self.tags_e,
            self.transfers_e, self.transfer_pair_e, self.department_e, self.off_days_percent_e, self.date_ranges_e,
            self.reward_e, self.staff_wallets_e
        )

        # dock edit tables
        self.reward_ed = DockWidget.Dock(self.reward_e, "Reward")
        self.spending_ed = DockWidget.Dock(self.spending_e, "Spending")
        self.staff_wallets_ed = DockWidget.Dock(self.staff_wallets_e, "Staff Wallets")
        self.regular_spending_ed = DockWidget.Dock(self.regular_spending_e, "Regular Spending")
        self.onetime_spending_ed = DockWidget.Dock(self.onetime_spending_e, "One Time Spending")
        self.personal_spending_ed = DockWidget.Dock(self.personal_spending_e, "Personal Spending")
        self.income_type_ed = DockWidget.Dock(self.income_type_e, "Income Type")
        self.income_ed = DockWidget.Dock(self.income_e, "Income")
        self.promotion_source_ed = DockWidget.Dock(self.promotion_source_e, "Promotion Source")
        self.promotion_commission_ed = DockWidget.Dock(self.promotion_commission_e, "Promotion Commission")
        self.department_ed = DockWidget.Dock(self.department_e, "Departments")
        self.staff_ed = DockWidget.Dock(self.staff_e, "Staff")
        self.tags_ed = DockWidget.Dock(self.tags_e, "Tags")
        self.transfers_ed = DockWidget.Dock(self.transfers_e, "Transfers All")
        self.transfer_pair_ed = DockWidget.Dock(self.transfer_pair_e, "Transfer Wallets")
        self.off_days_percent_ed = DockWidget.Dock(self.off_days_percent_e, "Off-Days Percent")
        self.date_ranges_ed = DockWidget.Dock(self.date_ranges_e, "Date Ranges")
        #self.transfers_vd = DockWidget.TransferDock(self.transfers_view)

        self.addDockWidget(Qt.RightDockWidgetArea, self.income_ed)
        self.tabifyDockWidget(self.income_ed, self.income_type_ed)
        self.tabifyDockWidget(self.income_ed, self.promotion_source_ed)
        self.tabifyDockWidget(self.income_ed, self.promotion_commission_ed)
        self.tabifyDockWidget(self.income_ed, self.spending_ed)
        self.tabifyDockWidget(self.income_ed, self.regular_spending_ed)
        self.tabifyDockWidget(self.income_ed, self.onetime_spending_ed)
        self.tabifyDockWidget(self.income_ed, self.personal_spending_ed)
        self.tabifyDockWidget(self.income_ed, self.reward_ed)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.staff_ed)
        self.tabifyDockWidget(self.staff_ed, self.department_ed)
        self.tabifyDockWidget(self.staff_ed, self.tags_ed)
        self.tabifyDockWidget(self.staff_ed, self.staff_wallets_ed)
        self.tabifyDockWidget(self.staff_ed, self.transfers_ed)
        self.tabifyDockWidget(self.staff_ed, self.transfer_pair_ed)
        self.tabifyDockWidget(self.staff_ed, self.off_days_percent_ed)
        self.tabifyDockWidget(self.staff_ed, self.date_ranges_ed)
        #self.tabifyDockWidget(self.staff_ed, self.transfers_vd)

        # # signals
        self.ui.action_add_staff_wallet.triggered.connect(self.dialog_wallet.open)
        self.ui.action_add_reward.triggered.connect(self.create_reward.open)
        self.ui.action_add_spending.triggered.connect(self.dialog_spending.open)
        self.ui.action_add_personal_spending.triggered.connect(self.dialog_personal_spending.open)
        self.ui.action_add_income.triggered.connect(self.dialog_income.open)
        self.ui.action_add_commission.triggered.connect(self.dialog_commission.open)
        self.ui.action_add_staff.triggered.connect(self.dialog_staff.open)
        self.ui.action_dismiss_staff.triggered.connect(self.dialog_staff_dismiss.open)
        self.ui.action_set_new_salary.triggered.connect(self.dialog_salary.open)
        self.ui.action_budget.triggered.connect(self.updateBudget)
        self.ui.action_reload_dialogs.triggered.connect(self.reloadDialogs)

        self.ui.action_reward.triggered.connect(self.reward_ed.show)
        self.ui.action_spending.triggered.connect(self.spending_ed.show)
        self.ui.action_personal_spending.triggered.connect(self.personal_spending_ed.show)
        self.ui.action_regular_spending.triggered.connect(self.regular_spending_ed.show)
        self.ui.action_onetime_spending.triggered.connect(self.onetime_spending_ed.show)
        self.ui.action_income.triggered.connect(self.income_ed.show)
        self.ui.action_income_type.triggered.connect(self.income_type_ed.show)
        self.ui.action_promotion_source.triggered.connect(self.promotion_source_ed.show)
        self.ui.action_promotion_commission.triggered.connect(self.promotion_commission_ed.show)
        self.ui.action_department.triggered.connect(self.department_ed.show)
        self.ui.action_staff.triggered.connect(self.staff_ed.show)
        self.ui.action_off_days_percent.triggered.connect(self.off_days_percent_ed.show)
        self.ui.action_date_ranges.triggered.connect(self.date_ranges_ed.show)
        self.ui.action_tags.triggered.connect(self.tags_ed.show)
        self.ui.action_transfers_all.triggered.connect(self.transfers_ed.show)
        # self.ui.action_transfers.triggered.connect(self.transfers_vd.show)
        self.ui.action_transfer_wallets.triggered.connect(self.transfer_pair_ed.show)
        self.ui.action_staff_wallets.triggered.connect(self.staff_wallets_ed.show)

        self.ui.action_commit.triggered.connect(self.commit)
        self.ui.action_load_edit.triggered.connect(self.reloadTables)
        self.ui.action_find_transfers.triggered.connect(self.createTransfers)
        self.ui.action_create_repeat_spending.triggered.connect(self.createRepeatSpending)
        self.ui.action_delete_transfer_duplicates.triggered.connect(self.deleteTransferDuplicates)
        self.ui.action_report_unpaid_spending.triggered.connect(self.createReport)
        self.ui.action_report_unpaid_salaries.triggered.connect(self.createReportSalaries)
        self.ui.action_report_user_income.triggered.connect(self.win_report.open)
        self.ui.action_auto_close_transactions.triggered.connect(self.autoCloseTransfers)
        self.ui.action_auto_distribute_salaries.triggered.connect(self.autoDistributeSalaries)
        self.ui.action_monthly_report.triggered.connect(self.openMonthlyReport)

        self.action_salary_history.triggered.connect(self.dlg_salary_history.open)



        for dialog in self.dialogs:
            dialog.signal.connect(self.reloadTables)
        self.dialog_personal_spending.ui.btn_spending.released.connect(self.dialog_spending.open)
        self.confirm_transfer.ui.btn_add.released.connect(self.dialog_spending.open)
        self.ui.line_tags.returnPressed.connect(self.filterRows)

        # post
        self.menu_tags = QMenu()
        self.ui.btn_tags.setMenu(self.menu_tags)
        self.ui.btn_date.released.connect(self.filterRows)
        today = datetime.date.today()
        today = f"{today.year}-{today.month}"
        self.ui.line_date_start.setText(today)
        self.ui.line_date_end.setText(today)
        self.ui.line_date.setText(str(datetime.date.today()))
        self.spending_view.loadData()
        self.displayBudget()
        self.loadTags()

    def commit(self) -> None:
        for table in self.edit_tables:
            table.dumpData()
        self.reloadDialogs()
        for table in filter(lambda t: t.is_loaded, self.edit_tables):
            table.loadContext()
        self.spending_view.loadData()

    def reloadTables(self) -> None:
        """reload tables after dialogs confirmation"""
        EngineSQL.Cache.clear()
        for table in filter(lambda t: t.is_loaded, self.edit_tables):
            table.loadData()
        self.spending_view.loadData()
        self.transfers_view.loadData()
        self.reloadDialogs()

    def reloadDialogs(self) -> None:
        """reload all combos for dialogs"""
        for dialog in self.dialogs:
            dialog.reloadCombo()

    def openMonthlyReport(self):
        # если не создавали в конструкторе, то сделаем:
        # if self.monthly_report_dialog is None:
        #     self.monthly_report_dialog = MonthlyReportDialog()

        self.monthly_report_dialog.show()
        self.monthly_report_dialog.raise_()
        self.monthly_report_dialog.activateWindow()

    @Tools.connection
    def createTransfers(self, *args) -> None:
        count = EngineSQL.createTransfers()
        if count:
            Dialogs.showMessage(f"{count} new transactions added", False)
            self.reloadTables()
        else:
            Dialogs.showMessage("no new transactions", False)

    @Tools.connection
    def createRepeatSpending(self, *args) -> None:
        EngineSQL.repeatSpending()
        self.reloadTables()

    @Tools.connection
    def updateBudget(self, *args) -> None:
        self.displayBudget(EngineSQL.updateBudget())

    @Tools.connection
    def displayBudget(self, budget=None) -> None:
        if budget is None:
            budget = EngineSQL.getBudget()
        budget = round(budget, 2)
        if budget >= 0:
            self.ui.line_budget.setText(str(budget))
            self.ui.line_budget.setStyleSheet("color: green; background-color: transparent;")
        else:
            self.ui.line_budget.setText(str(budget))
            self.ui.line_budget.setStyleSheet("color: red; background-color: transparent;")

    @Tools.connection
    def deleteTransferDuplicates(self, *args):
        tx_count = EngineSQL.deleteTransferDuplicates()
        Dialogs.showMessage(f"deleted {tx_count} transfer duplicates", False)
        self.reloadTables()

    @Tools.connection
    def loadTags(self) -> None:
        """load list of tags"""
        self.menu_tags.clear()
        for item in EngineSQL.Cache.get(Tables.Tags, order=lambda t: t.name, no_cache=True):
            self.ui.menu_tags.addAction(item.name, functools.partial(self.addTag, item.name))
        self.filterRows()

    def addTag(self, tag) -> None:
        """add tag to filters"""
        text = self.ui.line_tags.text()
        if text:
            self.ui.line_tags.setText(f"{text}, {tag}")
        else:
            self.ui.line_tags.setText(tag)
        self.filterRows()

    @Tools.unsafe
    def filterRows(self, *args) -> None:
        """filter rows in view table"""
        date_start = self.ui.line_date_start.text()
        year, month = date_start.split("-")
        month_start = int(year) * 12 + int(month) - 1

        date_end = self.ui.line_date_end.text()
        year, month = date_end.split("-")
        month_end = int(year) * 12 + int(month) - 1

        self.spending_view.setFilterRows(self.ui.line_tags.text(), month_start, month_end)

    @Tools.connectionWithLock
    def createReport(self, *args):
        spending = Cache.get(Tables.Spending, where=lambda s: s.status == Enumerators.PaymentStatusEnum.unpaid)
        regular = {v.id: v.purpose for v in EngineSQL.Cache.get(Tables.RegularSpending)}
        personal = {v.id: v.purpose for v in EngineSQL.Cache.get(Tables.OneTimeSpending)}
        amount = 0
        with open("report.csv", "w", encoding="utf-8") as file:
            file.write("left amount,date,purpose\n")
            for s in spending:
                amount += s.left_amount
                if s.spending_type == Enumerators.SpendingTypeEnum.regular:
                    purpose = regular[s.spending_id]
                else:
                    purpose = personal[s.spending_id]
                file.write(f"{s.left_amount},{s.date.date().isoformat()},{purpose}\n")

    @Tools.connectionWithLock
    def createReportSalaries(self, *args):
        spending = Cache.get(
            Tables.Spending,
            where=lambda s: s.status == Enumerators.PaymentStatusEnum.unpaid and
                            s.spending_type == Enumerators.SpendingTypeEnum.regular and
                            s.tags[:1] == "1"
        )
        regular = {v.id: v.purpose for v in EngineSQL.Cache.get(Tables.RegularSpending)}
        today = datetime.date.today()
        t_date = today.year * 12 + today.month
        amount = 0
        with open("report_salary_till_today.csv", "w", encoding="utf-8") as file:
            file.write("date,personal\n")
            for s in spending:
                s_date = s.date.year * 12 + s.date.month
                if s_date > t_date:
                    continue
                amount += s.left_amount
                file.write(f"{s.date.date().isoformat()},{regular[s.spending_id]}\n")
            file.write(str(amount))

    @Tools.connection
    def autoCloseTransfers(self, checked=False):
        """
        Сканируем закрытые траты (Spending со статусом complete) и парсим transaction,
        чтобы извлечь tx_hash (через extractTxHash). Если находим в Transfers совпадающую
        транзакцию (complete == False), помечаем её как complete=True.
        """

        s = EngineSQL.s
        closed_spendings = s.query(Tables.Spending).filter(Tables.Spending.status == Enumerators.PaymentStatusEnum.complete).all()

        found_count = 0
        for sp in closed_spendings:
            # Пытаемся выдрать хэш
            hash_candidate = Tools.extractTxHash(sp.transaction or "")
            if not hash_candidate:
                continue

            # Ищем в Transfers по такому хэшу
            transfer = s.query(Tables.Transfers).filter(
                Tables.Transfers.tx_hash == hash_candidate,
                Tables.Transfers.complete == False
            ).first()

            if transfer:
                transfer.complete = True
                found_count += 1

        if found_count:
            s.commit()

        QMessageBox.information(
            self,
            "Auto mark closed transactions",
            f"Автоматически закрыто {found_count} транзакций" if found_count else "Совпадений не найдено"
        )

    @Tools.connection
    def autoDistributeSalaries(self, checked=False):
        """
        Пример: Ищем все незавершённые транзакции (Transfers.complete=False),
        проверяем условия (день 25..30, receiver — кошелёк сотрудника, сумма <= 
        очередной незакрытой зарплаты). 
        После чего вызываем confirmSpending(...) для оплаты, помечаем Transfer.complete = True.
        """
        
       
        
        s = EngineSQL.s
        open_transfers = s.query(Tables.Transfers).filter(Tables.Transfers.complete == False).all()

        # wallet -> staff
        wallets = {}
        for sw in s.query(Tables.StaffWallets).all():
            if sw.wallet:
                wallets[sw.wallet.lower()] = sw.staff

        distributed_count = 0
        
        for tx in open_transfers:
            # 1) Дата 25..30 (учитывая конец месяца)
            if not tx.date:
                continue
            d = tx.date.day
            days_in_month = calendar.monthrange(tx.date.year, tx.date.month)[1]
            if d < 25 or d > min(30, days_in_month):
                continue
            
            # 2) По кошельку receiver ищем сотрудника
            staff_id = wallets.get(tx.receiver.lower())
            if not staff_id:
                continue
            
            staff_obj = s.query(Tables.Staff).filter(Tables.Staff.id == staff_id).first()
            if not staff_obj:
                continue
            
            # 3) ищем "зарплату" Spending (spending_id = staff_obj.salary_id) в том же (год, месяц), 
            #    которая не закрыта
            salary_sp = s.query(Tables.Spending).filter(
                Tables.Spending.spending_type == Enumerators.SpendingTypeEnum.regular,
                Tables.Spending.spending_id == staff_obj.salary_id,
                extract("year", Tables.Spending.date) == tx.date.year,
                extract("month", Tables.Spending.date) == tx.date.month,
                Tables.Spending.status != Enumerators.PaymentStatusEnum.complete,
                Tables.Spending.tags.startswith("1")  # если "1" — признак зарплаты
            ).order_by(Tables.Spending.id).first()

            if not salary_sp:
                continue
            
            # 4) проверяем: tx.amount <= salary_sp.left_amount
            if tx.amount > salary_sp.left_amount:
                continue
            
            # 5) confirmSpending
            # index=Spending.id, tx=tx.tx_hash, amount=tx.amount, 
            # comment="auto distribution", date=tx.date, user_id=staff_id
            EngineSQL.confirmSpending(
                index=salary_sp.id,
                tx=tx.tx_hash,
                amount=tx.amount,
                comment="auto distribution",
                date=tx.date,
                user_id=staff_id
            )
            
            # 6) сам Transfer помечаем complete=True
            tx.complete = True
            distributed_count += 1

        if distributed_count:
            s.commit()

        not_distributed = s.query(Tables.Transfers).filter(Tables.Transfers.complete == False).count()
        QMessageBox.information(
            self,
            "Auto Distribute Salaries",
            f"Распределили {distributed_count} транзакций.\n"
            f"Осталось нераспределёнными: {not_distributed}"
        )
