"""Passos BDD da integração entre sistemas: contrato, idempotência, fila de erros, falhas do Settlement e do T2S."""

import os
import sys

from behave import step

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.contracts import validate_trade_executed  # noqa: E402
from _helpers import eventually, instruction  # noqa: E402


def settlement_health(context):
    return context.api.get("/api/integration").json()["settlement"]


@step("o evento publicado respeita o contrato TradeExecuted v1")
def step_contrato(context):
    tid = context.trade["trade_id"]
    ins = instruction(context)
    # O evento é o que o Settlement recebeu: os campos da instrução vêm dele
    assert (ins["trade_id"], ins["qty"], ins["symbol"]) == (tid, context.trade["qty"], context.trade["symbol"])
    assert round(float(ins["amount"]), 2) == round(context.trade["qty"] * context.trade["price"], 2)
    assert len(ins["event_id"]) == 32


@step("o evento do negócio é entregue outra vez")
def step_replay(context):
    r = context.api.post(f"/api/integration/replay/{context.trade['trade_id']}")
    assert r.status_code == 200, r.text
    eventually(lambda: settlement_health(context)["consumer"]["duplicates"] >= 1,
               "o Settlement não recebeu o evento duplicado")


@step("o negócio continua a ter uma única instrução de liquidação")
def step_unica(context):
    rows = context.api.get(f"/api/settlement/instructions?trade_id={context.trade['trade_id']}").json()
    assert len(rows) == 1, f"Esperada 1 instrução, encontradas {len(rows)}: {rows}"


@step("é publicada uma mensagem com a quantidade 0 e sem identificador do evento")
def step_invalida(context):
    payload = {"event_type": "TradeExecuted", "schema_version": 1, "generation": 0,
               "trade": {"trade_id": "T99999", "symbol": "EDP", "qty": 0, "price": 4.5}}
    assert validate_trade_executed(payload), "a mensagem de teste devia ser inválida"
    r = context.api.post("/api/integration/publish-raw", payload)
    assert r.status_code == 200, r.text


@step("a mensagem aparece nos eventos rejeitados do Settlement")
def step_rejeitada(context):
    eventually(lambda: settlement_health(context)["consumer"]["rejected"] >= 1,
               "o Settlement não rejeitou a mensagem inválida")


@step("não existe nenhuma instrução de liquidação")
def step_sem_instrucoes(context):
    rows = context.api.get("/api/settlement/instructions").json()
    assert rows == [], f"Não era esperada nenhuma instrução: {rows}"


@step("que o Settlement deixou de consumir eventos")
def step_pausa(context):
    base = os.environ.get("SETTLEMENT_URL", "http://localhost:8001")
    r = context.api.session.post(f"{base}/api/consumer/pause", timeout=10)
    assert r.status_code == 200, r.text
    context.settlement_url = base


@step("o Settlement volta a consumir eventos")
def step_retoma(context):
    r = context.api.session.post(f"{context.settlement_url}/api/consumer/resume", timeout=10)
    assert r.status_code == 200, r.text


@step('é executado um negócio de {qtd:d} "{simbolo}" a {preco} EUR sem esperar pelo Settlement')
def step_negocio_sem_esperar(context, qtd, simbolo, preco):
    for side in ("SELL", "BUY"):
        r = context.api.post("/api/orders", {"symbol": simbolo, "side": side, "qty": qtd, "price": float(preco)})
        assert r.status_code == 201, r.text
    context.trade = r.json()["trades"][0]


@step("a reconciliação mostra o negócio em falta no Settlement")
def step_em_falta(context):
    r = context.api.get("/api/reconciliation").json()
    assert context.trade["trade_id"] in r["missing_in_settlement"], r


@step('o T2S rejeita as instruções de "{simbolo}"')
def step_t2s_rejeita(context, simbolo):
    r = context.api.post("/api/t2s/mode", {"mode": "rejeitar_simbolo", "symbol": simbolo})
    assert r.status_code == 200, r.text


@step("o T2S está indisponível")
def step_t2s_em_baixo(context):
    assert context.api.post("/api/t2s/mode", {"mode": "indisponivel"}).status_code == 200


@step("o T2S volta ao normal")
def step_t2s_normal(context):
    assert context.api.post("/api/t2s/mode", {"mode": "normal"}).status_code == 200
