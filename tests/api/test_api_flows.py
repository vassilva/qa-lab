"""End-to-end flows through the API: order → trade → settlement instruction → settled at T+2."""


def _order(client, side, qty, price, symbol="EDP"):
    return client.post("/api/orders", json={"symbol": symbol, "side": side, "qty": qty, "price": price})


def test_health(client):
    body = client.get("/health").get_json()
    assert body["status"] == "UP" and body["database_ok"] is True


def test_rejected_order_returns_422(client):
    r = _order(client, "BUY", 10_001, 4.50)
    assert r.status_code == 422
    assert r.get_json()["order"]["reject_reason"] == "Invalid quantity"


def test_malformed_request_returns_400(client):
    assert client.post("/api/orders", json={"symbol": "EDP"}).status_code == 400


def test_trade_creates_t_plus_2_instruction(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    [ins] = client.get("/api/settlement/instructions").get_json()
    assert ins["status"] == "PENDING"
    assert ins["amount"] == 450.0
    assert (ins["trade_date"], ins["intended_settlement_date"]) == ("2026-11-02", "2026-11-04")


def test_eod_settles_only_on_intended_date(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)                      # traded Monday 2/11, settles Wednesday 4/11
    assert client.post("/api/eod").get_json()["settled"] == 0      # Monday EOD
    assert client.post("/api/eod").get_json()["settled"] == 0      # Tuesday EOD
    result = client.post("/api/eod").get_json()                    # Wednesday EOD
    assert (result["business_date"], result["settled"]) == ("2026-11-04", 1)
    [ins] = client.get("/api/settlement/instructions").get_json()
    assert (ins["status"], ins["settled_on"]) == ("SETTLED", "2026-11-04")


def test_held_instruction_does_not_settle(client):
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


def test_hold_on_settled_instruction_is_refused(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    for _ in range(3):
        client.post("/api/eod")
    assert client.post("/api/settlement/instructions/S00001/hold").status_code == 409


def test_business_date_rejects_weekend(client):
    assert client.post("/api/business-date", json={"date": "2026-11-07"}).status_code == 400


def test_eod_moves_to_next_business_day(client):
    client.post("/api/business-date", json={"date": "2026-11-06"})          # Friday
    assert client.post("/api/eod").get_json()["next_business_date"] == "2026-11-09"


def test_cross_system_reconciliation(client):
    _order(client, "SELL", 300, 4.50)
    _order(client, "BUY", 100, 4.50)
    _order(client, "BUY", 200, 4.55)
    r = client.get("/api/reconciliation").get_json()
    assert (r["ok"], r["trades"], r["instructions"]) == (True, 2, 2)


def test_sql_console_refuses_writes(client):
    assert client.post("/api/query", json={"sql": "DELETE FROM orders"}).status_code == 400
