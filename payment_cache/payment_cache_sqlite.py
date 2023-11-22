from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sqlite3
from typing import Dict, MutableSet


class PaymentCacheSqlite:
    def __init__(self, payment_file: Path = Path("payments.db")):
        self.payment_file = payment_file
        self.payments: Dict[str, MutableSet[date]] = {}
        self._init_db()

    @contextmanager
    def _connect_db(self, ):
        con = sqlite3.connect(self.payment_file)
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def _cursor(self, commit: bool = True):
        with self._connect_db() as con:
            cursor = con.cursor()
            try:
                yield cursor
                if commit:
                    con.commit()
            finally:
                cursor.close()

    def _init_db(self):
        query = """CREATE TABLE IF NOT EXISTS payments (
            bill TEXT NOT NULL,
            date TEXT NOT NULL,
            PRIMARY KEY ( bill, date )
        )"""
        with self._cursor() as cursor:
            cursor.execute(query)

    def is_paid(self, bill_name: str, paid_date: date) -> bool:
        query = f"""SELECT * FROM payments WHERE bill = "{bill_name}" AND date = "{paid_date.isoformat()}" ;"""
        with self._cursor() as cursor:
            cursor.execute(query)
            return any(cursor.fetchall())
        
    def mark_paid(self, bill_name: str, paid_date: date):
        query = f"""INSERT INTO payments VALUES ("{bill_name}", "{paid_date.isoformat()}")"""
        with self._cursor() as cursor:
            cursor.execute(query)
