"""
Testes de integração Trading ↔ Settlement ↔ T2S e testes de contrato (TradeExecuted v1).
Correm no mesmo processo, com o barramento em memória; o comportamento é o mesmo que com o Kafka.
"""

import copy
import json

import pytest

from app.contracts import validate_trade_executed


def _trade(client, symbol="EDP", qty=100, price=4.50):
    client.post("/api/orders", json={"symbol": symbol, "side": "SELL", "qty": qty, "price": price})
    r = client.post("/api/orders", json={"symbol": symbol, "side": "BUY", "qty": qty, "price": price})
    return r.get_json()["trades"][0]


def _instructions(client, **filters):
    qs = "&".join(f"{k}={v}" for k, v in filters.items())
    return client.get("/api/settlement/instructions" + (f"?{qs}" if qs else "")).get_json()


def _published_event(services, trade_id):
    server = services[0]
    with server.lock:
        ev = server.database.outbox_event_for_trade(trade_id)
        server.database.rollback()
    return json.loads(ev["payload"])


# ---------------------------------------------------------------------- contrato
def test_evento_publicado_respeita_o_contrato(client, services):
    trade = _trade(client)
    event = _published_event(services, trade["trade_id"])
    assert validate_trade_executed(event) == []
    assert event["trade"] == {k: trade[k] for k in event["trade"]}


@pytest.mark.parametrize("mutate, erro", [
    (lambda e: e.pop("event_id"), "campo obrigatório em falta: event_id"),
    (lambda e: e["trade"].update(qty=0), "$.trade.qty: 0 < mínimo 1"),
    (lambda e: e["trade"].update(price="4.50"), "$.trade.price: tipo esperado number"),
    (lambda e: e["trade"].update(trade_date="06/11/2026"), "$.trade.trade_date"),
    (lambda e: e.update(schema_version=2), "$.schema_version: esperado 1"),
    (lambda e: e["trade"].update(isin="PTEDP0AM0009"), "campo não previsto no contrato: isin"),
])
def test_contrato_rejeita_eventos_invalidos(client, services, mutate, erro):
    event = copy.deepcopy(_published_event(services, _trade(client)["trade_id"]))
    mutate(event)
    assert any(erro in e for e in validate_trade_executed(event))


# ---------------------------------------------------------------------- consumidor
def test_evento_duplicado_nao_cria_segunda_instrucao(client):
    trade = _trade(client)
    assert client.post(f"/api/integration/replay/{trade['trade_id']}").status_code == 200
    assert len(_instructions(client, trade_id=trade["trade_id"])) == 1


def test_mensagem_invalida_vai_para_a_fila_de_erros(client, services):
    r = client.post("/api/integration/publish-raw", json={"event_type": "TradeExecuted", "trade": {"qty": -1}})
    assert r.get_json()["contract_errors"]
    rejected = services[1].app.test_client().get("/api/rejected-events").get_json()
    assert len(rejected) == 1 and "event_id" in rejected[0]["reason"]
    assert _instructions(client) == []


def test_evento_de_geracao_anterior_e_ignorado(client, services):
    event = copy.deepcopy(_published_event(services, _trade(client)["trade_id"]))
    client.post("/api/reset")                               # nova geração do ambiente
    client.post("/api/business-date", json={"date": "2026-11-02"})
    client.post("/api/integration/publish-raw", json=event)  # evento antigo ainda "em trânsito"
    assert _instructions(client) == []


def test_settlement_indisponivel_negocio_fica_na_outbox_e_e_entregue_depois(client, services):
    server, settlement_client = services[0], services[1].app.test_client()
    settlement_client.post("/api/consumer/pause")
    trade = _trade(client)                                   # o Trading continua a negociar
    assert client.get("/health").get_json()["outbox_pending"] == 1
    assert client.get("/api/reconciliation").get_json()["missing_in_settlement"] == [trade["trade_id"]]
    settlement_client.post("/api/consumer/resume")
    server.publish_pending()                                 # o publicador volta a tentar
    assert client.get("/api/reconciliation").get_json()["ok"] is True
    assert client.get("/health").get_json()["outbox_pending"] == 0


# ---------------------------------------------------------------------- T2S
def _eod_until_due(client, n=3):
    return [client.post("/api/eod").get_json() for _ in range(n)]


def test_t2s_rejeita_e_a_instrucao_e_reciclada(client):
    _trade(client)                                           # negociado 2/11, liquida 4/11
    client.post("/api/t2s/mode", json={"mode": "rejeitar_simbolo", "symbol": "EDP"})
    last = _eod_until_due(client)[-1]
    assert (last["settled"], last["failed"]) == (0, 1)
    [ins] = _instructions(client)
    assert ins["status"] == "FAILED" and "Títulos insuficientes" in ins["fail_reason"]
    client.post("/api/t2s/mode", json={"mode": "normal"})
    assert client.post("/api/eod").get_json()["settled"] == 1
    assert _instructions(client)[0]["attempts"] == 2


def test_t2s_indisponivel_nada_e_liquidado_e_recupera_no_dia_seguinte(client):
    _trade(client)
    client.post("/api/t2s/mode", json={"mode": "indisponivel"})
    last = _eod_until_due(client)[-1]
    assert last["settled"] == 0 and last["t2s"].startswith("indisponível")
    client.post("/api/t2s/mode", json={"mode": "normal"})
    assert client.post("/api/eod").get_json()["settled"] == 1


def test_t2s_so_rejeita_o_simbolo_indicado(client):
    _trade(client, "EDP")
    _trade(client, "GALP", price=15.20)
    client.post("/api/t2s/mode", json={"mode": "rejeitar_simbolo", "symbol": "EDP"})
    _eod_until_due(client)
    states = {i["symbol"]: i["status"] for i in _instructions(client)}
    assert states == {"EDP": "FAILED", "GALP": "SETTLED"}


def test_modo_invalido_do_simulador(client):
    assert client.post("/api/t2s/mode", json={"mode": "explodir"}).status_code == 400


def test_reconciliacao_deteta_diferenca_de_montante(client, services):
    trade = _trade(client)
    st = services[1]
    with st.lock:
        st.database.execute("UPDATE settlement_instructions SET amount = 999 WHERE trade_id = ?", (trade["trade_id"],))
        st.database.commit()
    r = client.get("/api/reconciliation").get_json()
    assert r["ok"] is False and r["mismatched"][0]["trade_id"] == trade["trade_id"]
