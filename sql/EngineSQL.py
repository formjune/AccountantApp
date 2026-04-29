import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import math
import sqlalchemy
import traceback
from sqlalchemy.exc import OperationalError
from sqlalchemy import and_, func, text
from sqlalchemy.orm import sessionmaker
from blockchain import EngineWeb3
from tools import Config, Tools
from sql.Tables import *
from sql.Enumerators import *


engine = sqlalchemy.create_engine(
     url=f"postgresql://{Config.USERNAME}:{Config.PASSWORD}@{Config.HOST}:{Config.PORT}/{Config.DATABASE}",
     connect_args={'connect_timeout': Config.TIMEOUT},
     pool_size=Config.POOL_SIZE,

     max_overflow=Config.MAX_OVERFLOW,
     # главный параметр, который «пингует» соединение перед использованием
     pool_pre_ping=True
)

Session = sessionmaker(bind=engine)
Session.configure(bind=engine)
ONE_DAY = datetime.timedelta(days=1)
MIN_TX = 0.5
s = Session()


class Cache(object):

    data = {}

    @classmethod
    def clear(cls) -> None:
        cls.data.clear()

    @classmethod
    def get(cls, table, where=None, order=None, reverse: bool = False, no_cache: bool = False) -> tuple:
        if no_cache or table.__tablename__ not in cls.data:
            cls.data[table.__tablename__] = tuple(s.query(table).all())
        data = cls.data[table.__tablename__]
        if where:
            data = tuple(filter(where, data))
        if order:
            data = tuple(sorted(data, key=order, reverse=reverse))
        return data

    @classmethod
    def put(cls, table, data) -> None:
        cls.data[table.__tablename__] = tuple(data)


def salaryDate(date, month_shift=0) -> datetime.date:
    year, month = divmod(date.year * 12 + date.month - 1 + month_shift, 12)
    month += 1
    return datetime.date(year, month, 27 if month in (2, 4, 6, 9, 11) else 28)


def checkConnection():
    """
    Проверяем, что сессия ещё «живая». Если соединение отвалилось, то пересоздаем объект s.
    Рекомендуется вызывать этот метод в декораторах @Tools.connection / @Tools.connectionWithLock.
    """
    global s
    try:
        # Небольшой тестовый запрос.
        # Если соединение «битое», мы получим ошибку (OperationalError или аналогичную).
        s.execute(text("SELECT 1"))
    except OperationalError:
        # Закрываем старую, пересоздаем новую.
        s.close()
        s = Session()
        print("[INFO] SQL connection was lost and has been re-created.")
    except:
        print("[ERROR] SQL connection error")  # при иных ошибках — своё логирование, если нужно
        traceback.print_exc()


def createTables() -> None:
    Base.metadata.create_all(engine)

@Tools.connection               # ⬅ read only – блокирует только сессию
def getSalaryHistory(staff_id: int) -> list[StaffSalaryHistory]:
    """
    Вернуть историю изменений зарплаты для сотрудника.

    Параметры
    ---------
    staff_id : int
        Идентификатор сотрудника (Staff.id).

    Returns
    -------
    list[StaffSalaryHistory]
        Отсортированный по времени список записей.
    """
    if staff_id is None:
        return []

    return (s.query(StaffSalaryHistory)                 # noqa: WPS442
             .filter_by(staff_id=staff_id)
             .order_by(StaffSalaryHistory.changed_at.asc())
             .all())


def getForeignKey(column):
    """find first acceptable value for foreign key"""
    f_key = s.query(column).first() 
    if f_key is not None:
        return f_key[0] 
    else: 
        # column.table — это модельная таблица, например Department или IncomeType.
        model = column.table  
        # создаём «пустую» запись. Если нужно заполнить поля, то 
        # new_record = model(name="Default department", parent=-1, lead=-1) (пример)
        new_record = model()
        s.add(new_record)
        s.commit()
        return new_record.id


def dumpTable(table: Base, new_data: list) -> None:
    """just overwrite values, no adding/removal needed"""
    new_data = {item.id: item for item in new_data}
    for item in s.query(table).all():
        if item.id in new_data:
            update(item, new_data[item.id])
    s.commit()


