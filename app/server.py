"""
Serviço TRADING do QA Lab (Flask): página da mini bolsa + API REST.

Componentes (inspirados na arquitetura pública da Euronext):
    Order Entry Gateway (app/gateway.py) → Matching Engine (app/matching_engine.py) → Market Data (esta API)
Integração com o sistema SETTLEMENT (serviço separado, app/settlement_service.py):
    - cada negócio gera um evento TradeExecuted, gravado na mesma transação (outbox) e publicado no Kafka
    - a data de negócio, as instruções e o fecho do dia são do Settlement: esta API reencaminha esses pedidos

Ambiente: ENV_NAME (QA, UAT ou LOCAL) e APP_VERSION aparecem na página e em /health.
"""

import json
import os
import threading
import time
import uuid
from datetime import date, datetime

from flask import Flask, abort, jsonify, request, send_from_directory

from app import bus as busmod
from app.contracts import validate_trade_executed
from app.db import Database
from app.gateway import OrderEntryGateway
from app.logs import get_logger
from app.matching_engine import MatchingEngine
from app.model import challenge_mode
from app.service_client import ServiceClient, ServiceUnavailable

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CHECKLIST_FILE = os.path.join(BASE_DIR, "checklist.json")

ENV_NAME = os.environ.get("ENV_NAME", "local").upper()
APP_VERSION = os.environ.get("APP_VERSION", "local")
REFERENCE_PRICES = {"EDP": 4.50, "GALP": 15.20, "BCP": 0.65, "NOS": 3.80}

log = get_logger("API")
outbox_log = get_logger("OUTBOX")
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))
lock = threading.RLock()           # uma operação de negócio de cada vez (simples e previsível)

database = Database()
bus = busmod.get_bus()
settlement_api = ServiceClient(os.environ.get("SETTLEMENT_URL", "http://localhost:8001"), "Settlement")
t2s_api = ServiceClient(os.environ.get("T2S_URL", "http://localhost:8002"), "T2S")
engine = gateway = None
_last_business_date = {"value": date.today().isoformat()}


def generation():
    return int(database.get_state("generation") or 0)


def current_business_date():
    """A data de negócio pertence ao Settlement. Se não responder, usa a última conhecida (e regista um aviso)."""
    try:
        status, body = settlement_api.request("GET", "/api/business-date", timeout=2)
        if status == 200:
            _last_business_date["value"] = body["business_date"]
    except ServiceUnavailable as exc:
        log.warning("%s; a usar a última data de negócio conhecida (%s)", exc, _last_business_date["value"])
    return _last_business_date["value"]


def _build_components(restore=True):
    global engine, gateway
    engine = MatchingEngine(trade_date_provider=current_business_date)
    if restore:
        engine.restore(database.load_orders(), database.load_trades())
    gateway = OrderEntryGateway(engine, REFERENCE_PRICES)


_build_components()


# ---------------------------------------------------------------------- outbox → barramento (Kafka)
def trade_event(trade):
    return {
        "event_id": uuid.uuid4().hex,
        "event_type": "TradeExecuted",
        "schema_version": 1,
        "occurred_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "generation": generation(),
        "trade": {"trade_id": trade.trade_id, "symbol": trade.symbol, "qty": trade.qty, "price": trade.price,
                  "trade_date": trade.trade_date, "buy_order_id": trade.buy_order_id,
                  "sell_order_id": trade.sell_order_id},
    }


def publish_pending():
    """Publica os eventos pendentes da outbox, por ordem. Pára no primeiro erro (mantém a ordem dos eventos)."""
    published = 0
    with lock:
        pending = database.pending_outbox()
        database.rollback()
    for ev in pending:
        try:
            bus.publish(ev["topic"], ev["event_key"], json.loads(ev["payload"]))
        except Exception as exc:  # noqa: BLE001 - Kafka/consumidor indisponível: fica pendente
            with lock:
                database.mark_failed(ev["event_id"], f"{exc.__class__.__name__}: {exc}")
                database.commit()
            outbox_log.warning("Evento %s (%s) não publicado: %s. Nova tentativa em breve.",
                               ev["event_id"], ev["event_key"], exc)
            break
        with lock:
            database.mark_published(ev["event_id"])
            database.commit()
        published += 1
        outbox_log.info("Evento %s publicado em %s (negócio %s)", ev["event_id"], ev["topic"], ev["event_key"])
    return published


