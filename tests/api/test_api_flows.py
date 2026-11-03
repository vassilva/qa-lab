"""Fluxos de ponta a ponta pela API: ordem → negócio → instrução de liquidação → liquidada em T+2."""


def _order(client, side, qty, price, symbol="EDP"):
    return client.post("/api/orders", json={"symbol": symbol, "side": side, "qty": qty, "price": price})


def test_health(client):
    body = client.get("/health").get_json()
    assert body["status"] == "UP" and body["database_ok"] is True


def test_ordem_rejeitada_devolve_422(client):
    r = _order(client, "BUY", 10_001, 4.50)
    assert r.status_code == 422
    assert r.get_json()["order"]["reject_reason"] == "Quantidade inválida"


def test_pedido_mal_formado_devolve_400(client):
    assert client.post("/api/orders", json={"symbol": "EDP"}).status_code == 400


def test_negocio_gera_instrucao_t_mais_2(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    [ins] = client.get("/api/settlement/instructions").get_json()
    assert ins["status"] == "PENDING"
    assert ins["amount"] == 450.0
    assert (ins["trade_date"], ins["intended_settlement_date"]) == ("2026-11-02", "2026-11-04")


def test_eod_liquida_so_na_data_prevista(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)                      # negociado segunda 2/11, liquida quarta 4/11
    assert client.post("/api/eod").get_json()["settled"] == 0      # fecho de segunda
    assert client.post("/api/eod").get_json()["settled"] == 0      # fecho de terça
    result = client.post("/api/eod").get_json()                    # fecho de quarta
    assert (result["business_date"], result["settled"]) == ("2026-11-04", 1)
    [ins] = client.get("/api/settlement/instructions").get_json()
    assert (ins["status"], ins["settled_on"]) == ("SETTLED", "2026-11-04")


def test_instrucao_retida_nao_liquida(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    assert client.post("/api/settlement/instructions/S00001/hold").status_code == 200
    for _ in range(3):
        client.post("/api/eod")
    [ins] = client.get("/api/settlement/instructions").get_json()
    assert ins["status"] == "ON_HOLD"
    assert client.post("/api/settlement/instructions/S00001/release").status_code == 200
    client.post("/api/eod")
    assert client.get("/api/settlement/instructions").get_json()[0]["status"] == "SETTLED"


def test_hold_numa_instrucao_liquidada_e_recusado(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    for _ in range(3):
        client.post("/api/eod")
    assert client.post("/api/settlement/instructions/S00001/hold").status_code == 409


def test_data_de_negocio_nao_aceita_fim_de_semana(client):
    assert client.post("/api/business-date", json={"date": "2026-11-07"}).status_code == 400


def test_eod_avanca_para_o_proximo_dia_util(client):
    client.post("/api/business-date", json={"date": "2026-11-06"})          # sexta
    assert client.post("/api/eod").get_json()["next_business_date"] == "2026-11-09"


def test_reconciliacao_todos_os_negocios_tem_instrucao(client):
    _order(client, "SELL", 300, 4.50)
    _order(client, "BUY", 100, 4.50)
    _order(client, "BUY", 200, 4.55)
    r = client.post("/api/query", json={"sql": (
        "SELECT t.trade_id FROM trades t LEFT JOIN settlement_instructions s "
        "ON s.trade_id = t.trade_id WHERE s.instruction_id IS NULL")}).get_json()
    assert r["rows"] == []


def test_consola_sql_recusa_escrita(client):
    assert client.post("/api/query", json={"sql": "DELETE FROM orders"}).status_code == 400
