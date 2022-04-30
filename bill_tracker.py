#!/usr/bin/env python3
import argparse
from enum import Enum
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from math import floor
from pathlib import Path
import re
from typing import List, Tuple, Dict
import yaml

import sys

from tabulate import tabulate


WEEKLY = relativedelta(weeks=+1)
MONTHLY = relativedelta(months=+1)
YEARLY = relativedelta(years=+1)


MONTHS_PER_YEAR = 12
WEEKS_PER_YEAR = 52
SALES_TAX = 1.07


def dbg(msg, **kwargs):
    print(f'DEBUG: {msg}', **kwargs, file=sys.stderr)


def parse_date(s: str) -> date:
    return datetime.strptime(s.replace('-', '/'), "%Y/%m/%d").date()


class BillingCycle(str, Enum):
    Monthly = "monthly"
    Yearly = "yearly"
    Weekly = "weekly"


def t_timespan(x) -> relativedelta:
    if isinstance(x, str):
        if x == 'weekly':
            return WEEKLY
        elif x == 'monthly':
            return MONTHLY
        elif x == 'yearly':
            return YEARLY
    elif isinstance(x, dict):
        return relativedelta(**x)
    raise ValueError(f"ERROR: invalid timespan {x}")


def pay_days_since(since_date: date, last_pay_day: date, pay_period: timedelta=timedelta(weeks=2)):
    pay_days = 0
    current = last_pay_day
    while since_date <= current:
        pay_days += 1
        current -= pay_period
    return pay_days


def pay_days_until(until_date: date, last_pay_day: date, pay_period: timedelta=timedelta(weeks=2)):
    pay_days = 0
    current = last_pay_day + pay_period
    while current < until_date:
        pay_days += 1
        current += pay_period
    return pay_days


@dataclass
class Bill:
    name: str
    amount: float
    cycle: relativedelta = relativedelta(months=+1)
    lastPaid: datetime = None

    day: int = 1  # (1-31)
    weekday: int = 0  # (0-6) (Monday=0)
    month: int = 1  # (1-12)

    notes: str = ""

    paid_next: bool = False

    def __post_init__(self):
        if not isinstance(self.cycle, relativedelta):
            self.cycle = t_timespan(self.cycle)
        if self.lastPaid is None:
            today = date.today()
            if self.cycle == YEARLY:
                self.lastPaid = date(today.year, self.month, self.day)
                if today < self.lastPaid:
                    self.lastPaid -= relativedelta(years=+1)
            elif self.cycle == MONTHLY:
                self.lastPaid = date(today.year, today.month, self.day)
                if today < self.lastPaid:
                    self.lastPaid -= relativedelta(months=+1)
            elif self.cycle == WEEKLY:
                self.lastPaid = today
                while self.lastPaid.weekday() != self.weekday:
                    self.lastPaid -= relativedelta(days=+1)
            else:
                raise ValueError(f"ERROR: Must provide lastBilled for irregular billing cycle ({self.name})")
        elif isinstance(self.lastPaid, str):
            self.lastPaid = parse_date(self.lastPaid)

    def per_paycheck_estimate(self, pay_period: timedelta):
        paychecks_per_cycle = ((self.lastPaid + self.cycle) - self.lastPaid).days / pay_period.days
        return round(self.amount / paychecks_per_cycle, 2)

    def is_due(self, due_date: date) -> bool:
        last_billed = self.lastPaid
        while last_billed < due_date:
            last_billed += self.cycle
        return due_date == last_billed

    def next_due_date(self, start_date: date) -> date:
        next_due = self.lastPaid
        while next_due < start_date:
            next_due += self.cycle
        return next_due

    def last_due_date(self, start_date: date) -> date:
        last_due = self.lastPaid
        while (last_due + self.cycle) < start_date:
            last_due += self.cycle
        return last_due

    def pay(self):
        self.paid_next = True

    def needed_balance(
        self, on_day: date, last_pay_day: date, pay_period=timedelta(days=14)
    ) -> float:
        last_payment = self.last_due_date(on_day)
        next_payment = last_payment + self.cycle
        needed = 0
        pay_days_since_last_payment = pay_days_since(last_payment, last_pay_day, pay_period)
        pay_days_until_due = pay_days_until(next_payment, last_pay_day, pay_period)
        total_pay_days_in_cycle = pay_days_since_last_payment + pay_days_until_due
        alloc_percent = pay_days_since_last_payment / total_pay_days_in_cycle
        needed = round(self.amount * alloc_percent, 2)
        if self.paid_next and needed >= self.amount:
            needed -= self.amount
        return needed


@dataclass
class ReservedItem:
    amount: float
    store: str = None
    orderNo: str = None
    description: str = None
    addSalesTax: bool = False
    group: str = None
    quantity: int = 1

    def __post_init__(self):
        self.amount *= self.quantity
        if self.addSalesTax:
            self.amount *= SALES_TAX

    @property
    def as_tuple(self) -> Tuple[str, float]:
        return (f'[RESERVED] {self.description}'.rstrip(), self.amount)