def _publisher_loop():
    while True:
        try:
            publish_pending()
        except Exception:  # noqa: BLE001
            outbox_log.exception("Erro no publicador da outbox")
        time.sleep(0.5)


if bus.name != "memory":
    threading.Thread(target=_publisher_loop, daemon=True, name="outbox-publisher").start()


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


DOCS_DIR = os.path.join(BASE_DIR, "docs")


@app.get("/docs/")
def docs_index():
    return send_from_directory(app.static_folder, "docs.html")


@app.get("/api/docs")
def docs_list():
    """Índice da documentação: título (primeira linha) de cada ficheiro .md, por pasta."""
    items = []
    for folder, _, files in os.walk(DOCS_DIR):
        for f in sorted(files):
            if f.endswith(".md"):
                path = os.path.relpath(os.path.join(folder, f), DOCS_DIR).replace(os.sep, "/")
                with open(os.path.join(folder, f), encoding="utf-8") as fh:
                    title = fh.readline().lstrip("# ").strip()
                items.append({"path": path, "folder": path.split("/")[0], "title": title})
    return jsonify(sorted(items, key=lambda i: (i["folder"], i["path"])))


@app.get("/docs/<path:name>")
def docs_page(name):
    if not name.endswith(".md") or not os.path.isfile(os.path.join(DOCS_DIR, name)):
        abort(404)
    return send_from_directory(app.static_folder, "docs.html")


@app.get("/docs-raw/<path:name>")
def docs_raw(name):
    if not name.endswith(".md"):
        abort(404)
    return send_from_directory(DOCS_DIR, name, mimetype="text/markdown; charset=utf-8")


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
        outbox = database.outbox_stats()
        database.rollback()
        orders, trades_ = len(engine.orders), len(engine.trades)
    try:
        st_status, _ = settlement_api.request("GET", "/health", timeout=2)
        settlement_ok = st_status == 200
    except ServiceUnavailable:
        settlement_ok = False
    body = dict(status="UP" if db_ok else "DEGRADED", service="trading", environment=ENV_NAME, version=APP_VERSION,
                database=database.engine_name, database_ok=db_ok, challenge_mode=challenge_mode(),
                orders=orders, trades=trades_, bus=bus.name, bus_ok=bus.ping(), settlement_ok=settlement_ok,
                outbox_pending=outbox["pending"])
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
            event = trade_event(t)
            database.insert_outbox(event["event_id"], busmod.TOPIC_TRADES, t.trade_id, json.dumps(event))
        database.commit()                      # negócio e evento gravados juntos (ou nenhum)
    if new_trades and bus.name == "memory":
        publish_pending()                      # em testes: entrega imediata
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


# ---------------------------------------------------------------------- Settlement (reencaminhado ao serviço)
def _forward(method, path, body=None):
    try:
        status, data = settlement_api.request(method, path, body)
    except ServiceUnavailable as exc:
        log.error("%s", exc)
        return jsonify(error=str(exc)), 503
    return jsonify(data), status


@app.get("/api/business-date")
def get_business_date():
    return _forward("GET", "/api/business-date")


@app.post("/api/business-date")
def set_business_date():
    return _forward("POST", "/api/business-date", _json())


@app.get("/api/settlement/instructions")
def settlement_instructions():
    qs = "&".join(f"{k}={v}" for k, v in request.args.items())
    return _forward("GET", "/api/settlement/instructions" + (f"?{qs}" if qs else ""))


@app.post("/api/settlement/instructions/<instruction_id>/<action>")
def settlement_action(instruction_id, action):
    return _forward("POST", f"/api/settlement/instructions/{instruction_id}/{action}")


@app.post("/api/eod")
def end_of_day():
    return _forward("POST", "/api/eod")


# ---------------------------------------------------------------------- integração entre sistemas
def _test_only():
    if ENV_NAME == "UAT":
        abort(403, description="Operação de teste não disponível em UAT")


@app.get("/api/integration")
def integration_status():
    with lock:
        outbox = database.outbox_stats()
        database.rollback()
    try:
        _, sim = t2s_api.request("GET", "/api/mode", timeout=2)
    except ServiceUnavailable:
        sim = {"mode": "sem resposta"}
    try:
        _, st = settlement_api.request("GET", "/health", timeout=2)
    except ServiceUnavailable:
        st = {"status": "sem resposta"}
    return jsonify(bus=bus.name, bus_ok=bus.ping(), outbox=outbox, settlement=st, t2s=sim, generation=generation())