def updateBudget() -> float:
    budget = 0
    for item in s.query(TransferWallets).where(TransferWallets.budget == True).all():
        for network in EngineWeb3.NETWORKS:
            budget += EngineWeb3.getBalance(network, item.wallet)
    item = s.query(Budget).where(Budget.id == 1).one()
    if item is not None:
        item.value = budget
    s.commit()
    return budget


def getBudget() -> float:
    return s.query(Budget.value).where(Budget.id == 1).one()[0]

def getBudgetByMonth(date: datetime.date) -> float:
    _year, _month = date.year, date.month
    budget_total = s.query(BudgetMonthly.start_value).where(BudgetMonthly.year == _year, BudgetMonthly.month == _month).one()[0]
    print(budget_total)
    return budget_total


def addValue(table: Base) -> Base:
    """add new value and return with current ID"""
    s.add(table())
    s.commit()
    return s.query(table).order_by(table.id.desc()).first()


def deleteValues(table: Base, indices: set) -> None:
    for index in indices:
        s.query(table).where(table.id == index).delete()
    s.commit()


def confirmTransfer(tx_id, spending_id, amount, comment) -> None:
    tx = s.query(Transfers).where(Transfers.id == tx_id).first()
    spending = s.query(Spending).where(Spending.id == spending_id).first()
    amount = min(amount, tx.amount, spending.left_amount)
    if spending.spending_type == SpendingTypeEnum.regular:
        rs = s.query(RegularSpending).where(RegularSpending.id == spending.spending_id).first()
        if rs.unpredictable:
            amount = min(amount, tx.amount)
    tx.amount -= amount
    if tx.amount <= 0:
        tx.complete = True
    confirmSpending(spending_id, EngineWeb3.getUrl(tx.tx_hash, tx.network), amount, comment, tx.date, skip_tx=True)
    s.commit()


def discardTransfer(tx_id) -> None:
    s.query(Transfers).where(Transfers.id == tx_id).first().complete = True
    s.commit()


def createTags(tag_list):
    for tag in tag_list:
        s.add(Tags(name=tag))
    s.commit()


def confirmSpending(index, tx, amount, comment, date, user_id=-1, skip_tx = False) -> None:
    tx_hash = tx.lower().split("/")[-1]
    if tx_hash and not skip_tx:
        left_amount = amount
        for transfer in s.query(Transfers).where(Transfers.tx_hash == tx_hash).where(Transfers.complete == False).all():
            tx_amount = max(transfer.amount, left_amount)
            transfer.amount -= tx_amount
            left_amount -= tx_amount
            if transfer.amount <= 0:
                transfer.complete = True
            if left_amount <= 0:
                break

    sp = s.query(Spending).where(Spending.id == index).first()
    sp.transaction = tx
    sp.comment = comment
    sp.paid_amount = amount
    sp.date = date
    if sp.spending_type == SpendingTypeEnum.regular:
        rs = s.query(RegularSpending).where(RegularSpending.id == sp.spending_id).first()
        if rs.unpredictable:
            sp.left_amount = sp.amount = sp.paid_amount = amount
            sp.status = PaymentStatusEnum.complete
        elif sp.left_amount > amount:
            sp.status = PaymentStatusEnum.partial
            createSpending(sp.spending_type, sp.date, sp.amount, sp.left_amount - amount, sp.tags, sp.spending_id)
        else:
            sp.status = PaymentStatusEnum.complete
    else:
        if sp.left_amount > amount:
            sp.status = PaymentStatusEnum.partial
            createSpending(sp.spending_type, sp.date, sp.amount, sp.left_amount - amount, sp.tags, sp.spending_id)
        else:
            sp.status = PaymentStatusEnum.complete
        sp.left_amount -= amount

    # payment is personal spending
    if user_id != -1:
        item = PersonalSpending(
            username=user_id,
            spending=index,
            amount=amount,
            date=date,
            comment=comment
        )
        s.add(item)

        # append spending to salary
        salary_id = s.query(Staff.salary_id).where(Staff.id == user_id).first()[0]
        salary = s.query(RegularSpending.amount).where(RegularSpending.id == salary_id).first()[0]
        item = s.query(Spending).where(Spending.spending_id == salary_id).order_by(Spending.date.desc()).first()
        if item.status != PaymentStatusEnum.unpaid:
            item = Spending(
                tags=item.tags,
                spending_id=salary_id,
                date=salaryDate(item.date, 1),
                amount=salary + amount,
                left_amount=salary + amount
            )
            s.add(item)
        else:
            item.amount += amount
            item.left_amount += amount

    s.commit()


