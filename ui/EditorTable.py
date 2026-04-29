import functools

from sql.EngineSQL import Cache

try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from tools import Tools
from ui import EditorDelegate, HighlightTable, TableItems
from sql import EngineSQL, Convert
from sql.Tables import *
from sql.Enumerators import *


class BaseTable(HighlightTable.HighlightTable):

    TABLE = None
    COLUMN_WIDTH = ()
    COLUMN_NAMES = ()
    HAS_MENU = False
    DUMP = True
    IS_EDITABLE = True
    DELEGATE = None
    SUPPORTS_ADD: bool = True
    is_loaded: bool = False
    _last_item = None
    _menu: dict
    _load_hash: int = 0

    MENU_BOOLEAN = ("true", "true"), ("false", "false")

    def __init__(self):
        super(BaseTable, self).__init__()
        self._menu = {}
        if self.HAS_MENU:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.showMenu)
        if not self.IS_EDITABLE:
            self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        if self.DELEGATE is not None:
            delegate = self.DELEGATE()
            delegate.widget_table = self
            self.setItemDelegate(delegate)
        self.setSortingEnabled(True)
        self.setColumnCount(len(self.COLUMN_NAMES))
        self.setHorizontalHeaderLabels(self.COLUMN_NAMES)
        for width in enumerate(self.COLUMN_WIDTH):
            self.setColumnWidth(*width)

    @Tools.connection
    def loadData(self, first_time: bool = False) -> None:
        if self.is_loaded and first_time:
            return
        data = EngineSQL.Cache.get(self.TABLE)
        self.setSortingEnabled(False)
        self.clear()
        self.setColumnCount(len(self.COLUMN_NAMES))
        self.setRowCount(len(data))
        self.setHorizontalHeaderLabels(self.COLUMN_NAMES)
        self.fillTable()
        for row, block in enumerate(data):
            for column, item in enumerate(Convert.asTuple(block)):
                self.setItem(row, column, TableItems.EditorItem(item))
        self.setSortingEnabled(True)
        self.loadContext()
        self.is_loaded = True
        self._load_hash = hash(self.convertTable())

    @Tools.connection
    def dumpData(self) -> None:
        if not self.is_loaded:
            return
        data = self.convertTable()
        new_hash = hash(data)
        if new_hash == self._load_hash:
            return
        data = [Convert.asItem(self.TABLE, v) for v in data]
        EngineSQL.dumpTable(self.TABLE, data)
        EngineSQL.Cache.put(self.TABLE, data)
        self._load_hash = new_hash

    @Tools.connection
    def addRow(self) -> None:
        row_count = self.rowCount()
        block = Convert.asTuple(EngineSQL.addValue(self.TABLE))
        self.setSortingEnabled(False)
        self.setRowCount(row_count + 1)
        for column, item in enumerate(block):
            self.setItem(row_count, column, TableItems.EditorItem(item))
        self.setSortingEnabled(True)

    @Tools.connection
    def deleteRows(self) -> None:
        self.setSortingEnabled(False)
        indices = set()
        for item in self.selectedItems():
            try:
                row = item.row()
            except RuntimeError:
                continue
            indices.add(int(self.item(row, 0).text()))
            self.removeRow(row)
        if indices:
            EngineSQL.deleteValues(self.TABLE, indices)
        self.setSortingEnabled(True)

    def convertTable(self) -> tuple:
        data = []
        for row in range(self.rowCount()):
            block = []
            for column in range(self.columnCount()):
                item = self.item(row, column)
                text = "" if item is None else item.text().strip()
                block.append(text)
            data.append(tuple(block))
        try:
            data.sort(key=lambda v: int(v[0]))
        except ValueError:
            print("failed to sort", data)
        return tuple(data)

    def unload(self) -> None:
        self.clear()
        self.is_loaded = False

    def loadContext(self) -> None:
        """load menu and formatter context. must be implemented"""
        pass

    def showMenu(self, point: QPoint) -> None:
        """show custom menu"""
        indices = {c.column() for c in self.selectedIndexes()}
        if len(indices) != 1:
            return
        index = indices.pop()
        if index not in self._menu:
            return
        menu = QMenu()
        for name, value in self._menu[index]:
            menu.addAction(name, functools.partial(self.setValues, value))
        menu.exec(self.mapToGlobal(point))

    def setValues(self, value: str) -> None:
        """set cell values via menu"""
        for item in self.selectedItems():
            item.setText(value)


class IncomeTypeEdit(BaseTable):

    TABLE = IncomeType
    COLUMN_NAMES = "ID", "name"
    COLUMN_WIDTH = 50, 200


class IncomeEdit(BaseTable):

    TABLE = Income
    COLUMN_NAMES = "ID", "source", "type", "amount", "commission %", "tokens", "date", "comment"
    COLUMN_WIDTH = 50, 200, 100, 100, 100, 100, 100, 200
    SUPPORTS_ADD = False
    HAS_MENU = True
    DELEGATE = EditorDelegate.Income

    @Tools.connection
    def loadContext(self) -> None:
        income_data = EngineSQL.Cache.get(IncomeType)
        self._menu[2] = [(e.name, str(e.id)) for e in income_data]
        self.DELEGATE.income_type = {str(e.id): e.name for e in income_data}


