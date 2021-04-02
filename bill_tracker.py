#!/usr/bin/env python3
import argparse
from enum import Enum
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import floor
from pathlib import Path
from typing import List, Dict
import yaml

from tabulate import tabulate


WEEKS_PER_YEAR = 52


def parse_date(s: str) -> date:
    return datetime.strptime(s.replace('-', '/'), "%Y/%m/%d").date()


class BillingCycle(str, Enum):
    Monthly = "monthly"
    Yearly = "yearly"
    Weekly = "weekly"


@dataclass
class Bill:
    name: str
    amount: float
    cycle: BillingCycle = BillingCycle.Monthly

    day: int = 1  # (1-31)
    weekday: int = 0  # (0-6) (Monday=0)
    month: int = 1  # (1-12)

    notes: str = ""

    paid_next: bool = False

    def __post_init__(self):
        if isinstance(self.cycle, str):
            self.cycle = BillingCycle(self.cycle)

    def per_paycheck_estimate(self, pay_period):
        if self.cycle == BillingCycle.Monthly:
            yearly_amount = self.amount * 12
        elif self.cycle == BillingCycle.Weekly:
            yearly_amount = self.amount * WEEKS_PER_YEAR
        elif self.cycle == BillingCycle.Yearly:
            yearly_amount = self.amount
        else:
            return 0
        pay_period_weeks = pay_period.days / 7
        pay_periods_per_year = WEEKS_PER_YEAR / pay_period_weeks
        return yearly_amount / pay_periods_per_year

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
        if self.paid_next:
            due_date += timedelta(days=1)
            while not self.is_due(due_date):
                due_date += timedelta(days=1)
        return due_date

    def last_due_date(self, start_date: date) -> date:
        due_date = start_date
        while not self.is_due(due_date):
            due_date -= timedelta(days=1)
        return due_date

    def pay(self):
        self.paid_next = True

    def needed_balance(
        self, on_day: date, last_pay_day: date, pay_period=timedelta(days=14)
    ) -> float:
        last_payment = self.last_due_date(on_day)
        next_payment = self.next_due_date(on_day)
        next_pay_day = last_pay_day + pay_period
        needed = 0
        if self.cycle == BillingCycle.Monthly:
            if last_payment > last_pay_day:
                needed = 0
            elif (next_payment - last_pay_day) < pay_period:
                # due this pay period
                needed = self.amount
            else:
                needed = round(self.amount / 2, 2)
        elif self.cycle == BillingCycle.Weekly:
            # one_week = timedelta(days=7)
            if next_payment > next_pay_day:
                needed = 0
            elif last_payment < last_pay_day:
                needed = self.amount * 2
            return self.amount
        elif self.cycle == BillingCycle.Yearly:
            if last_payment > last_pay_day:
                needed = 0
            else:
                amount_due = 0
                day = last_pay_day
                while day > last_payment:
                    amount_due += self.amount / 26
                    day -= pay_period
                needed = round(amount_due, 2)
        if self.paid_next and needed >= self.amount:
            needed -= self.amount
        return needed


@dataclass
class Budget:
    bills: List[Bill]
    directdeposit: List[Bill] = None
    pay_period_days: int = 14
    minimum_balance: float = 0
    paid: List[str] = None

    def __post_init__(self):
        for i, bill in enumerate(self.bills):
            if isinstance(bill, dict):
                self.bills[i] = Bill(**bill)
        if self.directdeposit is None:
            self.directdeposit = []
        if self.paid is None:
            self.paid = {}
        else:
            for bill in self.bills:
                if bill.name in self.paid:
                    bill.pay()
        for i, bill in enumerate(self.directdeposit):
            if isinstance(bill, dict):
                self.directdeposit[i] = Bill(**bill)

    @property
    def pay_period(self) -> timedelta:
        return timedelta(days=self.pay_period_days)

    @classmethod
    def load_from_file(cls, budget_file: Path, paid: List[str]) -> "Budget":
        with budget_file.open() as f:
            return cls(paid=paid, **yaml.load(f, Loader=yaml.SafeLoader))

    def estimate_paycheck(self, bills_only=False):
        bill_total = sum(
            bill.per_paycheck_estimate(self.pay_period) for bill in self.bills
        )
        if bills_only:
            return bill_total
        return bill_total + sum(b.amount for b in self.directdeposit)

    def estimate_monthly(self, bills_only=False):
        paychecks_per_year = WEEKS_PER_YEAR / (self.pay_period_days / 7)
        paychecks_per_month = paychecks_per_year / 12
        per_paycheck = self.estimate_paycheck(bills_only=bills_only)
        return per_paycheck * paychecks_per_month


def hrule(length):
    return "".join(["-"] * length)


def print_bill_allocations(bills: List[Bill], allocations: List[float]):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    headers = ["Bill", "Allocated", "Total", "Cycle", "Last Paid", "Next Due"]
    data = [
        (
            bill.name,
            allocated,
            bill.amount,
            bill.cycle.name,
            bill.last_due_date(today),
            bill.next_due_date(tomorrow),
        )
        for bill, allocated in zip(bills, allocations)
    ]
    data = sorted(data, key=lambda d: d[5])
    print(tabulate(data, headers=headers, tablefmt="github", floatfmt=".2f"))


def get_allocations(budget: Budget, last_pay_day: date) -> List[float]:
    today = date.today()
    tomorrow = today + timedelta(days=1)
    # yesterday = today - timedelta(days=1)
    return [bill.needed_balance(tomorrow, last_pay_day) for bill in budget.bills]


def find_current_margin(
    budget, last_pay_day: date, current_balance: float, round_margin=True
):
    allocations = get_allocations(budget, last_pay_day)
    total_allocated = sum(allocations)
    margin = current_balance - budget.minimum_balance - total_allocated
    if round_margin:
        rounded_margin = floor(margin / 10) * 10
        return rounded_margin, allocations
    else:
        return margin, allocations


def manual_payment(text):
    name, amount = text.split('=')
    return (name, float(amount))


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("last_pay_day", type=parse_date, help="(ex: YYYY/MM/DD)")
    cli.add_argument("balance", type=float, help="(ex: 1234.56)")
    cli.add_argument("--budget", type=Path, default=Path("budget.yml"))
    cli.add_argument("-p", "--paid", action="append", default=[])
    opts = cli.parse_args()
    budget = Budget.load_from_file(opts.budget, opts.paid)

    margin, allocations = find_current_margin(budget, opts.last_pay_day, opts.balance)
    print_bill_allocations(budget.bills, allocations)

    print(hrule(40))
    data = [
        ("Estimated Monthly Expenses", budget.estimate_monthly(bills_only=True)),
        ("Estimated Minimum Paycheck", budget.estimate_paycheck()),
    ]
    print(tabulate(data, floatfmt=".2f", tablefmt="plain"))

    print(hrule(40))
    data = [
        ("Current Balance", opts.balance),
        ("Minimum Balance", budget.minimum_balance),
        ("Allocated Total", sum(allocations)),
    ]
    print(tabulate(data, floatfmt=".2f", tablefmt="plain"))

    print(hrule(40))
    print(f"Margin {margin:7.2f}")