def createSpending(spending_type, date, amount, left_amount, tags="", spending=None, repeat=-1, purpose="", period="",
                   unpredictable=False) -> None:
    """create spending + regular/onetime if required"""

    if spending is not None:
        item_spending = s.query(RegularSpending).where(RegularSpending.id == spending).first()
    elif spending_type == SpendingTypeEnum.regular:
        item_spending = RegularSpending(
            purpose=purpose,
            amount=amount,
            repeat=repeat,
            date=date,
            period=period,
            unpredictable=unpredictable
        )
        s.add(item_spending)
        spending = s.query(RegularSpending.id).order_by(RegularSpending.id.desc()).first()[0]
    else:
        item_spending = OneTimeSpending(
            purpose=purpose,
            amount=amount,
            date=date
        )
        s.add(item_spending)
        spending = s.query(OneTimeSpending.id).order_by(OneTimeSpending.id.desc()).first()[0]

    item = Spending(
        spending_type=spending_type,
        spending_id=spending,
        date=date,
        amount=amount,
        left_amount=left_amount,
        tags=tags
    )
    s.add(item)
    s.commit()
    if spending_type == SpendingTypeEnum.regular:
        repeatSpending(item_spending)


def createIncome(name, income_type, amount, commission, tokens, date, comment, tx_id=-1, recipient=0) -> None:
    """create income and commission if required"""

    # new income type
    if isinstance(income_type, str):
        s.add(IncomeType(name=income_type))
        income_type = s.query(IncomeType.id).order_by(IncomeType.id.desc()).first()[0]

    if tx_id != -1:
        s.query(Transfers).where(Transfers.id == tx_id).first().complete = True

    item = Income(
        source=name,
        type=income_type,
        amount=amount,
        commission=commission,
        tokens=tokens,
        comment=comment,
        date=date
    )
    s.add(item)
    if commission:
        amount *= commission / 100
        item = PromotionCommission(
            income=s.query(Income.id).order_by(Income.id.desc()).first()[0],
            recipient=recipient,
            percent=commission,
            amount=amount,
            date=date,
            comment=comment
        )
        s.add(item)
        createSpending(SpendingTypeEnum.onetime, date, amount, amount, "01", purpose=f"{name}'s commission")
    s.commit()


def createCommission(income, recipient, commission, amount, date, comment) -> None:
    """create new commission for an income"""
    income = s.query(Income).where(Income.id == income).first()
    income.commission += commission
    item = PromotionCommission(
        income=income.id,
        recipient=recipient,
        percent=commission,
        amount=amount,
        date=date,
        comment=comment
    )
    s.add(item)
    createSpending(SpendingTypeEnum.onetime, date, amount, amount, "01", purpose=f"{income.source}'s commission")
    s.commit()


def createStaff(name, position, staff_type, wallet, salary, date, unpredictable, comment):
    # create regular spending
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    item_regular = RegularSpending(
        purpose=f"{name}'s salary",
        amount=salary,
        repeat=-1,
        date=date,
        period="0/1/0/0",
        unpredictable=unpredictable
    )
    s.add(item_regular)

    # create staff
    salary_id = s.query(RegularSpending.id).order_by(RegularSpending.id.desc()).first()[0]
    item = Staff(
        name=name,
        position=position,
        type=staff_type,
        hire_date=date,
        salary_id=salary_id,
        comment=comment
    )
    s.add(item)
    s.flush()                 
    _log_salary_change(
        s, item.id,
        Decimal("0.00"), Decimal(salary), "initial"
    )


    staff_id = s.query(Staff.id).order_by(Staff.id.desc()).first()[0]
    item = StaffWallets(
        staff=staff_id,
        wallet=wallet
    )
    s.add(item)

    if salary:
        salary_date = salaryDate(date)
        prev_salary_date = salaryDate(date, -1) + ONE_DAY
        if salary_date < date:
            salary_date = salaryDate(date, 1)
            prev_salary_date = salaryDate(date) + ONE_DAY
        worked_days = working_days = 0
        while prev_salary_date <= salary_date:
            if prev_salary_date.weekday() < 5:
                working_days += 1
            prev_salary_date += ONE_DAY
        while date <= salary_date:
            if date.weekday() < 5:
                worked_days += 1
            date += ONE_DAY
        salary = round(salary / working_days * worked_days, 2)

        item = Spending(
            spending_id=salary_id,
            date=salary_date,
            amount=salary,
            left_amount=salary,
            tags="1"
        )
        s.add(item)
        s.commit()
        repeatSpending(item_regular)
    elif unpredictable:
        repeatSpending(item_regular)
    

    s.commit()


