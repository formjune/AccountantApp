from sql.EngineSQL import Session, engine, Base
from sql.Tables import Staff, RegularSpending, StaffSalaryHistory
from datetime import datetime, timezone
from decimal import Decimal

Base.metadata.create_all(engine, tables=[StaffSalaryHistory.__table__])
def backfill_salary_history():
    with Session() as s:
        for staff in s.query(Staff).all():
            rs = s.query(RegularSpending).where(
                    RegularSpending.id == staff.salary_id).one_or_none()
            if rs:
                s.add(StaffSalaryHistory(
                    staff=staff,
                    amount=rs.amount,
                    comment="auto-backfill",
                    changed_at=rs.date or datetime(2024, 1, 1, tzinfo=timezone.utc)
                ))
        s.commit()

backfill_salary_history()
