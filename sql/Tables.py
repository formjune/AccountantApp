import datetime
from sqlalchemy import Column, Integer, Float, Boolean, Numeric, String, DateTime, Enum, ForeignKey, func
from sqlalchemy.schema import Sequence
from sqlalchemy.orm import DeclarativeBase, relationship
from sql import EngineSQL
from sql.Enumerators import *


__all__ = ("Base", "update", "Budget", "IncomeType", "Income", "PromotionSource", "PromotionCommission", "RegularSpending",
           "OneTimeSpending", "Spending",  "Department", "Staff", "PersonalSpending", "Tags", "Transfers",
           "TransferWallets", "DateRanges", "OffDaysPercent","Reward", "StaffWallets", "BudgetMonthly", "StaffSalaryHistory")

class Base(DeclarativeBase):
    pass

def foreignKey(column):
    """return first suitable foreign key"""
    return lambda: EngineSQL.getForeignKey(column)


def update(table_old, table_new):
    """replace previous values with new except ID"""
    for name in table_old.slots[1:]:
        table_old.__setattr__(name.name, table_new.__getattribute__(name.name))


class IncomeType(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    
    __tablename__ = "income_type"
    slots = id, name
    types = Integer, String


class Income(Base):
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, default="")
    type = Column(Integer, ForeignKey(IncomeType.id), default=foreignKey(IncomeType.id))
    amount = Column(Float, default=0)
    commission = Column(Float, default=0)
    tokens = Column(Float, default=0)
    date = Column(DateTime, default=datetime.date.today())
    comment = Column(String, default="")

    __tablename__ = "income"
    slots = id, source, type, amount, commission, tokens, date, comment
    types = Integer, String, Integer, Float, Float, Float, DateTime, String


