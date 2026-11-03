"""
Servidor web do QA Lab (Flask): página da mini bolsa + API REST.

Componentes (inspirados na arquitetura pública da Euronext):
    Order Entry Gateway (app/gateway.py)  →  Matching Engine (app/matching_engine.py)
    Market Data (livro de ordens e negócios, nesta API)  →  Settlement T+2 (app/settlement.py)

Ambiente: ENV_NAME (QA, UAT ou LOCAL) e APP_VERSION aparecem na página e em /health.
"""

import os
import threading
from datetime import date

from flask import Flask, abort, jsonify, request, send_from_directory

from app.db import Database
from app.gateway import OrderEntryGateway
from app.logs import get_logger
from app.matching_engine import MatchingEngine
from app.model import challenge_mode
from app.settlement import SettlementService, is_business_day

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CHECKLIST_FILE = os.path.join(BASE_DIR, "checklist.json")

ENV_NAME = os.environ.get("ENV_NAME", "local").upper()
APP_VERSION = os.environ.get("APP_VERSION", "local")
REFERENCE_PRICES = {"EDP": 4.50, "GALP": 15.20, "BCP": 0.65, "NOS": 3.80}

log = get_logger("API")
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))
lock = threading.RLock()           # uma operação de negócio de cada vez (simples e previsível)

database = Database()
settlement = SettlementService(database)
engine = gateway = None


def _build_components(restore=True):
    global engine, gateway
    engine = MatchingEngine(trade_date_provider=lambda: settlement.business_date().isoformat())
    if restore:
        engine.restore(database.load_orders(), database.load_trades())
    gateway = OrderEntryGateway(engine, REFERENCE_PRICES)


_build_components()


# ---------------------------------------------------------------------- utilitários
def _json():
    return request.get_json(silent=True) or request.form or {}


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


@app.errorhandler(Exception)
def unexpected_error(err):
    from werkzeug.exceptions import HTTPException
    if isinstance(err, HTTPException):
        return err
    try:
        database.rollback()            # nunca deixar uma transação abortada pendurada
    except Exception:  # noqa: BLE001
        pass
    log.exception("Erro inesperado: %s", err)
    return jsonify(error=f"Erro interno: {err}"), 500


# ---------------------------------------------------------------------- páginas
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/checklist")
def checklist_page():
    return send_from_directory(app.static_folder, "checklist.html")


@app.get("/api/checklist")
def checklist_data():
    with open(CHECKLIST_FILE, encoding="utf-8") as f:
        return app.response_class(f.read(), mimetype="application/json")


@app.get("/reports/")
@app.get("/reports/<path:name>")
def reports(name="index.html"):
    if not os.path.isfile(os.path.join(REPORTS_DIR, name)):
        return jsonify(error="Ainda não há relatórios. Corre scripts/run_tests.sh"), 404
    return send_from_directory(REPORTS_DIR, name)


# ---------------------------------------------------------------------- estado do serviço
@app.get("/health")
def health():
    with lock:
        db_ok = database.ping()
        body = dict(status="UP" if db_ok else "DEGRADED", environment=ENV_NAME, version=APP_VERSION,
                    database=database.engine_name, database_ok=db_ok, challenge_mode=challenge_mode(),
                    orders=len(engine.orders), trades=len(engine.trades))
    return jsonify(body), 200 if db_ok else 503


@app.get("/api/symbols")
def symbols():
    return jsonify([{"symbol": s, "reference_price": p} for s, p in sorted(REFERENCE_PRICES.items())])


# ---------------------------------------------------------------------- Order Entry Gateway
@app.post("/api/orders")
def submit_order():
    symbol, side, qty, price = _parse_order(_json())
    with lock:
        trades_before = len(engine.trades)
        order = gateway.submit(symbol, side, qty, price)
        new_trades = engine.trades[trades_before:]
        database.save_order(order)
        for t in new_trades:
            database.save_order(engine.orders[t.buy_order_id])
            database.save_order(engine.orders[t.sell_order_id])
            database.save_trade(t)
            settlement.create_instruction(t)
        database.commit()
    status = 422 if order.status == "REJECTED" else 201
    return jsonify(order=order.to_dict(), trades=[t.to_dict() for t in new_trades]), status


