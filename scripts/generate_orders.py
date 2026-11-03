#!/usr/bin/env python3
"""
Generates random (but reproducible) orders against an environment, for exploratory testing,
volume data or to prepare a demo.

Usage: python3 scripts/generate_orders.py [--n 200] [--seed 42] [--url http://localhost:8000] [--invalid 0.1]

Each order has a price close to the symbol's reference, inside the bands; a share of them can be
deliberately invalid (quantity or price) to exercise the Order Entry Gateway.
At the end it prints a summary: accepted, rejected by reason, trades created and average response time.
"""

import argparse
import random
import time
from collections import Counter

import requests


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=200, help="number of orders (default 200)")
    p.add_argument("--seed", type=int, default=42, help="seed, to repeat exactly the same sequence")
    p.add_argument("--url", default="http://localhost:8000", help="environment URL")
    p.add_argument("--invalid", type=float, default=0.1, help="share of invalid orders (0 to 1)")
    args = p.parse_args()

    rnd = random.Random(args.seed)
    api = requests.Session()
    health = api.get(f"{args.url}/health", timeout=5).json()
    if health.get("environment") == "UAT":
        raise SystemExit("Refused: do not generate test data in UAT.")
    refs = {s["symbol"]: s["reference_price"] for s in api.get(f"{args.url}/api/symbols", timeout=5).json()}

    status, reasons, trades, times = Counter(), Counter(), 0, []
    for _ in range(args.n):
        symbol = rnd.choice(sorted(refs))
        ref = refs[symbol]
        ticks = rnd.randint(-int(ref * 0.05 / 0.01), int(ref * 0.05 / 0.01))   # up to ±5% of the reference
        order = {"symbol": symbol, "side": rnd.choice(["BUY", "SELL"]), "qty": rnd.choice([10, 50, 100, 250, 500]),
                 "price": round(ref + ticks * 0.01, 2)}
        if rnd.random() < 0.05:
            order["price"] = None                                    # market order
        if rnd.random() < args.invalid:
            order[rnd.choice(["qty", "price"])] = rnd.choice([0, 10_001]) if rnd.random() < 0.5 else round(ref * 1.2, 2)
        start = time.perf_counter()
        r = api.post(f"{args.url}/api/orders", json=order, timeout=10)
        times.append((time.perf_counter() - start) * 1000)
        body = r.json()
        status[body["order"]["status"]] += 1
        if body["order"]["reject_reason"]:
            reasons[body["order"]["reject_reason"]] += 1
        trades += len(body.get("trades", []))

    print(f"{args.n} orders sent to {args.url} ({health.get('environment')}, version {health.get('version')})")
    print("Statuses:   " + " · ".join(f"{k} {v}" for k, v in status.most_common()))
    print("Rejections: " + (" · ".join(f"{k} {v}" for k, v in reasons.most_common()) or "none"))
    print(f"Trades created: {trades}")
    times.sort()
    print(f"Response time: average {sum(times) / len(times):.1f} ms · p95 {times[int(len(times) * 0.95) - 1]:.1f} ms")


if __name__ == "__main__":
    main()
