"""Order Entry Gateway e Matching Engine testados isoladamente (standalone), sem base de dados."""

import pytest

from app.gateway import OrderEntryGateway
from app.matching_engine import MatchingEngine

REFS = {"EDP": 4.50}


@pytest.fixture
def oeg():
    return OrderEntryGateway(MatchingEngine(lambda: "2026-11-02"), REFS)


@pytest.mark.parametrize("qty, status", [(0, "REJECTED"), (1, "NEW"), (10_000, "NEW"), (10_001, "REJECTED")])
def test_limites_de_quantidade(oeg, qty, status):
    assert oeg.submit("EDP", "BUY", qty, 4.50).status == status


@pytest.mark.parametrize("price, reason", [
    (4.505, "Preço fora do tick size"),
    (4.96, "Preço fora das bandas"),
    (4.04, "Preço fora das bandas"),
    (0, "Preço inválido"),
])
def test_rejeicoes_por_preco(oeg, price, reason):
    order = oeg.submit("EDP", "BUY", 100, price)
    assert (order.status, order.reject_reason) == ("REJECTED", reason)


@pytest.mark.parametrize("price", [4.05, 4.95])
def test_limites_das_bandas_sao_aceites(oeg, price):
    assert oeg.submit("EDP", "BUY", 100, price).status == "NEW"


def test_simbolo_desconhecido(oeg):
    assert oeg.submit("XPTO", "BUY", 100, 4.50).reject_reason == "Símbolo desconhecido"


def test_negocio_ao_preco_do_livro(oeg):
    oeg.submit("EDP", "SELL", 100, 4.50)
    buy = oeg.submit("EDP", "BUY", 100, 4.55)
    trade = oeg.engine.trades[-1]
    assert buy.status == "FILLED"
    assert (trade.qty, trade.price, trade.trade_date) == (100, 4.50, "2026-11-02")


def test_execucao_parcial(oeg):
    sell = oeg.submit("EDP", "SELL", 100, 4.50)
    oeg.submit("EDP", "BUY", 40, 4.50)
    assert (sell.status, sell.remaining) == ("PARTIALLY_FILLED", 60)
    assert oeg.engine.book("EDP")["asks"][0]["remaining"] == 60


def test_prioridade_tempo(oeg):
    first = oeg.submit("EDP", "BUY", 100, 4.48)
    second = oeg.submit("EDP", "BUY", 100, 4.48)
    oeg.submit("EDP", "SELL", 100, 4.48)
    assert (first.status, second.status) == ("FILLED", "NEW")


def test_prioridade_preco(oeg):
    cheap = oeg.submit("EDP", "SELL", 100, 4.52)
    best = oeg.submit("EDP", "SELL", 100, 4.51)
    oeg.submit("EDP", "BUY", 100, 4.55)
    assert (best.status, cheap.status) == ("FILLED", "NEW")


def test_ordem_de_mercado_sem_contraparte_e_cancelada(oeg):
    order = oeg.submit("EDP", "BUY", 100, None)
    assert order.status == "CANCELLED"
    assert oeg.engine.book("EDP")["bids"] == []


def test_ordem_executada_nao_pode_ser_cancelada(oeg):
    sell = oeg.submit("EDP", "SELL", 100, 4.50)
    oeg.submit("EDP", "BUY", 100, 4.50)
    assert oeg.cancel(sell.order_id) is False


def test_restauro_do_estado(oeg):
    oeg.submit("EDP", "SELL", 100, 4.50)
    oeg.submit("EDP", "BUY", 40, 4.50)
    old = oeg.engine
    new = MatchingEngine(lambda: "2026-11-02")
    new.restore(list(old.orders.values()), list(old.trades))
    assert new.book("EDP")["asks"][0]["remaining"] == 60
    assert new.next_order_id() == "O00003"
