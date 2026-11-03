"""
Simulador do T2S (TARGET2-Securities), o sistema externo onde a liquidação acontece de facto.

Serve para testar o Settlement isolado (standalone), sem depender do sistema real, e para provocar falhas:
    normal              confirma todas as instruções (SETTLED)
    rejeitar_simbolo    rejeita as instruções de um símbolo (ex.: falta de títulos)
    rejeitar_tudo       rejeita todas
    lento               demora N segundos a responder (testar timeouts)
    indisponivel        responde HTTP 503 (sistema em baixo)

Interface por ficheiro: lê <files>/outbound/SI_*.csv e escreve <files>/inbound/CONF_*.csv
(instruction_id, status, reason).
"""

import csv
import os
import time

from flask import Flask, abort, jsonify, request

from app.logs import get_logger

FILES_DIR = os.environ.get("QA_LAB_FILES_DIR", "/var/lib/qa-lab/files")
MODES = ("normal", "rejeitar_simbolo", "rejeitar_tudo", "lento", "indisponivel")

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
        abort(400, description=f"Modo inválido. Modos: {', '.join(MODES)}")
    if new == "rejeitar_simbolo" and not data.get("symbol"):
        abort(400, description="Indica o símbolo a rejeitar, ex.: {\"mode\":\"rejeitar_simbolo\",\"symbol\":\"EDP\"}")
    mode.update(mode=new, symbol=(data.get("symbol") or None), delay=float(data.get("delay", 0) or 0))
    log.warning("Modo do simulador alterado para %s%s", new, f" ({mode['symbol']})" if mode["symbol"] else "")
    return jsonify(mode)


@app.post("/api/reset")
def reset():
    mode.update(mode="normal", symbol=None, delay=0)
    return jsonify(mode)


@app.post("/api/process")
def process():
    if mode["mode"] == "indisponivel":
        log.error("Pedido de processamento recusado: simulador em modo indisponível")
        return jsonify(error="T2S indisponível"), 503
    if mode["mode"] == "lento":
        time.sleep(mode["delay"] or 20)
    name = os.path.basename(str((request.get_json(silent=True) or {}).get("file", "")))
    src = os.path.join(FILES_DIR, "outbound", name)
    if not name.startswith("SI_") or not os.path.isfile(src):
        abort(400, description=f"Ficheiro de instruções não encontrado: {name}")
    with open(src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out_name = "CONF_" + name[3:]
    os.makedirs(os.path.join(FILES_DIR, "inbound"), exist_ok=True)
    settled = rejected = 0
    with open(os.path.join(FILES_DIR, "inbound", out_name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["instruction_id", "status", "reason"])
        for r in rows:
            if mode["mode"] == "rejeitar_tudo" or (mode["mode"] == "rejeitar_simbolo" and r["symbol"] == mode["symbol"]):
                w.writerow([r["instruction_id"], "REJECTED", "Títulos insuficientes na conta do vendedor (simulado)"])
                rejected += 1
            else:
                w.writerow([r["instruction_id"], "SETTLED", ""])
                settled += 1
    mode["processed_files"] += 1
    log.info("Ficheiro %s processado: %d liquidadas, %d rejeitadas → %s", name, settled, rejected, out_name)
    return jsonify(confirmation_file=out_name, settled=settled, rejected=rejected)


def main():
    port = int(os.environ.get("PORT", "8002"))
    log.info("Simulador T2S a arrancar na porta %d (ficheiros em %s)", port, FILES_DIR)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
