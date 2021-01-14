#!/usr/bin/env python3
import argparse
from enum import Enum
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import floor
from pathlib import Path
from typing import Dict, List
import yaml


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y/%m/%d").date()


class BillingCycle(str, Enum):
    Monthly = "monthly"
    Yearly = "yearly"
    Weekly = "weekly"

    def to_monthly(self, value):
        if self.value == "yearly":
            return round(value / 12, 2)
        elif self.value == "weekly":
            return round(value * 52 / 12, 2)
        return value

    @property
    def default_day(self) -> int:
        if self.value == "weekly":
            return 0
        return 1


@dataclass
class Bill:
    name: str
    amount: float
    cycle: BillingCycle = BillingCycle.Monthly

    day: int = 1  # (1-31)
    weekday: int = 0  # (0-6) (Monday=0)
    month: int = 1  # (1-12)

    notes: str = ""

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

    def last_due_date(self, start_date: date) -> date:
        due_date = start_date
        while not self.is_due(due_date):
            due_date -= timedelta(days=1)
        return due_date

    def needed_balance(
        self, on_day: date, last_pay_day: date, pay_period=timedelta(days=14)
    ) -> float:
        last_payment = self.last_due_date(on_day)
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

    @classmethod
    def load_from_file(cls, budget_file: Path) -> 'Budget':
        with budget_file.open() as f:
            return cls(**yaml.load(f, Loader=yaml.SafeLoader))


def print_bill_allocations(bills: List[Bill], allocations: List[float]):
    def hrule(length):
        return "".join(["-"] * length)

    yesterday = date.today() - timedelta(days=1)
    border = "|" + hrule(78) + "|"
    print(border)
    print(f'| {"Bill":<41} | Allocated | Total   | Last Paid  |')
    border_sep = "|".join(["", hrule(43), hrule(11), hrule(9), hrule(12), ""])
    print(border_sep)
    for bill, allocated in zip(bills, allocations):
        last_due = bill.last_due_date(yesterday)
        print(
            f"| {bill.name:<41} |   {allocated: 7.2f} | {bill.amount:7.2f} | {last_due} |"
        )
    print(border)


def get_allowcations(budget: Budget, last_pay_day: date) -> List[float]:
    yesterday = date.today() - timedelta(days=1)
    return [bill.needed_balance(yesterday, last_pay_day) for bill in budget.bills]


def find_current_margin(
    budget, last_pay_day: date, current_balance: float, round_margin=True
):
    allocations = get_allowcations(budget, last_pay_day)
    total_allocated = sum(allocations)
    margin = current_balance - total_allocated
    if round_margin:
        rounded_margin = floor(margin / 10) * 10
        return rounded_margin, allocations
    else:
        return margin, allocations


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("last_pay_day", type=parse_date, help="(ex: YYYY/MM/DD)")
    cli.add_argument("balance", type=float, help="(ex: 1234.56)")
    cli.add_argument("--budget", type=Path, default=Path('budget.yml'))
    opts = cli.parse_args()
    budget = Budget.load_from_file(opts.budget)
    margin, allocations = find_current_margin(budget, opts.last_pay_day, opts.balance)
    print_bill_allocations(budget.bills, allocations)
    print(f"Current Balance: {opts.balance:.2f}")
    print(f"Margin: {margin:.2f}")
