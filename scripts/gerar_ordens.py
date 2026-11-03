#!/usr/bin/env python3
"""
Gera ordens aleatórias (mas reproduzíveis) contra um ambiente, para testes exploratórios,
dados de volume ou para preparar uma demonstração.

Uso: python3 scripts/gerar_ordens.py [--n 200] [--seed 42] [--url http://localhost:8000] [--invalidas 0.1]

Cada ordem tem um preço perto da referência do símbolo, dentro das bandas; uma percentagem pode ser
propositadamente inválida (quantidade ou preço) para exercitar o Order Entry Gateway.
No fim mostra o resumo: aceites, rejeitadas por motivo, negócios criados e tempo médio de resposta.
"""

import argparse
import random
import time
from collections import Counter

import requests


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=200, help="número de ordens (por omissão 200)")
    p.add_argument("--seed", type=int, default=42, help="semente, para repetir exatamente a mesma sequência")
    p.add_argument("--url", default="http://localhost:8000", help="endereço do ambiente")
    p.add_argument("--invalidas", type=float, default=0.1, help="fração de ordens inválidas (0 a 1)")
    args = p.parse_args()

    rnd = random.Random(args.seed)
    api = requests.Session()
    health = api.get(f"{args.url}/health", timeout=5).json()
    if health.get("environment") == "UAT":
        raise SystemExit("Recusado: não gerar dados de teste em UAT.")
    refs = {s["symbol"]: s["reference_price"] for s in api.get(f"{args.url}/api/symbols", timeout=5).json()}

    status, reasons, trades, times = Counter(), Counter(), 0, []
    for _ in range(args.n):
        symbol = rnd.choice(sorted(refs))
        ref = refs[symbol]
        ticks = rnd.randint(-int(ref * 0.05 / 0.01), int(ref * 0.05 / 0.01))   # até ±5% da referência
        order = {"symbol": symbol, "side": rnd.choice(["BUY", "SELL"]), "qty": rnd.choice([10, 50, 100, 250, 500]),
                 "price": round(ref + ticks * 0.01, 2)}
        if rnd.random() < 0.05:
            order["price"] = None                                    # ordem de mercado
        if rnd.random() < args.invalidas:
            order[rnd.choice(["qty", "price"])] = rnd.choice([0, 10_001]) if rnd.random() < 0.5 else round(ref * 1.2, 2)
        start = time.perf_counter()
        r = api.post(f"{args.url}/api/orders", json=order, timeout=10)
        times.append((time.perf_counter() - start) * 1000)
        body = r.json()
        status[body["order"]["status"]] += 1
        if body["order"]["reject_reason"]:
            reasons[body["order"]["reject_reason"]] += 1
        trades += len(body.get("trades", []))

    print(f"{args.n} ordens enviadas para {args.url} ({health.get('environment')}, versão {health.get('version')})")
    print("Estados:  " + " · ".join(f"{k} {v}" for k, v in status.most_common()))
    print("Rejeições: " + (" · ".join(f"{k} {v}" for k, v in reasons.most_common()) or "nenhuma"))
    print(f"Negócios criados: {trades}")
    times.sort()
    print(f"Tempo de resposta: média {sum(times) / len(times):.1f} ms · p95 {times[int(len(times) * 0.95) - 1]:.1f} ms")


if __name__ == "__main__":
    main()
