#!/usr/bin/env python3
from enum import Enum
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List
import yaml


budget_file = Path('budget.yml')
transactions_file = Path('transactions.yml')


class BillingCycle(str, Enum):
    Monthly = 'monthly'
    Yearly = 'yearly'
    Weekly = 'weekly'

    def to_monthly(self, value):
        if self.value == 'yearly':
            return round(value / 12, 2)
        elif self.value == 'weekly':
            return round(value * 52 / 12, 2)
        return value

    @property
    def default_day(self) -> int:
        if self.value == 'weekly':
            return 0
        return 1


@dataclass
class Bill:
    name: str
    amount: float
    variable_amount: bool = False
    cycle: BillingCycle = BillingCycle.Monthly

    day: int = 1  # (1-31)
    weekday: int = 0  # (0-6) (Monday=0)
    month: int = 1  # (1-12)

    notes: str = ''

    def __post_init__(self):
        if isinstance(self.cycle, str):
            self.cycle = BillingCycle(self.cycle)
        if self.day == -1:
            self.day = self.cycle.default_day

    @property
    def monthly_amount(self) -> float:
        return self.cycle.to_monthly(self.amount)

    def is_due(self, due_date: date) -> bool:
        if self.cycle == BillingCycle.Monthly:
            return self.day == due_date.day
        elif self.cycle == BillingCycle.Weekly:
            return self.weekday == due_date.weekday()
        elif self.cycle == BillingCycle.Yearly:
            return self.day == due_date.day and self.month == due_date.month
        return False

    def next_due_date(self, start_date: date) -> date:
        due_date = start_date
        while not self.is_due(due_date):
            due_date += timedelta(days=1)
        return due_date

    def previous_due_date(self, start_date: date) -> date:
        due_date = start_date
        while not self.is_due(due_date):
            due_date -= timedelta(days=1)
        return due_date

    def needed_balance(self, on_day: date, last_pay_day: date, pay_period=timedelta(days=14)) -> float:
        last_payment = self.previous_due_date(on_day)
        next_payment = self.next_due_date(on_day)
        next_pay_day = last_pay_day + pay_period
        if self.cycle == BillingCycle.Monthly:
            if last_payment > last_pay_day:
                return 0
            elif (next_payment - last_pay_day) < pay_period:  # due this pay period
                return self.amount
            else:
                return round(self.amount / 2, 2)
        elif self.cycle == BillingCycle.Weekly:
            # one_week = timedelta(days=7)
            if next_payment > next_pay_day:
                return 0
            elif last_payment < last_pay_day:
                return self.amount * 2
            return self.amount
        elif self.cycle == BillingCycle.Yearly:
            if last_payment > last_pay_day:
                return 0
            amount_due = 0
            day = last_pay_day
            while day > last_payment:
                amount_due += self.amount / 26
                day -= pay_period
            return round(amount_due, 2)
        return 0


@dataclass
class Budget:
    paycheck: float
    bills: List[Bill]

    def __post_init__(self):
        for i, bill in enumerate(self.bills):
            if isinstance(bill, dict):
                self.bills[i] = Bill(**bill)


Transactions = Dict[str, Dict[datetime, float]]


def get_budget() -> Budget:
    with budget_file.open() as f:
        return yaml.load(f, Loader=yaml.SafeLoader)


def get_transactions() -> Transactions:
    if not transactions_file.is_file():
        return {}
    with transactions_file.open() as f:
        return yaml.load(f, loader=yaml.SafeLoader)


def save_transactions(transactions: Transactions):
    with transactions_file.open('w') as f:
        yaml.dump(transactions, f)


def prompt_missing_transactions(budget: Budget, transactions: Transactions, start_date: date):
    day = start_date
    while day <= date.today():
        for bill in budget.bills:
            if bill.name not in transactions:
                transactions[bill.name] = {}
            if bill.is_due(day) and day not in transactions[bill.name]:
                if bill.variable_amount:
                    s = input(f'Billed amount for {bill.name} on {day}: ')
                    billed_amount = float(s)
                else:
                    billed_amount = bill.amount
                transactions[bill.name] = billed_amount
        day += timedelta(days=1)


def get_bills_for_pay_period(budget, start_date) -> List[float]:
    day = start_date
    end_date = start_date + timedelta(days=14)
    upcoming = []
    while day < end_date:
        for bill in budget.bills:
            if bill.is_due(day):
                upcoming.append(bill.amount)
    return upcoming


def find_current_margin():
    budget = get_budget()
    transactions = get_transactions()
    prompt_missing_transactions(budget, transactions)
    save_transactions(transactions)
    s = input('Current Balance: ')
    current_balance = float(s)
    s = input('Last pay day (YY/MM/DD): ')
    last_pay_day = datetime.strptime(s, '%Y/%m/%d').date()
    previous_pay_day = last_pay_day - timedelta(days=14)


if __name__ == "__main__":
    test_yaml = """paycheck: 1234.56
bills:
- name: Bill1
  amount: 10.0
  cycle: weekly
  notes: |
    foo
    bar
    baz
"""
    budget = Budget(**yaml.load(test_yaml, Loader=yaml.SafeLoader))
    print(budget.bills[0].monthly_amount)
