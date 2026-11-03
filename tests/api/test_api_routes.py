"""API and page routes not exercised by the business flows (coverage improvement, see 3.1)."""

import pytest


def _order(client, side, qty, price, symbol="EDP"):
    return client.post("/api/orders", json={"symbol": symbol, "side": side, "qty": qty, "price": price})


@pytest.mark.parametrize("path", ["/", "/checklist", "/docs/", "/docs/qa/test-strategy.md", "/api/checklist",
                                  "/docs-raw/qa/risk-matrix.md", "/api/symbols"])
def test_pages_and_resources_respond(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs/qa/does-not-exist.md", "/docs/qa/test-strategy.txt",
                                  "/docs-raw/../app/server.py", "/api/orders/O99999"])
def test_missing_resources_return_404(client, path):
    assert client.get(path).status_code == 404


def test_cancel_order_in_book(client):
    order_id = _order(client, "BUY", 100, 4.40).get_json()["order"]["order_id"]
    r = client.delete(f"/api/orders/{order_id}")
    assert r.status_code == 200 and r.get_json()["order"]["status"] == "CANCELLED"
    assert client.get("/api/book/EDP").get_json()["bids"] == []
    assert client.delete(f"/api/orders/{order_id}").status_code == 409


def test_order_and_trade_filters(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    _order(client, "BUY", 10_001, 4.50)
    assert len(client.get("/api/orders?status=FILLED").get_json()) == 2
    assert len(client.get("/api/orders?status=REJECTED").get_json()) == 1
    assert len(client.get("/api/trades?symbol=EDP").get_json()) == 1
    assert client.get("/api/trades?symbol=GALP").get_json() == []


def test_instruction_filter_by_status(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    assert len(client.get("/api/settlement/instructions?status=PENDING").get_json()) == 1
    assert client.get("/api/settlement/instructions?status=SETTLED").get_json() == []


@pytest.mark.parametrize("body", [{"date": "06-11-2026"}, {"date": ""}, {}])
def test_business_date_with_invalid_format(client, body):
    assert client.post("/api/business-date", json=body).status_code == 400


def test_invalid_settlement_action(client):
    assert client.post("/api/settlement/instructions/S00001/delete").status_code == 400


def test_release_of_instruction_not_on_hold(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    assert client.post("/api/settlement/instructions/S00001/release").status_code == 409


def test_sql_console_with_syntax_error(client):
    r = client.post("/api/query", json={"sql": "SELECT missing_column FROM orders"})
    assert r.status_code == 400 and "error" in r.get_json()


def test_health_shows_environment_and_version(client):
    body = client.get("/health").get_json()
    assert {"environment", "version", "database", "challenge_mode"} <= body.keys()


def test_documentation_index(client):
    items = client.get("/api/docs").get_json()
    paths = {i["path"] for i in items}
    assert {"qa/test-strategy.md", "defects/README.md", "technical/git.md"} <= paths
    assert all(i["title"] for i in items)
