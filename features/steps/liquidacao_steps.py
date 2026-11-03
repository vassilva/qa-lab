"""Passos BDD da liquidação (Settlement T+2) e da reconciliação na base de dados."""

import os
import sys

from behave import step

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import eventually, instruction  # noqa: E402


@step('é executado um negócio de {qtd:d} "{simbolo}" a {preco} EUR')
def step_negocio(context, qtd, simbolo, preco):
    sell = context.api.post("/api/orders", {"symbol": simbolo, "side": "SELL", "qty": qtd, "price": float(preco)})
    buy = context.api.post("/api/orders", {"symbol": simbolo, "side": "BUY", "qty": qtd, "price": float(preco)})
    assert sell.status_code == 201 and buy.status_code == 201, f"Ordens rejeitadas: {sell.text} / {buy.text}"
    trades = buy.json()["trades"]
    assert len(trades) == 1, f"Esperado 1 negócio, obtido {trades}"
    context.trade = trades[0]
    instruction(context)                     # espera que o Settlement receba o evento


@step('é criada uma instrução de liquidação para "{data}" no estado "{estado}"')
def step_instrucao_criada(context, data, estado):
    ins = instruction(context)
    assert (ins["intended_settlement_date"], ins["status"]) == (data, estado), (
        f"Esperado {data} / {estado}, obtido {ins['intended_settlement_date']} / {ins['status']} "
        f"(negociado em {ins['trade_date']})")


@step("é feito o fecho do dia")
def step_eod(context):
    r = context.api.post("/api/eod")
    assert r.status_code == 200, f"Fecho do dia falhou: {r.text}"
    context.last_response = r


@step("são feitos {n:d} fechos do dia")
def step_n_eod(context, n):
    for _ in range(n):
        step_eod(context)


@step('a instrução fica no estado "{estado}"')
def step_estado_instrucao(context, estado):
    ins = instruction(context)
    assert ins["status"] == estado, f"Esperado {estado}, obtido {ins['status']}"


@step('a instrução fica liquidada em "{data}"')
def step_liquidada(context, data):
    ins = instruction(context)
    assert (ins["status"], ins["settled_on"]) == ("SETTLED", data), (
        f"Esperado SETTLED em {data}, obtido {ins['status']} em {ins['settled_on']}")


@step("a instrução é retida (hold)")
def step_hold(context):
    r = context.api.post(f"/api/settlement/instructions/{instruction(context)['instruction_id']}/hold")
    assert r.status_code == 200, f"Hold recusado: {r.text}"


@step("a instrução é libertada (release)")
def step_release(context):
    r = context.api.post(f"/api/settlement/instructions/{instruction(context)['instruction_id']}/release")
    assert r.status_code == 200, f"Release recusado: {r.text}"


@step('a data de negócio passa a ser "{data}"')
@step('a data de negócio continua a ser "{data}"')
def step_data_negocio(context, data):
    atual = context.api.get("/api/business-date").json()["business_date"]
    assert atual == data, f"Data de negócio esperada {data}, obtida {atual}"


@step('se tenta definir a data de negócio "{data}"')
def step_definir_data(context, data):
    context.last_response = context.api.post("/api/business-date", {"date": data})


@step("o pedido é recusado com o código {codigo:d}")
def step_recusado(context, codigo):
    assert context.last_response.status_code == codigo, (
        f"Esperado HTTP {codigo}, obtido {context.last_response.status_code}: {context.last_response.text}")


@step("todos os negócios têm instrução de liquidação")
@step("a reconciliação entre o Trading e o Settlement não tem diferenças")
def step_reconciliacao(context):
    r = eventually(lambda: (lambda x: x if x.get("ok") else None)(context.api.get("/api/reconciliation").json()),
                   "a reconciliação entre sistemas continua com diferenças")
    assert r["ok"], r


@step("a quantidade executada de cada ordem coincide com os negócios")
def step_quantidades(context):
    rows = context.api.query(
        "SELECT o.order_id, o.qty, o.remaining, COALESCE(SUM(t.qty), 0) AS executado "
        "FROM orders o LEFT JOIN trades t ON o.order_id IN (t.buy_order_id, t.sell_order_id) "
        "WHERE o.status <> 'REJECTED' "
        "GROUP BY o.order_id, o.qty, o.remaining "
        "HAVING o.qty - o.remaining <> COALESCE(SUM(t.qty), 0)")
    assert rows == [], f"Ordens cuja quantidade executada não coincide com os negócios: {rows}"