@app.get("/api/reconciliation")
def reconciliation():
    """Reconciliação ENTRE SISTEMAS: negócios do Trading vs. instruções do Settlement."""
    with lock:
        trades_ = {t.trade_id: t for t in engine.trades}
    try:
        status, rows = settlement_api.request("GET", "/api/settlement/instructions")
    except ServiceUnavailable as exc:
        return jsonify(error=str(exc)), 503
    instructions = {r["trade_id"]: r for r in rows}
    missing = sorted(set(trades_) - set(instructions))
    orphan = sorted(set(instructions) - set(trades_))
    mismatched = []
    for tid in sorted(set(trades_) & set(instructions)):
        t, i = trades_[tid], instructions[tid]
        expected = round(t.qty * t.price, 2)
        if (t.qty, t.symbol, expected) != (int(i["qty"]), i["symbol"], round(float(i["amount"]), 2)):
            mismatched.append({"trade_id": tid, "trading": {"qty": t.qty, "symbol": t.symbol, "amount": expected},
                               "settlement": {"qty": i["qty"], "symbol": i["symbol"], "amount": i["amount"]}})
    ok = not (missing or orphan or mismatched)
    return jsonify(ok=ok, trades=len(trades_), instructions=len(instructions),
                   missing_in_settlement=missing, orphan_in_settlement=orphan, mismatched=mismatched)


@app.post("/api/integration/replay/<trade_id>")
def replay_event(trade_id):
    """Volta a publicar o evento de um negócio (simula a entrega duplicada do Kafka). Só fora de UAT."""
    _test_only()
    with lock:
        ev = database.outbox_event_for_trade(trade_id)
        database.rollback()
    if not ev:
        return jsonify(error=f"Sem evento para o negócio {trade_id}"), 404
    bus.publish(busmod.TOPIC_TRADES, trade_id, json.loads(ev["payload"]))
    log.warning("Evento do negócio %s publicado OUTRA VEZ (teste de idempotência)", trade_id)
    return jsonify(replayed=trade_id, event_id=ev["event_id"])


@app.post("/api/integration/publish-raw")
def publish_raw():
    """Publica uma mensagem arbitrária no tópico (teste de contrato e da fila de erros). Só fora de UAT."""
    _test_only()
    payload = _json()
    bus.publish(busmod.TOPIC_TRADES, str(payload.get("event_id", "teste")), payload)
    log.warning("Mensagem de teste publicada em %s (válida pelo contrato: %s)", busmod.TOPIC_TRADES,
                not validate_trade_executed(payload))
    return jsonify(published=True, contract_errors=validate_trade_executed(payload))


@app.post("/api/t2s/mode")
def t2s_mode():
    _test_only()
    try:
        status, body = t2s_api.request("POST", "/api/mode", _json())
    except ServiceUnavailable as exc:
        return jsonify(error=str(exc)), 503
    return jsonify(body), status


# ---------------------------------------------------------------------- administração
@app.post("/api/reset")
def reset():
    """Reinicia o ambiente inteiro: Trading, Settlement e simulador T2S (nova geração de eventos)."""
    with lock:
        database.reset()
        database.execute("DELETE FROM outbox_events")
        gen = generation() + 1
        database.set_state("generation", str(gen))
        database.commit()
        _build_components(restore=False)
    errors = []
    for name, client, body in (("Settlement", settlement_api, {"generation": gen}), ("T2S", t2s_api, {})):
        try:
            client.request("POST", "/api/reset", body)
        except ServiceUnavailable as exc:
            errors.append(str(exc))
    log.info("Ambiente %s reiniciado (geração %d)%s", ENV_NAME, gen, f"; avisos: {errors}" if errors else "")
    return jsonify(status="reset", generation=gen, warnings=errors)


@app.post("/api/query")
def query():
    data = _json()
    if data.get("db") == "settlement":
        return _forward("POST", "/api/query", {"sql": data.get("sql", "")})
    try:
        with lock:
            cols, rows = database.run_query(str(data.get("sql", "")))
    except Exception as exc:  # noqa: BLE001 - devolver o erro SQL ao utilizador
        return jsonify(error=str(exc)), 400
    return jsonify(columns=cols, rows=rows)


def main():
    port = int(os.environ.get("PORT", "8000"))
    log.info("Trading %s versão %s a arrancar na porta %d (base de dados: %s, barramento: %s, modo desafio: %s)",
             ENV_NAME, APP_VERSION, port, database.engine_name, bus.name, challenge_mode())
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
