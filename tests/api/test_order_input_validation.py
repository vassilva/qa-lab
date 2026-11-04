"""DEF-017: an order with an invalid side returned 500, exposed database details and was not stored.

Equivalence classes for each order field: valid / invalid business value (422, order REJECTED and stored)
/ malformed value that cannot be stored (400, no order created)."""

import pytest


def _post(client, **fields):
    body = {"symbol": "EDP", "side": "BUY", "qty": 10, "price": 4.50}
    body.update(fields)
    return client.post("/api/orders", json=body)


def _orders_in_db(client):
    r = client.post("/api/query", json={"sql": "SELECT order_id, side, status, reject_reason FROM orders ORDER BY order_id"})
    return r.get_json()["rows"]


@pytest.mark.parametrize("side", ["", "HOLD", "X", "BUYY"])
def test_invalid_side_is_rejected_with_422_and_stored(client, side):
    r = _post(client, side=side)
    assert r.status_code == 422
    order = r.get_json()["order"]
    assert order["status"] == "REJECTED" and order["reject_reason"] == "Invalid side"
    # memory (API) and database agree: the rejected order is kept for audit
    assert client.get(f"/api/orders/{order['order_id']}").status_code == 200
    assert _orders_in_db(client) == [[order["order_id"], side, "REJECTED", "Invalid side"]]


def test_lowercase_side_is_still_accepted(client):
    r = _post(client, side="sell")
    assert r.status_code == 201 and r.get_json()["order"]["side"] == "SELL"


@pytest.mark.parametrize("fields", [{"side": "BUY-AND-HOLD"}, {"symbol": "VERYLONGSYMBOL"},
                                    {"qty": 99_999_999_999}, {"price": 123_456_789.0}])
def test_values_that_cannot_be_stored_are_a_bad_request(client, fields):
    r = _post(client, **fields)
    assert r.status_code == 400 and r.get_json()["error"].startswith("Invalid request")
    assert client.get("/api/orders").get_json() == [] and _orders_in_db(client) == []


def test_unexpected_error_does_not_expose_internal_details(client, services, monkeypatch):
    server = services[0]

    def broken(order):
        raise RuntimeError('relation "orders" violates check constraint "orders_side_check"')

    monkeypatch.setattr(server.database, "save_order", broken)
    r = _post(client)
    assert r.status_code == 500
    body = r.get_json()
    assert body["error"] == "Internal error" and len(body["error_id"]) == 12
    assert "orders" not in r.get_data(as_text=True)