def repeatSpending(regular_spending=None):
    """duplicate regular spending"""
    today = datetime.date.today()
    if regular_spending is not None:
        regular_spending = [regular_spending]
    else:
        regular_spending = s.query(RegularSpending).all()
    spending = s.query(Spending).where(Spending.spending_type == SpendingTypeEnum.regular).order_by(Spending.date).all()

    for rs in regular_spending:
        p = [int(p) for p in rs.period.split("/")]
        period = relativedelta(years=p[0], months=p[1], weeks=p[2], days=p[3])
        tmp_s = [s for s in spending if s.spending_id == rs.id]
        repeat = math.inf if rs.repeat == -1 else rs.repeat - len(tmp_s)
        while repeat > 0:
            tags = tmp_s[-1].tags if tmp_s else ""

            # no previous spending. create first one
            if not tmp_s:
                spending_day = rs.date

            # unpredictable spending
            elif rs.unpredictable and tmp_s[-1].status == PaymentStatusEnum.unpaid:
                break

            # salary
            elif tags[:1] == "1":
                prev_date = tmp_s[-1].date
                spending_day = salaryDate(prev_date, 1)
                if (spending_day - today).days > 32:
                    break

            # just spending
            else:
                spending_day = tmp_s[-1].date + period
                if (spending_day.date() - today).days > 32:
                    break

            item = Spending(
                spending_id=rs.id,
                date=spending_day,
                amount=rs.amount,
                left_amount=rs.amount,
                tags=tags
            )
            repeat -= 1
            tmp_s.append(item)
            s.add(item)
    s.commit()


def dismissStaff(user_id) -> None:
    user = s.query(Staff).where(Staff.id == user_id).first()
    user.type = StaffTypeEnum.dismissed
    spending = s.query(RegularSpending).where(RegularSpending.id == user.salary_id).first()
    spending.repeat = 0
    s.commit()
    # todo recalculate latest salary


def setNewSalary(staff_id: int,
                 new_salary: Decimal,
                 effective_date: datetime.date | None = None) -> None:
    if effective_date is None:
        effective_date = datetime.date.today()

    staff = s.get(Staff, staff_id)        
    if staff is None:
        raise ValueError(f"staff id {staff_id} not found")

    salary_id = staff.salary_id           

    rs        = s.get(RegularSpending, salary_id)

    old_amount     = Decimal(rs.amount)
    rs.amount      = Decimal(new_salary)

    _log_salary_change(
        s, staff_id, old_amount, rs.amount,
        comment=f"manual change in UI (effective {effective_date})",
        changed_at=datetime.datetime.combine(
            effective_date, datetime.time(0, 0), datetime.timezone.utc)
    )

    # Пересчитываем только будущие (неоплаченные) зарплаты,
    # начиная с месяца effective_date
    for sp in s.query(Spending).filter(
            Spending.status == PaymentStatusEnum.unpaid,
            Spending.spending_id == salary_id,          # только этот сотрудник
            Spending.date >= salaryDate(effective_date)
    ):
        delta = rs.amount - old_amount
        sp.amount      += float(delta)
        sp.left_amount += float(delta)

    s.commit()


def updateSalaryChangeDate(history_id: int,
                           new_date: datetime.date) -> None:
    rec = s.get(StaffSalaryHistory, history_id)
    if rec is None:
        raise ValueError(f"history id {history_id} not found")
    rec.changed_at = datetime.datetime.combine(
        new_date, datetime.time(0, 0), datetime.timezone.utc)
    s.commit()



