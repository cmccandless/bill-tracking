from datetime import date
import json
from pathlib import Path
from typing import Dict, MutableSet


class PaymentCacheJSON:
    def __init__(self, payment_file: Path = Path("payments.json")):
        self.payment_file = payment_file
        self.payments: Dict[str, MutableSet[date]] = {}
        self.load()

    def load(self):
        if self.payment_file.is_file():
            with self.payment_file.open() as f:
                safe = json.load(f)
            self.payments = {
                bill_name: {date.fromisoformat(payment) for payment in payments}
                for bill_name, payments in safe.items()
            }
        else:
            self.payments = {}

    def save(self):
        safe = {
            bill_name: [payment.isoformat() for payment in payments]
            for bill_name, payments in self.payments.items()
        }
        with self.payment_file.open("w") as f:
            json.dump(safe, f)

    def is_paid(self, bill_name: str, paid_date: date) -> bool:
        if bill_name not in self.payments:
            self.payments[bill_name] = set()
        return paid_date in self.payments[bill_name]

    def mark_paid(self, bill_name: str, paid_date: date):
        if bill_name not in self.payments:
            self.payments[bill_name] = set()
        self.payments[bill_name].add(paid_date)
        self.save()
