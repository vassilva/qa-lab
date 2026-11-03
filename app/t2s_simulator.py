"""
Simulator of T2S (TARGET2-Securities), the external system where settlement actually happens.

Used to test Settlement in isolation (standalone), without depending on the real system, and to inject failures:
    normal              confirms every instruction (SETTLED)
    reject_symbol       rejects the instructions of one symbol (e.g. insufficient securities)
    reject_all          rejects every instruction
    slow                takes N seconds to respond (timeout testing)
    unavailable         responds HTTP 503 (system down)

File interface: reads <files>/outbound/SI_*.csv and writes <files>/inbound/CONF_*.csv
(instruction_id, status, reason).
"""

import csv
import os
import time

from flask import Flask, abort, jsonify, request

from app.logs import get_logger

FILES_DIR = os.environ.get("QA_LAB_FILES_DIR", "/var/lib/qa-lab/files")
MODES = ("normal", "reject_symbol", "reject_all", "slow", "unavailable")

log = get_logger("T2S-SIM")
app = Flask(__name__)
mode = {"mode": "normal", "symbol": None, "delay": 0, "processed_files": 0}


@app.errorhandler(400)
def bad_request(err):
    return jsonify(error=err.description), 400


@app.get("/health")
def health():
    return jsonify(status="UP", service="t2s-simulator", environment=os.environ.get("ENV_NAME", "local").upper(), **mode)


@app.get("/api/mode")
def get_mode():
    return jsonify(mode)


@app.post("/api/mode")
def set_mode():
    data = request.get_json(silent=True) or {}
    new = data.get("mode", "normal")
    if new not in MODES:
        abort(400, description=f"Invalid mode. Modes: {', '.join(MODES)}")
    if new == "reject_symbol" and not data.get("symbol"):
        abort(400, description="Give the symbol to reject, e.g. {\"mode\":\"reject_symbol\",\"symbol\":\"EDP\"}")
    mode.update(mode=new, symbol=(data.get("symbol") or None), delay=float(data.get("delay", 0) or 0))
    log.warning("Simulator mode changed to %s%s", new, f" ({mode['symbol']})" if mode["symbol"] else "")
    return jsonify(mode)


@app.post("/api/reset")
def reset():
    mode.update(mode="normal", symbol=None, delay=0)
    return jsonify(mode)


@app.post("/api/process")
def process():
    if mode["mode"] == "unavailable":
        log.error("Processing request refused: simulator in unavailable mode")
        return jsonify(error="T2S unavailable"), 503
    if mode["mode"] == "slow":
        time.sleep(mode["delay"] or 20)
    name = os.path.basename(str((request.get_json(silent=True) or {}).get("file", "")))
    src = os.path.join(FILES_DIR, "outbound", name)
    if not name.startswith("SI_") or not os.path.isfile(src):
        abort(400, description=f"Instruction file not found: {name}")
    with open(src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out_name = "CONF_" + name[3:]
    os.makedirs(os.path.join(FILES_DIR, "inbound"), exist_ok=True)
    settled = rejected = 0
    with open(os.path.join(FILES_DIR, "inbound", out_name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["instruction_id", "status", "reason"])
        for r in rows:
            if mode["mode"] == "reject_all" or (mode["mode"] == "reject_symbol" and r["symbol"] == mode["symbol"]):
                w.writerow([r["instruction_id"], "REJECTED", "Insufficient securities in the seller's account (simulated)"])
                rejected += 1
            else:
                w.writerow([r["instruction_id"], "SETTLED", ""])
                settled += 1
    mode["processed_files"] += 1
    log.info("File %s processed: %d settled, %d rejected → %s", name, settled, rejected, out_name)
    return jsonify(confirmation_file=out_name, settled=settled, rejected=rejected)


def main():
    port = int(os.environ.get("PORT", "8002"))
    log.info("T2S simulator starting on port %d (files in %s)", port, FILES_DIR)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