def createTransfers() -> int:
    updateBudget()
    s.query(Transfers)
    all_transfers = {(t.tx_hash.lower(), t.receiver.lower()): t for t in s.query(Transfers).all()}
    all_staff = {t.id: t.hire_date.date() for t in s.query(Staff).all()}
    all_wallets = {t.wallet.lower(): all_staff[t.staff] for t in s.query(StaffWallets).all()}
    new_transfer_count = 0
    for pair in s.query(TransferWallets).all():
        for network in EngineWeb3.NETWORKS:
            for tx_key, new_tx in EngineWeb3.findTransfers(network, pair.wallet).items():
                if new_tx.get("amount_tx", 0) < MIN_TX: 
                    continue
                existing = all_transfers.get(tx_key)
                if existing:
                    # если amount_tx изменился — перезаписываем данные
                    if existing.amount_tx != new_tx["amount_tx"]:
                        existing.amount_tx = new_tx["amount_tx"]
                        existing.amount    = new_tx["amount"]
                        print(f"DEBUG: updated amount_tx for {existing.tx_hash}: {existing.amount_tx}")
                    # ничего вставлять не нужно
                    continue
                receiver = new_tx["receiver"].lower()
                if "date" not in new_tx:
                        new_tx["date"] = EngineWeb3.getBlockTime(new_tx["block"], network)
                if receiver in all_wallets and new_tx["date"] < all_wallets[receiver]:
                    continue
                s.add(Transfers(**new_tx))
                new_transfer_count += 1
    s.commit()
    recalcBudgetReverse()
    return new_transfer_count


def createStaffWallet(user_id, wallet, comment) -> None:
    s.add(StaffWallets(staff=user_id, wallet=wallet, comment=comment))
    s.commit()


def createDateRanges(date_type, all_dates: list) -> set:
    """create set of dates from range"""
    dates = set()
    for date in all_dates:
        if date.type != date_type:
            continue
        current_date = date.start
        while current_date <= date.end:
            dates.add(current_date)
            current_date += ONE_DAY
    return dates


def createReward(user_id, amount, date) -> bool:
    sp_id = s.query(Staff).where(Staff.id == user_id).first().salary_id
    salaries = s.query(Spending).where(
        and_(Spending.spending_id == sp_id, Spending.spending_type == SpendingTypeEnum.regular)).all()
    salaries = {salaryDate(salary.date): salary for salary in salaries}
    date = salaryDate(date)
    if date in salaries:
        if salaries[date].status != PaymentStatusEnum.unpaid:
            return False
        else:
            s.add(Reward(staff=user_id, amount=amount, date=date, payment=salaries[date].id))
            salaries[date].amount += amount
    else:
        s.add(Reward(staff=user_id, amount=amount, date=date))
    s.commit()
    return True


def deleteTransferDuplicates() -> int:
    transfers = {}
    tx_count = 0
    for tx in s.query(Transfers).order_by(Transfers.id).all():
        key = tx.network, tx.tx_hash, tx.receiver
        if key in transfers:
            s.delete(tx)
            tx_count += 1
        else:
            transfers[key] = tx
    s.commit()
    return tx_count


def addRewards() -> None:
    """add rewards to salaries"""
    spending = s.query(Spending).where(
        and_(Spending.spending_type == SpendingTypeEnum.regular, Spending.status == PaymentStatusEnum.unpaid)).all()
    salaries = {}
    for sp in filter(lambda i: i.tags[:1] == "1", spending):
        salaries[salaryDate(sp.date)] = sp
    for reward in s.query(Reward).where(Reward.payment != -1).all():
        reward_date = salaryDate(reward.date)
        if reward_date in salaries:
            sp = salaries[reward_date]
            sp.amount += reward.amount
            reward.payment = sp.id
    s.commit()