@dataclass
class Budget:
    bills: List[Bill]
    directdeposit: List[Bill] = None
    pay_period_days: int = 14
    minimum_balance: float = 0
    paid: List[str] = None
    reserved: List[ReservedItem] = None

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
        if self.reserved is None:
            self.reserved = []
        else:
            for i, reserved in enumerate(self.reserved):
                if isinstance(reserved, dict):
                    self.reserved[i] = ReservedItem(**reserved)

    @property
    def pay_period(self) -> timedelta:
        return timedelta(days=self.pay_period_days)

    @classmethod
    def load_from_file(cls, budget_file: Path, paid: List[str], reserved: List[ReservedItem]) -> "Budget":
        with budget_file.open() as f:
            budget = cls(paid=paid, **yaml.load(f, Loader=yaml.SafeLoader))
        for reserved_item in reserved:
            budget.reserved.append(reserved_item)
        return budget

    def estimate_paycheck(self, bills_only=False):
        bill_total = sum(
            bill.per_paycheck_estimate(self.pay_period) for bill in self.bills
        )
        if bills_only:
            return bill_total
        return bill_total + sum(b.amount for b in self.directdeposit)

    def estimate_monthly(self, bills_only=False):
        paychecks_per_year = WEEKS_PER_YEAR / (self.pay_period_days / 7)
        paychecks_per_month = paychecks_per_year / MONTHS_PER_YEAR
        per_paycheck = self.estimate_paycheck(bills_only=bills_only)
        return per_paycheck * paychecks_per_month


def hrule(length):
    return "".join(["-"] * length)


def format_billing_cycle(cycle: relativedelta):
    if cycle == MONTHLY:
        return 'Monthly'
    elif cycle == YEARLY:
        return 'Yearly'
    elif cycle == WEEKLY:
        return 'Weekly'
    return f"Years={cycle.years} Months={cycle.months} Weeks={cycle.weeks}"


def print_bill_allocations(bills: List[Bill], allocations: List[float]):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    headers = ["Bill", "Allocated", "Total", "Cycle", "Last Paid", "Next Due"]
    data = [
        (
            bill.name,
            allocated,
            bill.amount,
            format_billing_cycle(bill.cycle),
            bill.last_due_date(today),
            bill.next_due_date(tomorrow),
        )
        for bill, allocated in zip(bills, allocations)
    ]
    data = sorted(data, key=lambda d: d[5])
    print(tabulate(data, headers=headers, tablefmt="github", floatfmt=".2f"))


def get_allocations(budget: Budget, last_pay_day: date) -> List[float]:
    today = date.today()
    # tomorrow = today + timedelta(days=1)
    # yesterday = today - timedelta(days=1)
    return [bill.needed_balance(today, last_pay_day) for bill in budget.bills]


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


def t_reserve(s: str) -> ReservedItem:
    if m := re.match(r"^(?:(?P<name>[\w ]+)=)?(?P<amount>-?\d+(?:\.\d{1,2})?)$", s):
        amount = float(m.group('amount'))
        name = m.group("name")
        if not name:
            item = ReservedItem(amount=amount)
        else:
            item = ReservedItem(amount=amount, description=name)
        return item
    raise ValueError(f"ERROR: NO MATCH: {s}")


def apply_reservations(margin: float, allocations: List[float], reservations: List[ReservedItem]):
    allocations = allocations[:]
    for item in reservations:
        margin -= item.amount
        allocations.append(item.amount)
    return margin, allocations


def group_reservations(reservations: List[ReservedItem]) -> List[Tuple[str, float]]:
    ungrouped = []
    groups: Dict[str, ReservedItem] = {}
    for item in reservations:
        if item.group is None:
            ungrouped.append(item)
        else:
            if item.group not in groups:
                groups[item.group] = ReservedItem(item.amount, description=f'{item.group} (Grouped)')
            else:
                groups[item.group].amount += item.amount
    return [*ungrouped, *list(groups.values())]


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("last_pay_day", type=parse_date, help="(ex: YYYY/MM/DD)")
    cli.add_argument("balance", type=float, help="(ex: 1234.56)")
    cli.add_argument("--budget", type=Path, default=Path("budget.yml"))
    cli.add_argument("-p", "--paid", action="append", default=[])
    cli.add_argument("-r", "--reserve", action="append", default=[], type=t_reserve, help=("ex: 59.99, Preorder=120"))
    opts = cli.parse_args()
    budget = Budget.load_from_file(opts.budget, opts.paid, opts.reserve)

    margin, allocations = find_current_margin(budget, opts.last_pay_day, opts.balance)
    margin, allocations = apply_reservations(margin, allocations, budget.reserved)
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
        *(r.as_tuple for r in group_reservations(budget.reserved)),
        ("Allocated Total", sum(allocations)),
    ]
    print(tabulate(data, floatfmt=".2f", tablefmt="plain"))

    print(hrule(40))
    print(f"Margin {margin:7.2f}")
