"""
SETTLEMENT service (a system separate from Trading), inspired by Euronext Securities settlement.

- Consumes the Kafka topic "trades.executed" (contract contracts/trade-executed.v1.schema.json)
- Validates each message; invalid ones go to the "trades.executed.dlq" topic and the rejected_events table
- Is idempotent: the same trade received twice creates a single instruction
- Settles at end of day through T2S (simulator), by exchanging files
- Has its own database (DATABASE_URL, e.g. .../settlement)

API: /health, /api/business-date, /api/settlement/instructions, /api/eod, /api/rejected-events, /api/query ...
"""

import json
import os
import threading
from datetime import date

from flask import Flask, abort, jsonify, request

from app import bus as busmod
from app.contracts import validate_trade_executed
from app.db import SETTLEMENT_SCHEMA_FILE, Database
from app.logs import get_logger
from app.service_client import ServiceClient
from app.settlement import SettlementService, is_business_day

ENV_NAME = os.environ.get("ENV_NAME", "local").upper()
APP_VERSION = os.environ.get("APP_VERSION", "local")
CONSUMER_GROUP = "settlement-service"

log = get_logger("SETTLEMENT")
app = Flask(__name__)
lock = threading.RLock()

database = Database(schema_file=SETTLEMENT_SCHEMA_FILE, sqlite_env="SETTLEMENT_SQLITE", default_sqlite="settlement.db")
t2s_client = ServiceClient(os.environ.get("T2S_URL", "http://localhost:8002"), "T2S")
settlement = SettlementService(database, t2s_client)
bus = busmod.get_bus()
state = {"generation": 0, "paused": False, "processed": 0, "duplicates": 0, "rejected": 0, "stale": 0}


# ---------------------------------------------------------------------- event consumer
def handle_trade_event(event):
    """Processes an event from the trades.executed topic. Raises RetryableError on temporary failures."""
    if state["paused"]:
        raise busmod.RetryableError("consumer paused")
    errors = ["message is not JSON"] if "_raw" in event else validate_trade_executed(event)
    with lock:
        try:
            if errors:
                reason = "; ".join(errors)
                log.warning("Event REJECTED (trade-executed v1 contract): %s", reason)
                database.insert_rejected_event(reason, json.dumps(event)[:4000])
                database.commit()
                bus.publish(busmod.TOPIC_TRADES_DLQ, str(event.get("event_id", "invalid")),
                            {"reason": reason, "original": event})
                state["rejected"] += 1
                return
            if event["generation"] < state["generation"]:
                log.info("Event %s from a previous environment generation ignored (test reset)", event["event_id"])
                state["stale"] += 1
                return
            before = database.instruction_for_trade(event["trade"]["trade_id"])
            settlement.create_instruction(event)
            state["duplicates" if before else "processed"] += 1
        except busmod.RetryableError:
            raise
        except Exception as exc:  # noqa: BLE001 - database down, etc.: retry
            database.rollback()
            raise busmod.RetryableError(str(exc)) from exc


bus.start_consumer(busmod.TOPIC_TRADES, CONSUMER_GROUP, handle_trade_event)


# ---------------------------------------------------------------------- API
def _json():
    return request.get_json(silent=True) or {}


@app.errorhandler(400)
def bad_request(err):
    return jsonify(error=err.description), 400


@app.get("/health")
def health():
    with lock:
        db_ok = database.ping()
    bus_ok = bus.ping()
    ok = db_ok and bus_ok
    return jsonify(status="UP" if ok else "DEGRADED", service="settlement", environment=ENV_NAME, version=APP_VERSION,
                   database=database.engine_name, database_ok=db_ok, bus=bus.name, bus_ok=bus_ok,
                   consumer_ready=bus.ready(busmod.TOPIC_TRADES),     # readiness (DEF-015): partition assigned
                   consumer={k: v for k, v in state.items()}), 200 if ok else 503


@app.get("/api/business-date")
def get_business_date():
    with lock:
        return jsonify(business_date=settlement.business_date().isoformat())


@app.post("/api/business-date")
def set_business_date():
    try:
        new_date = date.fromisoformat(str(_json().get("date", "")))
    except ValueError:
        abort(400, description="Invalid date: use the format YYYY-MM-DD")
    if not is_business_day(new_date):
        abort(400, description=f"{new_date.isoformat()} is not a business day (weekend or TARGET2 holiday)")
    with lock:
        settlement.set_business_date(new_date)
    return jsonify(business_date=new_date.isoformat())


@app.get("/api/settlement/instructions")
def instructions():
    with lock:
        rows = database.list_instructions((request.args.get("status") or "").upper() or None)
        database.rollback()
    trade_id = request.args.get("trade_id")
    return jsonify([r for r in rows if not trade_id or r["trade_id"] == trade_id])


@app.post("/api/settlement/instructions/<instruction_id>/<action>")
def instruction_action(instruction_id, action):
    if action not in ("hold", "release"):
        abort(400, description="Invalid action: use hold or release")
    with lock:
        ok = settlement.hold(instruction_id) if action == "hold" else settlement.release(instruction_id)
        instruction = database.get_instruction(instruction_id)
        database.rollback()
    if not ok:
        return jsonify(error=f"Could not apply {action} to {instruction_id}", instruction=instruction), 409
    return jsonify(instruction)


@app.post("/api/eod")
def eod():
    with lock:
        return jsonify(settlement.run_eod())


@app.get("/api/rejected-events")
def rejected_events():
    with lock:
        rows = database.list_rejected_events()
        database.rollback()
    return jsonify(rows)


@app.post("/api/consumer/<action>")
def consumer_control(action):
    """Pause/resume the consumer: simulates Settlement being unavailable (not available in UAT)."""
    if ENV_NAME == "UAT":
        abort(403, description="Not available in UAT")
    if action not in ("pause", "resume"):
        abort(400, description="Invalid action: use pause or resume")
    state["paused"] = action == "pause"
    log.warning("Event consumer %s", "PAUSED" if state["paused"] else "resumed")
    return jsonify(paused=state["paused"])


@app.post("/api/reset")
def reset():
    """Clears Settlement data and adopts the new environment generation (ignores old events still in transit)."""
    with lock:
        database.reset()
        database.execute("DELETE FROM system_state WHERE state_key = 'business_date'")
        database.commit()
        state.update(generation=int(_json().get("generation", state["generation"])), paused=False,
                     processed=0, duplicates=0, rejected=0, stale=0)
    log.info("Settlement reset (generation %d)", state["generation"])
    return jsonify(status="reset", generation=state["generation"])


@app.post("/api/query")
def query():
    try:
        with lock:
            cols, rows = database.run_query(str(_json().get("sql", "")))
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=str(exc)), 400
    return jsonify(columns=cols, rows=rows)


def main():
    port = int(os.environ.get("PORT", "8001"))
    log.info("Settlement %s version %s starting on port %d (bus: %s, database: %s)",
             ENV_NAME, APP_VERSION, port, bus.name, database.engine_name)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