def recalculateSalaries() -> None:
    """recalculate salary in regards of vacations and sick days"""
    # todo potential bug for the first month of work

    all_ranges = s.query(DateRanges).all()
    vacation_days = createDateRanges(DateRangeTypeEnum.vacation, all_ranges)
    sick_days = createDateRanges(DateRangeTypeEnum.sick, all_ranges)

    for salary in s.query(Spending).where(and_(Spending.tags == "1", Spending.status == PaymentStatusEnum.unpaid)).all():
        vacation_count = sick_count = work_count = 0
        current_day = salaryDate(salary.date, -1)
        while current_day < salary.date:
            if current_day.weekday() > 5:
                pass
            elif current_day in vacation_days:
                vacation_count += 1
            elif current_day in sick_days:
                sick_count += 1
            else:
                work_count += 1
            current_day += ONE_DAY
        if sick_count == vacation_count == 0:
            continue

        # todo add recalculate salary

        full_salary = 1000
        sum_days = work_count + vacation_count + sick_count
        work_salary = work_count / sum_days * full_salary
        vacation_salary = vacation_count / sum_days * full_salary * 0.8
        sick_salary = sick_count / sum_days * full_salary * 0.6
        salary = work_salary + vacation_salary + sick_salary # + addition_part



def startTask():
    for i, name in enumerate(("salary", "commission"), 1):
        if not s.query(Tags).where(Tags.id == i).one_or_none():
            s.add(Tags(id=i, name=name))
    if not s.query(Budget).where(Budget.id == 1).one_or_none():
        s.add(Budget(id=1, value=0))
    if not s.query(Department).where(Department.id == 0).one_or_none():
        s.add(Department(id=0))
    if not s.query(OffDaysPercent).where(OffDaysPercent.id == 0).one_or_none():
        s.add(OffDaysPercent(id=0, staff=0))
    s.commit()
    repeatSpending()
    addRewards()



def getMonthlyDelta(year_: int, month_: int) -> float:
    """
    Считает "delta" (вход - выход) за указанный месяц,
    используя локальную БД Transfers (таблица sql.Tables.Transfers).
    Исключаем переводы внутри компании (budget->budget).
    """
    # Определим границы месяца
    first_day = datetime.date(year_, month_, 1)
    next_month = first_day + relativedelta(months=1)
    last_day = next_month - datetime.timedelta(seconds=1)

    # Собираем список всех "корпоративных" кошельков
    company_wallets = {
        w.wallet.lower()
        for w in s.query(TransferWallets)
                  .filter(TransferWallets.budget == True)
                  .all()
    }

    # incoming: sender - внешний, receiver - компания
    incoming = s.query(func.coalesce(func.sum(Transfers.amount_tx), 0)).filter(
        Transfers.date >= first_day,
        Transfers.date <= last_day,
        func.lower(Transfers.receiver).in_(company_wallets),
        ~func.lower(Transfers.sender).in_(company_wallets)        
    ).scalar()

    # outgoing: sender - компания, receiver - внешний
    outgoing = s.query(func.coalesce(func.sum(Transfers.amount_tx), 0)).filter(
        Transfers.date >= first_day,
        Transfers.date <= last_day,
        func.lower(Transfers.sender).in_(company_wallets),
        ~func.lower(Transfers.receiver).in_(company_wallets)
    ).scalar()

    delta = float(incoming - outgoing)
    return delta

def __prevMonth(year, month):
    """Возвращает (year, month) за предыдущий месяц."""
    month -= 1
    if month < 1:
        month = 12
        year -= 1
    return year, month