class PromotionSourceEdit(BaseTable):

    TABLE = PromotionSource
    COLUMN_NAMES = "ID", "name", "type", "comment"
    COLUMN_WIDTH = 50, 200, 100, 200
    HAS_MENU = True

    def loadContext(self) -> None:
        self._menu[2] = [(v.name, v.name) for v in PromotionSourceEnum]


class PromotionCommissionEdit(BaseTable):

    TABLE = PromotionCommission
    COLUMN_NAMES = "ID", "income source", "promotion source", "commission %", "amount", "date", "comment"
    COLUMN_WIDTH = 50, 200, 200, 100, 100, 100, 200, 200
    DELEGATE = EditorDelegate.PromotionCommission
    SUPPORTS_ADD = False
    HAS_MENU = True

    @Tools.connection
    def loadContext(self) -> None:
        income_source = EngineSQL.Cache.get(Income)
        promotion_source = EngineSQL.Cache.get(PromotionSource)
        self._menu[1] = [(v.source, str(v.id)) for v in income_source]
        self._menu[2] = [(v.name, str(v.id)) for v in promotion_source]
        self.DELEGATE.income_source = {str(v.id): v.source for v in income_source}
        self.DELEGATE.income_type = {str(v.id): v.name for v in promotion_source}


class RegularSpendingEdit(BaseTable):

    TABLE = RegularSpending
    COLUMN_NAMES = "ID", "updt", "purpose", "period", "amount", "repeat", "date"
    COLUMN_WIDTH = 50, 100, 200, 200, 100, 100, 200
    DELEGATE = EditorDelegate.RegularSpending
    HAS_MENU = True

    def loadContext(self) -> None:
        self._menu[1] = self.MENU_BOOLEAN


class OneTimeSpendingEdit(BaseTable):

    TABLE = OneTimeSpending
    COLUMN_NAMES = "ID", "purpose", "amount", "date"
    COLUMN_WIDTH = 50, 200, 100, 200


class StaffEdit(BaseTable):

    TABLE = Staff
    COLUMN_NAMES = "ID", "name", "position", "type", "department", "hire date", "salary ID", "comment"
    COLUMN_WIDTH = 50, 150, 150, 100, 200, 100, 100, 200
    DELEGATE = EditorDelegate.Staff
    SUPPORTS_ADD = False
    HAS_MENU = True

    @Tools.connection
    def loadContext(self) -> None:
        departments = EngineSQL.Cache.get(Department)
        self._menu[3] = [(e.name, e.name) for e in StaffTypeEnum]
        self._menu[4] = [(e.name, str(e.id)) for e in departments]
        self.DELEGATE.department = {t.id: t.name for t in departments}


class PersonalSpendingEdit(BaseTable):

    TABLE = PersonalSpending
    COLUMN_NAMES = "ID", "staff ID", "spending ID", "amount", "payment date", "comment"
    COLUMN_WIDTH = 50, 200, 200, 100, 200, 200
    HAS_MENU = True
    SUPPORTS_ADD = False
    DELEGATE = EditorDelegate.PersonalSpending

    @Tools.connection
    def loadContext(self) -> None:
        staff_data = EngineSQL.Cache.get(Staff)
        self._menu[1] = [(v.name, str(v.id)) for v in staff_data]
        self.DELEGATE.user_id = {v.id: v.name for v in staff_data}
        regular = {v.id: v.purpose for v in EngineSQL.Cache.get(RegularSpending)}
        personal = {v.id: v.purpose for v in EngineSQL.Cache.get(OneTimeSpending)}
        spending = {}
        for s in EngineSQL.Cache.get(Spending):
            try:
                if s.spending_type == SpendingTypeEnum.regular:
                    spending[s.id] = regular[s.spending_id]
                else:
                    spending[s.id] = personal[s.spending_id]
            except KeyError:
                pass
        self.DELEGATE.spending = spending


