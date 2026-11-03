"""Calendário de liquidação: dias úteis TARGET2 e ciclo T+2."""

from datetime import date

import pytest

from app.settlement import add_business_days, easter_sunday, is_business_day, target2_holidays


@pytest.mark.parametrize("year, expected", [(2026, date(2026, 4, 5)), (2027, date(2027, 3, 28))])
def test_domingo_de_pascoa(year, expected):
    assert easter_sunday(year) == expected


def test_feriados_target2_2026():
    assert target2_holidays(2026) == {
        date(2026, 1, 1), date(2026, 4, 3), date(2026, 4, 6),
        date(2026, 5, 1), date(2026, 12, 25), date(2026, 12, 26),
    }


@pytest.mark.parametrize("trade_date, expected", [
    (date(2026, 11, 2), date(2026, 11, 4)),    # segunda → quarta
    (date(2026, 11, 5), date(2026, 11, 9)),    # quinta → segunda (salta o fim de semana)
    (date(2026, 11, 6), date(2026, 11, 10)),   # sexta → terça
    (date(2026, 12, 23), date(2026, 12, 28)),  # 24/12 conta, 25 e 26 são feriado, 27 é domingo
    (date(2026, 4, 2), date(2026, 4, 8)),      # Páscoa: 3/4 e 6/4 são feriado
])
def test_data_de_liquidacao_t_mais_2(trade_date, expected):
    assert add_business_days(trade_date, 2) == expected


@pytest.mark.parametrize("day, business", [
    (date(2026, 11, 7), False),   # sábado
    (date(2026, 12, 25), False),  # Natal
    (date(2026, 12, 24), True),   # véspera de Natal é dia útil TARGET2
    (date(2026, 6, 10), True),    # feriado nacional português, mas não TARGET2
])
def test_dia_util(day, business):
    assert is_business_day(day) is business