def recalcBudgetReverse():
    """
    Пересчёт бюджета "сверху вниз":
     1) Текущий месяц ВСЕГДА пересчитываем:
        - Считаем delta для текущего месяца => delta_cur
        - Узнаём реальный баланс (getRealWalletsBalance) => end_value
        - start_value = end_value - delta_cur
        - Записываем/обновляем в BudgetMonthly
     2) Идём назад (M-1, M-2, ... до 2024-01):
        - Если запись за месяц M уже существует, 
          то НЕ пересчитываем delta. 
          Но для согласованности:
            end_value(M) ДОЛЖЕН быть = start_value(M+1).
          => start_value(M+1) читаем из DB. 
          => row_M.end_value = row_cur.start_value
          -> row_M: 
             => row_M.start_value остаётся неизменным, 
                т.к. мы не пересчитываем
          => row_cur = row_M
        - Если записи НЕТ, тогда:
          => row_M.end_value = row_cur.start_value
          => deltaM = getMonthlyDelta(M)
          => row_M.start_value = row_M.end_value - deltaM
          => сохраняем, row_cur = row_M
    """

    # Определяем текущий месяц (year_cur, month_cur)
    today = datetime.date.today()
    year_cur = today.year
    month_cur = today.month

    # 1) ВСЕГДА пересчитываем текущий месяц
    row_cur = s.query(BudgetMonthly).filter_by(year=year_cur, month=month_cur).one_or_none()
    if not row_cur:
        row_cur = BudgetMonthly(year=year_cur, month=month_cur)
        s.add(row_cur)

    # Считаем delta
    delta_cur = getMonthlyDelta(year_cur, month_cur)
    # Берём реальный баланс
    real_bal = getBudget()

    row_cur.end_value = real_bal
    row_cur.start_value = real_bal - delta_cur
    s.commit()

    # 2) Двигаемся назад
    ptr_year, ptr_month = year_cur, month_cur

    while True:
        # предыдущий месяц
        ptr_year, ptr_month = __prevMonth(ptr_year, ptr_month)

        # Если дошли раньше 2024-01 => выходим
        if ptr_year < 2024 or (ptr_year == 2024 and ptr_month < 1):
            break

        # row_past - запись за (ptr_year, ptr_month)
        row_past = s.query(BudgetMonthly).filter_by(year=ptr_year, month=ptr_month).one_or_none()

        if row_past:
            # Запись уже существует, значит "пропускаем пересчёт"
            # Но нужно связать end_value(row_past) = start_value(row_cur).
            # => row_past.end_value = row_cur.start_value
            # start_value(row_past) НЕ меняем (так как skip recalculation).
            row_past.end_value = row_cur.start_value
            s.commit()

            # затем row_cur = row_past
            row_cur = row_past
        else:
            # Записи нет => создаём и пересчитываем
            row_past = BudgetMonthly(year=ptr_year, month=ptr_month, start_value=0, end_value=0)
            s.add(row_past)
            # end_value(row_past) = row_cur.start_value
            row_past.end_value = row_cur.start_value
            # deltaM = getMonthlyDelta(ptr_year, ptr_month)
            dval = getMonthlyDelta(ptr_year, ptr_month)
            row_past.start_value = row_past.end_value - dval
            s.commit()

            # row_cur = row_past
            row_cur = row_past

        # идём к ещё более раннему месяцу
    print("[INFO] Reverse recalc done.")


def getMonthlyIncomingOutgoing(year_: int, month_: int):
    """
    Выводит список транзакций, которые учитываются в getMonthlyDelta(year_, month_).
    А именно, те, что попадают в [first_day, last_day],
    и при этом (receiver in company_wallets, sender not in company_wallets) или (sender in..., receiver not in...).
    Также выводит сумму incoming, outgoing, delta.
    """
    # filename = f"debug_delta{year_}_{month_}.txt"
    first_day = datetime.date(year_, month_, 1)
    next_month = first_day + relativedelta(months=1)
    last_day = next_month - datetime.timedelta(seconds=1)

    # Собираем corporate-кошельки
    company_wallets = {
        w.wallet.lower()
        for w in s.query(TransferWallets).filter(TransferWallets.budget == True).all()
    }

    # Берём все Transfers за [first_day, last_day].
    all_txs = s.query(Transfers).filter(
        Transfers.date >= first_day,
        Transfers.date <= last_day
    ).all()

    incoming_list = []
    outgoing_list = []
    for tx in all_txs:
        snd = tx.sender.lower()
        rcv = tx.receiver.lower()
        amt = tx.amount_tx

        # incoming: receiver in company_wallets, sender not in company_wallets
        if (rcv in company_wallets) and (snd not in company_wallets):
            incoming_list.append(tx)
        # outgoing: sender in company_wallets, receiver not in company_wallets
        elif (snd in company_wallets) and (rcv not in company_wallets):
            outgoing_list.append(tx)

    # incoming_sum = sum(tx.amount_tx for tx in incoming_list)
    # outgoing_sum = sum(tx.amount_tx for tx in outgoing_list)
    # delta = incoming_sum - outgoing_sum

    # Запись в файл
    # with open(filename, "a", encoding="utf-8") as f:
    #     f.write(f"\n========== {year_}-{month_} ========== \n")
    #     f.write(f"Date range: {first_day} .. {last_day}\n\n")

    #     f.write("[INCOMING]:\n")
    #     for tx in incoming_list:
    #         f.write(
    #             f"  id={tx.id}, date={tx.date}, sender={tx.sender}, "
    #             f"receiver={tx.receiver}, amount_tx={tx.amount_tx}, hash={tx.tx_hash}\n"
    #         )

    #     f.write("\n[OUTGOING]:\n")
    #     for tx in outgoing_list:
    #         f.write(
    #             f"  id={tx.id}, date={tx.date}, sender={tx.sender}, "
    #             f"receiver={tx.receiver}, amount_tx={tx.amount_tx}, hash={tx.tx_hash}\n"
    #         )

    #     f.write(f"\nIncoming = {incoming_sum}, Outgoing = {outgoing_sum}, delta = {delta}\n\n")

    return (incoming_list, outgoing_list)

    

