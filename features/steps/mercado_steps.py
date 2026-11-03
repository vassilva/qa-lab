"""Passos BDD da negociação: Order Entry Gateway, Matching Engine e Market Data."""

from behave import step

SIDES = {"compra": "BUY", "venda": "SELL"}
BOOK_SIDES = {"compras": "bids", "vendas": "asks"}


def _price(text):
    return None if text == "mercado" else float(text)


def submit(context, alias, lado, qtd, simbolo, preco):
    body = {"symbol": simbolo, "side": SIDES[lado], "qty": qtd, "price": preco}
    r = context.api.post("/api/orders", body)
    assert r.status_code in (201, 422), f"Resposta inesperada {r.status_code}: {r.text}"
    context.last_response = r
    context.orders[alias] = r.json()["order"]
    return r


def current_order(context, alias):
    assert alias in context.orders, f"A ordem '{alias}' não foi criada neste cenário"
    order_id = context.orders[alias]["order_id"]
    r = context.api.get(f"/api/orders/{order_id}")
    assert r.status_code == 200, f"Ordem {order_id} não encontrada: {r.text}"
    return r.json()


# ---------------------------------------------------------------------- contexto
@step('um mercado limpo com a data de negócio "{data}"')
def step_mercado_limpo(context, data):
    r = context.api.post("/api/reset")
    assert r.status_code == 200, f"Não foi possível reiniciar o ambiente: {r.text}"
    r = context.api.post("/api/business-date", {"date": data})
    assert r.status_code == 200, f"Não foi possível definir a data de negócio {data}: {r.text}"


# ---------------------------------------------------------------------- ordens
@step('que existe uma ordem "{alias}" de {lado} de {qtd:d} "{simbolo}" a {preco} EUR')
def step_ordem_existente(context, alias, lado, qtd, simbolo, preco):
    r = submit(context, alias, lado, qtd, simbolo, _price(preco))
    assert r.status_code == 201, f"A ordem de preparação '{alias}' foi rejeitada: {r.text}"


@step('é submetida uma ordem "{alias}" de {lado} de {qtd:d} "{simbolo}" a {preco} EUR')
def step_submeter_ordem(context, alias, lado, qtd, simbolo, preco):
    submit(context, alias, lado, qtd, simbolo, _price(preco))


@step('é submetida uma ordem "{alias}" de {lado} de {qtd:d} "{simbolo}" a mercado')
def step_submeter_ordem_mercado(context, alias, lado, qtd, simbolo):
    submit(context, alias, lado, qtd, simbolo, None)


@step('o participante tenta cancelar a ordem "{alias}"')
def step_cancelar(context, alias):
    context.last_response = context.api.delete(f"/api/orders/{context.orders[alias]['order_id']}")


# ---------------------------------------------------------------------- verificações
@step('a ordem "{alias}" fica no estado "{estado}"')
def step_estado_ordem(context, alias, estado):
    order = current_order(context, alias)
    assert order["status"] == estado, (
        f"Ordem {alias} ({order['order_id']}): esperado {estado}, obtido {order['status']} "
        f"(motivo: {order.get('reject_reason')})")


@step('a ordem "{alias}" fica no estado "{estado}" com {resto:d} por executar')
def step_estado_e_restante(context, alias, estado, resto):
    order = current_order(context, alias)
    assert (order["status"], order["remaining"]) == (estado, resto), (
        f"Ordem {alias}: esperado {estado} com {resto} por executar, "
        f"obtido {order['status']} com {order['remaining']}")


@step('a ordem "{alias}" é rejeitada com o motivo "{motivo}"')
def step_rejeitada(context, alias, motivo):
    assert context.last_response.status_code == 422, (
        f"Esperado HTTP 422, obtido {context.last_response.status_code}: {context.last_response.text}")
    order = current_order(context, alias)
    assert (order["status"], order["reject_reason"]) == ("REJECTED", motivo), (
        f"Esperado REJECTED / {motivo}, obtido {order['status']} / {order['reject_reason']}")


@step("o cancelamento é recusado")
def step_cancelamento_recusado(context):
    assert context.last_response.status_code == 409, (
        f"Esperado HTTP 409, obtido {context.last_response.status_code}: {context.last_response.text}")


@step("existe {n:d} negócio de {qtd:d} ações a {preco} EUR")
def step_um_negocio(context, n, qtd, preco):
    trades = context.api.get("/api/trades").json()
    assert len(trades) == n, f"Esperado {n} negócio(s), obtido {len(trades)}: {trades}"
    last = trades[0]
    assert (last["qty"], last["price"]) == (qtd, float(preco)), (
        f"Esperado {qtd} a {preco}, obtido {last['qty']} a {last['price']}")


@step("existem {n:d} negócios")
def step_n_negocios(context, n):
    trades = context.api.get("/api/trades").json()
    assert len(trades) == n, f"Esperado {n} negócios, obtido {len(trades)}"


@step("não existe nenhum negócio")
def step_sem_negocios(context):
    trades = context.api.get("/api/trades").json()
    assert trades == [], f"Não era esperado nenhum negócio: {trades}"


@step('o livro de {lado_livro} de "{simbolo}" fica vazio')
def step_livro_vazio(context, lado_livro, simbolo):
    book = context.api.get(f"/api/book/{simbolo}").json()
    entries = book[BOOK_SIDES[lado_livro]]
    assert entries == [], f"O livro de {lado_livro} de {simbolo} devia estar vazio: {entries}"
