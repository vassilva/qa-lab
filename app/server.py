"""
Servidor web do QA Lab (Flask).

Página:  http://localhost:8000/
API:     ver README.md (secção "API")
"""

import os
import threading

from flask import Flask, jsonify, request, send_from_directory, abort

from app.db import Database
from app.engine import MatchingEngine, Order, challenge_mode, logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

REFERENCE_PRICES = {"EDP": 4.50, "GALP": 15.20, "BCP": 0.65, "NOS": 3.80}

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))
lock = threading.Lock()
engine = MatchingEngine(REFERENCE_PRICES)
database = Database()
CHECKLIST_FILE = os.path.join(BASE_DIR, "checklist.json")


def _new_engine():
    global engine
    engine = MatchingEngine(REFERENCE_PRICES)
    database.reset()
    logger.info("Ambiente reiniciado: livro de ordens e base de dados vazios")


def _parse_order(data):
    try:
        symbol = str(data["symbol"]).upper().strip()
        side = str(data["side"]).upper().strip()
        qty = int(data["qty"])
        raw_price = data.get("price")
        price = None if raw_price in (None, "", "MKT") else round(float(raw_price), 6)
    except (KeyError, TypeError, ValueError) as exc:
        abort(400, description=f"Pedido inválido: {exc}")
    return symbol, side, qty, price


@app.errorhandler(400)
def bad_request(err):
    return jsonify(error=err.description), 400


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/health")
def health():
    db_ok = database.ping()
    body = dict(status="UP" if db_ok else "DEGRADED", database="postgresql" if database.is_postgres else "sqlite",
                database_ok=db_ok, challenge_mode=challenge_mode(),
                orders=len(engine.orders), trades=len(engine.trades))
    return jsonify(body), 200 if db_ok else 503


@app.get("/checklist")
def checklist_page():
    return send_from_directory(app.static_folder, "checklist.html")


@app.get("/api/checklist")
def checklist_data():
    with open(CHECKLIST_FILE, encoding="utf-8") as f:
        return app.response_class(f.read(), mimetype="application/json")


@app.get("/api/symbols")
def symbols():
    return jsonify([{"symbol": s, "reference_price": REFERENCE_PRICES.get(s)} for s in engine.symbols()])


@app.post("/api/orders")
def submit_order():
    symbol, side, qty, price = _parse_order(request.get_json(silent=True) or request.form)
    with lock:
        order = Order(engine.next_order_id(), symbol, side, qty, price)
        trades_before = len(engine.trades)
        engine.submit(order)
        new_trades = engine.trades[trades_before:]
        database.save_order(order)
        for t in new_trades:
            database.save_order(engine.orders[t.buy_order_id])
            database.save_order(engine.orders[t.sell_order_id])
            database.save_trade(t)
        database.commit()
    status = 422 if order.status == "REJECTED" else 201
    return jsonify(order=order.to_dict(), trades=[t.to_dict() for t in new_trades]), status


@app.delete("/api/orders/<order_id>")
def cancel_order(order_id):
    with lock:
        ok = engine.cancel(order_id)
        if ok:
            database.save_order(engine.orders[order_id])
            database.commit()
    if not ok:
        return jsonify(error=f"Não foi possível cancelar {order_id}"), 409
    return jsonify(order=engine.orders[order_id].to_dict())


@app.get("/api/orders")
def list_orders():
    status = request.args.get("status")
    orders = [o.to_dict() for o in engine.orders.values() if not status or o.status == status.upper()]
    return jsonify(list(reversed(orders)))


@app.get("/api/orders/<order_id>")
def get_order(order_id):
    order = engine.orders.get(order_id)
    if order is None:
        return jsonify(error="Ordem não encontrada"), 404
    return jsonify(order.to_dict())


@app.get("/api/book/<symbol>")
def order_book(symbol):
    return jsonify(engine.book(symbol.upper()))


@app.get("/api/trades")
def trades():
    symbol = request.args.get("symbol")
    items = [t.to_dict() for t in engine.trades if not symbol or t.symbol == symbol.upper()]
    return jsonify(list(reversed(items)))


@app.post("/api/reset")
def reset():
    with lock:
        _new_engine()
    return jsonify(status="reset")


@app.post("/api/query")
def query():
    sql = (request.get_json(silent=True) or {}).get("sql", "")
    try:
        cols, rows = database.run_query(sql)
    except Exception as exc:  # noqa: BLE001 - devolver o erro SQL ao utilizador
        return jsonify(error=str(exc)), 400
    return jsonify(columns=cols, rows=rows)


@app.get("/reports/")
@app.get("/reports/<path:name>")
def reports(name="index.html"):
    if not os.path.isdir(REPORTS_DIR):
        return jsonify(error="Ainda não há relatórios. Corre ./scripts/run_tests.sh"), 404
    if not os.path.exists(os.path.join(REPORTS_DIR, name)):
        abort(404)
    return send_from_directory(REPORTS_DIR, name)


def main():
    port = int(os.environ.get("PORT", "8000"))
    logger.info("QA Lab a arrancar na porta %d (modo desafio: %s)", port, challenge_mode())
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