class SpendingEdit(BaseTable):

    TABLE = Spending
    COLUMN_NAMES = ("ID", "tags", "type", "spending ID", "date", "status", "amount", "left amount",
                    "paid amount", "transaction", "comment")
    SUPPORTS_ADD = False
    COLUMN_WIDTH = 50, 300, 100, 100, 200, 100, 100, 100, 100, 400, 200
    HAS_MENU = True
    DELEGATE = EditorDelegate.Spending

    @Tools.connection
    def loadContext(self) -> None:
        self._menu[2] = [(e.name, e.name) for e in SpendingTypeEnum]
        self._menu[5] = [(e.name, e.name) for e in PaymentStatusEnum]
        self.DELEGATE.tags = {t.id: t.name for t in EngineSQL.Cache.get(Tags)}
        self.DELEGATE.onetime_spending = {t.id: t.purpose for t in EngineSQL.Cache.get(OneTimeSpending)}
        self.DELEGATE.regular_spending = {t.id: t.purpose for t in EngineSQL.Cache.get(RegularSpending)}

    def showMenu(self, point: QPoint) -> None:
        indices = {c.column() for c in self.selectedIndexes()}
        if len(indices) != 1:
            return
        elif indices != {1}:
            BaseTable.showMenu(self, point)
            return
        indices = {(c.row(), c.column()) for c in self.selectedIndexes()}
        if len(indices) != 1:
            return
        item = self.item(*indices.pop())
        tags = item.text()
        menu = QMenu()
        actions = []
        for tag in EngineSQL.Cache.get(Tags):
            action = QAction(tag.name)
            action.setCheckable(True)
            if len(tags) < tag.id or tags[tag.id - 1] == "0":
                action.setChecked(False)
                action.triggered.connect(functools.partial(self.changeTag, item, tag.id, "1"))
            else:
                action.setChecked(True)
                action.triggered.connect(functools.partial(self.changeTag, item, tag.id, "0"))
            actions.append(action)
        menu.addActions(actions)
        menu.exec(self.mapToGlobal(point))

    def changeTag(self, item, tag_index, value):
        text = list(item.text())
        while len(text) < tag_index:
            text.append("0")
        text[tag_index - 1] = value
        item.setText("".join(text))


class TagsEdit(BaseTable):

    TABLE = Tags
    COLUMN_NAMES = "ID", "name"
    COLUMN_WIDTH = 50, 200


class TransfersEdit(BaseTable):

    TABLE = Transfers
    COLUMN_NAMES = ("ID", "done", "network", "from", "to", "amount", "amount tx", "token", "date", "token address",
                    "block", "hash")
    COLUMN_WIDTH = 50, 100, 300, 300, 150, 100, 100, 200, 300, 100, 500
    DELEGATE = EditorDelegate.Transfers
    DUMP = False

    @Tools.connection
    def loadContext(self) -> None:
        staff = {staff.id: staff.name for staff in EngineSQL.Cache.get(Staff)}
        self.DELEGATE.wallets = {wallet.wallet.lower(): staff[wallet.staff] for wallet in EngineSQL.Cache.get(StaffWallets)}
        self.DELEGATE.wallets.update({w.wallet.lower(): w.name for w in EngineSQL.Cache.get(TransferWallets)})


class TransferWalletsEdit(BaseTable):

    TABLE = TransferWallets
    COLUMN_NAMES = "ID", "wallet", "name", "budget"
    COLUMN_WIDTH = 50, 300, 300, 100
    HAS_MENU = True

    def loadContext(self) -> None:
        self._menu[3] = self.MENU_BOOLEAN


class StaffWalletsEdit(BaseTable):

    TABLE = StaffWallets
    COLUMN_NAMES = "ID", "staff", "wallet", "comment"
    COLUMN_WIDTH = 50, 200, 300, 300
    DELEGATE = EditorDelegate.StaffWallet
    HAS_MENU = True

    @Tools.connection
    def loadContext(self) -> None:
        staff = Cache.get(Staff)
        self._menu[1] = [(i.name, str(i.id)) for i in sorted(staff, key=lambda i: i.name.lower())]
        self.DELEGATE.staff = {i.id: i.name for i in staff}


class DepartmentEdit(BaseTable):

    TABLE = Department
    COLUMN_NAMES = "ID", "name", "parent", "lead"
    COLUMN_WIDTH = 50, 200, 200, 200
    DELEGATE = EditorDelegate.Department

    @Tools.connection
    def loadContext(self) -> None:
        self.DELEGATE.departments = {t.id: t.name for t in EngineSQL.Cache.get(Department)}
        self.DELEGATE.staff = {t.id: t.name for t in EngineSQL.Cache.get(Staff)}


class DateRangesEdit(BaseTable):

    TABLE = DateRanges
    COLUMN_NAMES = "ID", "type", "start", "end"
    COLUMN_WIDTH = 50, 100, 200, 200
    HAS_MENU = True

    def loadContext(self) -> None:
        self._menu[1] = [(t.name, t.name) for t in DateRangeTypeEnum]


class OffDaysPercentEdit(BaseTable):

    TABLE = OffDaysPercent
    COLUMN_NAMES = "ID", "staff", "vacation", "sickness"
    COLUMN_WIDTH = 50, 200, 100, 100
    DELEGATE = EditorDelegate.OffDaysPercent

    @Tools.connection
    def loadContext(self) -> None:
        self.DELEGATE.staff = {s.id: s.name for s in Cache.get(Staff)}


class RewardEdit(BaseTable):

    TABLE = Reward
    COLUMN_NAMES = "ID", "staff", "spending", "amount", "date"
    COLUMN_WIDTH = 50, 200, 100, 100, 200
