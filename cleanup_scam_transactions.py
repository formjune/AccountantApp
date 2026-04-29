#!/usr/bin/env python3
# cleanup_scam_transactions.py

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from tools.Config import USERNAME, PASSWORD, HOST, PORT, DATABASE

def main(threshold: float = 0.5):
    url = f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
    engine = create_engine(
        url,
        connect_args={'connect_timeout': 10},
        pool_pre_ping=True
    )

    try:
        with engine.begin() as conn:
            # DELETE возвращает число затронутых строк
            result = conn.execute(
                text("DELETE FROM transfers WHERE amount_tx < :thr"),
                {"thr": threshold}
            )
            print(f"Deleted {result.rowcount} transfers with amount < {threshold}")
    except SQLAlchemyError as e:
        print(f"[ERROR] failed to delete scam transactions: {e!r}")

if __name__ == "__main__":
    main()