@app.delete("/api/orders/<order_id>")
def cancel_order(order_id):
    with lock:
        ok = gateway.cancel(order_id)
        if ok:
            database.save_order(engine.orders[order_id])
            database.commit()
    if not ok:
        return jsonify(error=f"Não foi possível cancelar {order_id}"), 409
    return jsonify(order=engine.orders[order_id].to_dict())


@app.get("/api/orders")
def list_orders():
    status = (request.args.get("status") or "").upper()
    with lock:
        orders = [o.to_dict() for o in engine.orders.values() if not status or o.status == status]
    return jsonify(list(reversed(orders)))


@app.get("/api/orders/<order_id>")
def get_order(order_id):
    order = engine.orders.get(order_id)
    if order is None:
        return jsonify(error="Ordem não encontrada"), 404
    return jsonify(order.to_dict())


# ---------------------------------------------------------------------- Market Data
@app.get("/api/book/<symbol>")
def order_book(symbol):
    with lock:
        return jsonify(engine.book(symbol.upper()))


@app.get("/api/trades")
def trades():
    symbol = (request.args.get("symbol") or "").upper()
    with lock:
        items = [t.to_dict() for t in engine.trades if not symbol or t.symbol == symbol]
    return jsonify(list(reversed(items)))


# ---------------------------------------------------------------------- Settlement
@app.get("/api/business-date")
def get_business_date():
    with lock:
        return jsonify(business_date=settlement.business_date().isoformat())


@app.post("/api/business-date")
def set_business_date():
    try:
        new_date = date.fromisoformat(str(_json().get("date", "")))
    except ValueError:
        abort(400, description="Data inválida: usa o formato AAAA-MM-DD")
    if not is_business_day(new_date):
        abort(400, description=f"{new_date.isoformat()} não é um dia útil (fim de semana ou feriado TARGET2)")
    with lock:
        settlement.set_business_date(new_date)
    return jsonify(business_date=new_date.isoformat())


@app.get("/api/settlement/instructions")
def settlement_instructions():
    with lock:
        rows = database.list_instructions((request.args.get("status") or "").upper() or None)
        database.rollback()
    return jsonify(rows)


@app.post("/api/settlement/instructions/<instruction_id>/<action>")
def settlement_action(instruction_id, action):
    if action not in ("hold", "release"):
        abort(400, description="Ação inválida: usa hold ou release")
    with lock:
        ok = settlement.hold(instruction_id) if action == "hold" else settlement.release(instruction_id)
        instruction = database.get_instruction(instruction_id)
        database.rollback()
    if not ok:
        return jsonify(error=f"Não foi possível aplicar {action} a {instruction_id}", instruction=instruction), 409
    return jsonify(instruction)


@app.post("/api/eod")
def end_of_day():
    with lock:
        result = settlement.run_eod()
    return jsonify(result)


# ---------------------------------------------------------------------- administração
@app.post("/api/reset")
def reset():
    with lock:
        database.reset()
        _build_components(restore=False)
        log.info("Ambiente %s reiniciado: ordens, negócios e instruções apagados", ENV_NAME)
    return jsonify(status="reset")


@app.post("/api/query")
def query():
    sql = str(_json().get("sql", ""))
    try:
        with lock:
            cols, rows = database.run_query(sql)
    except Exception as exc:  # noqa: BLE001 - devolver o erro SQL ao utilizador
        return jsonify(error=str(exc)), 400
    return jsonify(columns=cols, rows=rows)


def main():
    port = int(os.environ.get("PORT", "8000"))
    log.info("QA Lab %s versão %s a arrancar na porta %d (base de dados: %s, modo desafio: %s)",
             ENV_NAME, APP_VERSION, port, database.engine_name, challenge_mode())
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
