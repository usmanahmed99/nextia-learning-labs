"""Business days: Monday to Friday, except the statutory holidays in the data's period.

The tools compute dates in code and give the model the results (expected date, business days late,
days since delivery). Date arithmetic is a job for code, not for a model.
"""

from datetime import date, timedelta

HOLIDAYS = {date(2026, 9, 7), date(2026, 10, 12)}  # Labour Day, Thanksgiving (Canada)


def is_business_day(day: date) -> bool:
    return day.weekday() < 5 and day not in HOLIDAYS


def add_business_days(start: date, n: int) -> date:
    day = start
    while n:
        day += timedelta(days=1)
        if is_business_day(day):
            n -= 1
    return day


def business_days_between(a: date, b: date) -> int:
    """The number of business days d with a < d <= b (0 when b <= a)."""
    n, day = 0, a
    while day < b:
        day += timedelta(days=1)
        if is_business_day(day):
            n += 1
    return n
