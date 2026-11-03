"""
QA Lab logs.

Each service writes to its own file, and each component uses its own tag:
    2026-11-03 10:15:02,118 INFO [OEG] Order O00001 accepted: SELL 100 EDP @ 4.50

Tags: OEG (Order Entry Gateway), ME (Matching Engine), SETTLEMENT, CONSUMER, T2S, API.
Folder: QA_LAB_LOG_DIR (in the container: /var/log/qa-lab); file: QA_LAB_LOG_FILE
"""

import logging
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.environ.get("QA_LAB_LOG_DIR", os.path.join(BASE_DIR, "logs"))
LOG_FILE = os.path.join(LOG_DIR, os.environ.get("QA_LAB_LOG_FILE", "qa-lab.log"))   # trading: qa-lab.log · settlement.log · t2s-sim.log

_handler = None


def get_logger(component: str) -> logging.Logger:
    global _handler
    if _handler is None:
        os.makedirs(LOG_DIR, exist_ok=True)
        _handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    log = logging.getLogger(component)
    if _handler not in log.handlers:
        log.addHandler(_handler)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log
