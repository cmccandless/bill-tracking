import unittest

from datetime import date

from bill_tracker import Bill, BillingCycle


class TestMonthlyBill(unittest.TestCase):
    def test_due_this_period(self):
        last_pay_day = date(2020, 12, 27)
        on_day = date(2020, 12, 28)
        bill = Bill('Rent', 1200)
        self.assertEqual(bill.needed_balance(on_day, last_pay_day), 1200)

    def test_paid_this_period(self):
        last_pay_day = date(2020, 12, 30)
        on_day = date(2021, 1, 3)
        bill = Bill('Rent', 1200)
        self.assertEqual(bill.needed_balance(on_day, last_pay_day), 0)

    def test_paid_last_period(self):
        last_pay_day = date(2021, 1, 4)
        on_day = date(2021, 1, 8)
        bill = Bill('Rent', 1200)
        self.assertEqual(bill.needed_balance(on_day, last_pay_day), 600)


class TestWeeklyBill(unittest.TestCase):
    def test_no_payments_this_period(self):
        last_pay_day = date(2021, 1, 8)
        on_day = date(2021, 1, 10)
        bill = Bill('HelloFresh', 60, cycle=BillingCycle.Weekly, day=1)
        self.assertEqual(bill.needed_balance(on_day, last_pay_day), 120)

    def test_one_payments_this_period(self):
        last_pay_day = date(2021, 1, 8)
        on_day = date(2021, 1, 15)
        bill = Bill('HelloFresh', 60, cycle=BillingCycle.Weekly, day=1)
        self.assertEqual(bill.needed_balance(on_day, last_pay_day), 60)

    def test_two_payments_this_period(self):
        last_pay_day = date(2021, 1, 8)
        on_day = date(2021, 1, 21)
        bill = Bill('HelloFresh', 60, cycle=BillingCycle.Weekly, day=1)
        self.assertEqual(bill.needed_balance(on_day, last_pay_day), 0)


class TestYearlyBill(unittest.TestCase):
    def test_paid_this_period(self):
        last_pay_day = date(2020, 12, 30)
        on_day = date(2021, 1, 7)
        bill = Bill('Disney+', 70, cycle=BillingCycle.Yearly, day=5, month=1)
        self.assertEqual(bill.needed_balance(on_day, last_pay_day), 0)

    def test_paid_three_periods_ago(self):
        last_pay_day = date(2020, 12, 30)
        on_day = date(2021, 1, 7)
        bill = Bill('Disney+', 70, cycle=BillingCycle.Yearly, day=24, month=11)
        expected_amount = 70 / 26 * 3
        self.assertAlmostEqual(
            bill.needed_balance(on_day, last_pay_day),
            expected_amount,
            places=2
        )

    def test_due_this_period(self):
        last_pay_day = date(2020, 12, 30)
        on_day = date(2021, 1, 7)
        bill = Bill('Disney+', 70, cycle=BillingCycle.Yearly, day=8, month=1)
        self.assertEqual(bill.needed_balance(on_day, last_pay_day), 70)
