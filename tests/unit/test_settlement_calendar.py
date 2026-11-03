"""Settlement calendar: TARGET2 business days and the T+2 cycle."""

from datetime import date

import pytest

from app.settlement import add_business_days, easter_sunday, is_business_day, target2_holidays


@pytest.mark.parametrize("year, expected", [(2026, date(2026, 4, 5)), (2027, date(2027, 3, 28))])
def test_easter_sunday(year, expected):
    assert easter_sunday(year) == expected


def test_target2_holidays_2026():
    assert target2_holidays(2026) == {
        date(2026, 1, 1), date(2026, 4, 3), date(2026, 4, 6),
        date(2026, 5, 1), date(2026, 12, 25), date(2026, 12, 26),
    }


@pytest.mark.parametrize("trade_date, expected", [
    (date(2026, 11, 2), date(2026, 11, 4)),    # Monday → Wednesday
    (date(2026, 11, 5), date(2026, 11, 9)),    # Thursday → Monday (skips the weekend)
    (date(2026, 11, 6), date(2026, 11, 10)),   # Friday → Tuesday
    (date(2026, 12, 23), date(2026, 12, 28)),  # 24/12 counts, 25 and 26 are holidays, 27 is a Sunday
    (date(2026, 4, 2), date(2026, 4, 8)),      # Easter: 3/4 and 6/4 are holidays
])
def test_t_plus_2_settlement_date(trade_date, expected):
    assert add_business_days(trade_date, 2) == expected


@pytest.mark.parametrize("day, business", [
    (date(2026, 11, 7), False),   # Saturday
    (date(2026, 12, 25), False),  # Christmas
    (date(2026, 12, 24), True),   # Christmas Eve is a TARGET2 business day
    (date(2026, 6, 10), True),    # Portuguese national holiday, but not a TARGET2 holiday
])
def test_business_day(day, business):
    assert is_business_day(day) is business