class PromotionSource(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    type = Column(Enum(PromotionSourceEnum), default=PromotionSourceEnum.adviser)
    comment = Column(String, default="")

    __tablename__ = "promotion_source"
    slots = id, name, type, comment
    types = Integer, String, Enum, String
    enums = {type: PromotionSourceEnum}


class PromotionCommission(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    income = Column(Integer, ForeignKey(Income.id), default=foreignKey(Income.id))
    recipient = Column(Integer, ForeignKey(PromotionSource.id), default=foreignKey(PromotionSource.id))
    percent = Column(Float, default=0)
    amount = Column(Float, default=0)
    date = Column(DateTime, default=datetime.date.today())
    comment = Column(String, default="")

    __tablename__ = "promotion_commission"
    slots = id, income, recipient, percent, amount, date, comment
    types = Integer, Integer, Integer, Float, Float, DateTime, String


class RegularSpending(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    unpredictable = Column(Boolean, default=False)
    purpose = Column(String, default="")
    period = Column(String, default="0/0/0/1")
    amount = Column(Float, default=0)
    repeat = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.date.today())

    __tablename__ = "regular_spending"
    slots = id, unpredictable, purpose, period, amount, repeat, date
    types = Integer, Boolean, String, String, Float, Integer, DateTime


class OneTimeSpending(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    purpose = Column(String, default="")
    amount = Column(Float, default=0)
    date = Column(DateTime, default=datetime.date.today())

    __tablename__ = "onetime_spending"
    slots = id, purpose, amount, date
    types = Integer, String, Float, DateTime


class Spending(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    tags = Column(String, default="")
    spending_type = Column(Enum(SpendingTypeEnum), default=SpendingTypeEnum.regular)
    spending_id = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.date.today())
    status = Column(Enum(PaymentStatusEnum), default=PaymentStatusEnum.unpaid)
    amount = Column(Float, default=0)
    left_amount = Column(Float, default=0)
    paid_amount = Column(Float, default=0)
    transaction = Column(String, default="")
    comment = Column(String, default="")

    __tablename__ = "spending"
    slots = id, tags, spending_type, spending_id, date, status, amount, left_amount, paid_amount, transaction, comment
    types = Integer, String, Enum, Integer, DateTime, Enum, Float, Float, Float, String, String
    slots_view = id, spending_id, tags, spending_type, date, amount, left_amount
    types_view = Integer, Integer, String, Enum, DateTime, Float, Float
    enums = {spending_type: SpendingTypeEnum, status: PaymentStatusEnum}


class Department(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    parent = Column(Integer, default=0)
    lead = Column(Integer, default=0)

    __tablename__ = "departments"
    slots = id, name, parent, lead
    types = Integer, String, Integer, Integer


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    position = Column(String, default="")
    type = Column(Enum(StaffTypeEnum), default=StaffTypeEnum.insource)
    department = Column(Integer, ForeignKey(Department.id), default=0)
    hire_date = Column(DateTime, default=datetime.date.today())
    salary_id = Column(Integer, ForeignKey(RegularSpending.id), default=foreignKey(RegularSpending.id))
    comment = Column(String, default="")
    salary_history = relationship("StaffSalaryHistory",
                                  order_by="StaffSalaryHistory.changed_at",
                                  cascade="all, delete-orphan")
    
    slots = id, name, position, type, department, hire_date, salary_id, comment
    types = Integer, String, String, Enum, Integer, DateTime, Integer, String
    enums = {type: StaffTypeEnum}


class PersonalSpending(Base):

    __tablename__ = "personal_spending"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Integer, ForeignKey(Staff.id), default=foreignKey(Staff.id))
    spending = Column(Integer, ForeignKey(Spending.id), default=foreignKey(Spending.id))
    amount = Column(Float, default=0)
    date = Column(DateTime, default=datetime.date.today())
    comment = Column(String, default="")

    slots = id, username, spending, amount, date, comment
    types = Integer, Integer, Integer, Float, DateTime, String


class Budget(Base):

    __tablename__ = "budget"
    id = Column(Integer, primary_key=True)
    value = Column(Float, default=0)


class Tags(Base):

    id = Column(Integer, Sequence('tags_sequence', start=10, increment=1), primary_key=True)
    name = Column(String, default="")

    __tablename__ = "tags"
    slots = id, name
    types = Integer, String


class Transfers(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    network = Column(String, default="mainnet")
    sender = Column(String(42), default="")
    receiver = Column(String(42), default="")
    amount = Column(Float, default=0)
    amount_tx = Column(Float, default=0)
    token = Column(String, default="")
    date = Column(DateTime, default=datetime.date.today())
    token_address = Column(String, default="")
    block = Column(Integer, default=0)
    tx_hash = Column(String, default="")
    complete = Column(Boolean, default=False)

    __tablename__ = "transfers"
    slots = id, complete, network, sender, receiver, amount, amount_tx, token, date, token_address, block, tx_hash
    types = Integer, Boolean, String, String, String, Float, Float, String, DateTime, String, Integer, String
    slots_view = sender, receiver, amount, amount_tx, token, network, date
    types_view = String, String, Float, Float, String, String, DateTime


class DateRanges(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Enum(DateRangeTypeEnum), default=DateRangeTypeEnum.vacation)
    start = Column(DateTime, default=datetime.date.today())
    end = Column(DateTime, default=datetime.date.today())

    __tablename__ = "date_ranges"
    slots = id, type, start, end
    types = Integer, Enum, DateTime, DateTime
    enums = {type: DateRangeTypeEnum}


class OffDaysPercent(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    staff = Column(Integer, default=1)
    vacation = Column(Float, default=.8)
    sick = Column(Float, default=.6)

    __tablename__ = "off_days_percent"
    slots = id, staff, vacation, sick
    types = Integer, Integer, Float, Float


class TransferWallets(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet = Column(String(42), default="")
    name = Column(String, default="")
    budget = Column(Boolean, default=False)

    __tablename__ = "transfer_wallets"
    slots = id, wallet, name, budget
    types = Integer, String, String, Boolean


class Reward(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    staff = Column(Integer, ForeignKey(Staff.id), default=foreignKey(Staff.id))
    payment = Column(Integer, default=-1)
    amount = Column(Float, default=0)
    date = Column(DateTime, default=datetime.date.today())

    __tablename__ = "reward"
    slots = id, staff, payment, amount, date
    types = Integer, Integer, Integer, Float, DateTime


class StaffWallets(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    staff = Column(Integer, ForeignKey(Staff.id), default=foreignKey(Staff.id))
    wallet = Column(String, default="")
    comment = Column(String, default="")

    __tablename__ = "staff_wallets"
    slots = id, staff, wallet, comment
    types = Integer, Integer, String, String


class BudgetMonthly(Base):
    __tablename__ = "budget_monthly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, default=2024)
    month = Column(Integer, default=1)
    start_value = Column(Float, default=0)
    end_value = Column(Float, default=0)

    def __repr__(self):
        return f"<BudgetMonthly y={self.year} m={self.month} start={self.start_value} end={self.end_value}>"


class StaffSalaryHistory(Base):
    __tablename__ = "staff_salary_history"

    id          = Column(Integer, primary_key=True)
    staff_id    = Column(Integer, ForeignKey("staff.id"), nullable=False)
    amount      = Column(Numeric(12, 2), nullable=False)
    changed_at  = Column(DateTime(timezone=True), nullable=False,
                         server_default=func.now())
    comment     = Column(String, nullable=True)

    staff       = relationship("Staff", back_populates="salary_history")