def getNameOrAddress(addr: str) -> str:
    wallet_name_map = {}

    # Соберём сначала staff_id->staff_name
    staff_dict = {st.id: st.name for st in s.query(Staff).all()}

    # StaffWallets:  wallet -> staff.name
    for sw in s.query(StaffWallets).all():
        staff_name = staff_dict.get(sw.staff, "")
        if staff_name:
            wallet_name_map[sw.wallet.lower()] = staff_name

    # TransferWallets: wallet -> name
    for tw in s.query(TransferWallets).all():
        if tw.name:
            wallet_name_map[tw.wallet.lower()] = tw.name
    a = addr.lower()
    return wallet_name_map[a] if a in wallet_name_map else addr


def makeMonthlyReport(year: int, month: int, exclude_ids: set[int] = None) -> str:
    """
    Формирует текстовый отчёт по формату:

    Monthly Cash Movements

    Cash balance at the beginning of the month
    Cash-in: ...
    Cash-in: ...
    ...
    Cash-out: ...
    Cash-out: ...
    ...
    Cash balance at the end of the month

    Параметр exclude_ids — множество id транзакций, которые следует исключить из учёта.
    """

    if exclude_ids is None:
        exclude_ids = set()

    # Берём данные из таблицы BudgetMonthly (см. предыдущую реализацию)
    row_cur = s.query(BudgetMonthly).filter_by(year=year, month=month).one_or_none()
    if row_cur:
        beginning_balance = row_cur.start_value
        ending_balance = row_cur.end_value
    else:
        # Если записи нет, пусть будет 0 и 0, либо посчитать иначе
        beginning_balance = 0
        ending_balance = 0

    # Собираем incoming/outgoing
    incoming_list, outgoing_list = getMonthlyIncomingOutgoing(year, month)

    # Применим исключённые транзакции
    incoming_list = [tx for tx in incoming_list if tx.id not in exclude_ids]
    outgoing_list = [tx for tx in outgoing_list if tx.id not in exclude_ids]

    # Подсчитаем объёмы
    total_incoming = sum(tx.amount_tx for tx in incoming_list)
    total_outgoing = sum(tx.amount_tx for tx in outgoing_list)

    # Формируем нужные строки
    lines = []
    lines.append("Monthly Cash Movements\n")
    lines.append("\nCash balance at the beginning of the month\n")
    lines.append(f"{beginning_balance:.2f}\n")

    # Входящие
    for tx in incoming_list:
        sender_name = getNameOrAddress(tx.sender)
        lines.append(f"Cash-in: {tx.date.date()} from {sender_name} amount {tx.amount_tx:.2f}\n")

    # Исходящие
    for tx in outgoing_list:
        receiver_name = getNameOrAddress(tx.receiver)
        lines.append(f"Cash-out: {tx.date.date()} to {receiver_name} amount {tx.amount_tx:.2f}\n")

    lines.append("Cash balance at the end of the month\n")
    lines.append(f"{ending_balance:.2f}\n")

    lines.append(f"Total incoming sum:{total_incoming}\nTotal outgoing sum: {total_outgoing}")


    return "".join(lines)


def _log_salary_change(session,
                       staff_id: int,
                       old: Decimal,
                       new: Decimal,
                       comment: str = "",
                       changed_at: datetime.datetime | None = None):
    """Пишет строку в staff_salary_history в той же транзакции."""
    if changed_at is None:                          # было: всегда now()
        changed_at = datetime.datetime.now(datetime.timezone.utc)

    session.add(StaffSalaryHistory(
        staff_id   = staff_id,
        amount     = new,
        comment    = comment,
        changed_at = changed_at,
    ))

