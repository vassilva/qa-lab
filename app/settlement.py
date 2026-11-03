"""
T+2 Settlement.

Inspired by Euronext's post-trade chain (Euronext Clearing → Euronext Securities → T2S):
each trade creates a settlement instruction for T+2 (two business days after
the trade date). The end-of-day (EOD) process settles the instructions that reached
their intended settlement date and writes a report file.

Instruction states:
    PENDING   waiting for the settlement date
    ON_HOLD   held by the participant; does not settle until released
    FAILED    rejected by T2S (or no response); recycled at the next end of day
    SETTLED   settled (securities and cash exchanged), confirmed by T2S

Business days: Monday to Friday, except TARGET2 closing days:
1 January, Good Friday, Easter Monday, 1 May, 25 and 26 December.
"""

import csv
import os
from datetime import date, datetime, timedelta

from app.logs import LOG_DIR, get_logger
from app.model import challenge_mode

SETTLEMENT_CYCLE = 2          # T+2
EOD_DIR = os.path.join(LOG_DIR, "eod")

log = get_logger("SETTLEMENT")


# ---------------------------------------------------------------------- calendar
def easter_sunday(year: int) -> date:
    """Easter Sunday (Meeus/Jones/Butcher algorithm, Gregorian calendar)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def target2_holidays(year: int) -> set:
    easter = easter_sunday(year)
    return {
        date(year, 1, 1),
        easter - timedelta(days=2),   # Good Friday
        easter + timedelta(days=1),   # Easter Monday
        date(year, 5, 1),
        date(year, 12, 25),
        date(year, 12, 26),
    }


def is_business_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    if challenge_mode():
        return True               # hidden defect: ignores TARGET2 holidays
    return d not in target2_holidays(d.year)


def add_business_days(start: date, days: int) -> date:
    d = start
    while days > 0:
        d += timedelta(days=1)
        if is_business_day(d):
            days -= 1
    return d


def next_business_day(d: date) -> date:
    return add_business_days(d, 1)


def to_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


# ---------------------------------------------------------------------- service
class SettlementService:
    """Settlement logic. Communication with T2S (simulator) uses files plus a processing call."""

    def __init__(self, database, t2s_client=None, files_dir=None):
        self.db = database
        self.t2s = t2s_client
        self.files_dir = files_dir or os.environ.get("QA_LAB_FILES_DIR", os.path.join(LOG_DIR, "files"))

    # system business date (stored in the database, survives restarts)
    def business_date(self) -> date:
        value = self.db.get_state("business_date")
        if value:
            return to_date(value)
        today = date.today()
        if not is_business_day(today):
            today = next_business_day(today)
        self.set_business_date(today)
        return today

    def set_business_date(self, d: date):
        self.db.set_state("business_date", d.isoformat())
        self.db.commit()
        log.info("Business date set to %s", d.isoformat())

    def create_instruction(self, event) -> dict:
        """Creates the instruction from the TradeExecuted event. Idempotent: a repeated trade is ignored."""
        trade = event["trade"]
        existing = self.db.instruction_for_trade(trade["trade_id"])
        if existing:
            log.warning("Duplicate event ignored: trade %s already has instruction %s (event_id %s)",
                        trade["trade_id"], existing["instruction_id"], event["event_id"])
            return existing
        trade_date = to_date(trade["trade_date"])
        isd = add_business_days(trade_date, SETTLEMENT_CYCLE)
        instruction = {
            "instruction_id": "S" + trade["trade_id"][1:],
            "trade_id": trade["trade_id"],
            "event_id": event["event_id"],
            "symbol": trade["symbol"],
            "qty": trade["qty"],
            "amount": round(trade["qty"] * trade["price"], 2),
            "buy_order_id": trade["buy_order_id"],
            "sell_order_id": trade["sell_order_id"],
            "trade_date": trade_date,
            "intended_settlement_date": isd,
            "status": "PENDING",
        }
        self.db.insert_instruction(instruction)
        self.db.commit()
        log.info("Instruction %s created for trade %s: %d %s, %.2f EUR, intended settlement %s",
                 instruction["instruction_id"], trade["trade_id"], trade["qty"], trade["symbol"],
                 instruction["amount"], isd.isoformat())
        return instruction

    def hold(self, instruction_id) -> bool:
        return self._transition(instruction_id, ("PENDING", "FAILED"), "ON_HOLD", "held")

    def release(self, instruction_id) -> bool:
        return self._transition(instruction_id, ("ON_HOLD",), "PENDING", "released")

    def _transition(self, instruction_id, current, new, label):
        instruction = self.db.get_instruction(instruction_id)
        if instruction is None or instruction["status"] not in current:
            log.warning("Instruction %s cannot be %s (current status: %s)", instruction_id, label,
                        instruction["status"] if instruction else "not found")
            self.db.rollback()
            return False
        self.db.update_instruction(instruction_id, new, None, instruction.get("fail_reason"))
        self.db.commit()
        log.info("Instruction %s %s", instruction_id, label)
        return True

    # ------------------------------------------------------------------ end of day
    def run_eod(self) -> dict:
        """
        End of day: sends T2S a file with the due instructions (PENDING, and FAILED ones, which are recycled),
        reads the confirmation file, updates the statuses, writes the report and moves the business date forward.
        """
        bd = self.business_date()
        log.info("Start of end of day (EOD) for %s", bd.isoformat())
        due = self.db.due_instructions(bd)
        to_send = [i for i in due if i["status"] in ("PENDING", "FAILED")]
        held = [i for i in due if i["status"] == "ON_HOLD"]
        for ins in held:
            log.warning("Instruction %s NOT settled on its intended date: status ON_HOLD", ins["instruction_id"])

        t2s_status, settled, failed = "no instructions", [], []
        if to_send:
            out_file = self._write_outbound(bd, to_send)
            try:
                confirmations = self._process_at_t2s(out_file, bd)
                t2s_status = "ok"
            except Exception as exc:  # noqa: BLE001 - T2S unavailable: instructions stay for the next day
                confirmations = {}
                t2s_status = f"unavailable ({exc})"
                log.error("T2S unavailable at EOD for %s: %d instructions not settled (%s)", bd.isoformat(), len(to_send), exc)
            for ins in to_send:
                conf = confirmations.get(ins["instruction_id"])
                if conf and conf["status"] == "SETTLED":
                    self.db.update_instruction(ins["instruction_id"], "SETTLED", bd, None, attempt=True)
                    ins.update(status="SETTLED", settled_on=bd.isoformat(), fail_reason=None)
                    settled.append(ins)
                    log.info("Instruction %s SETTLED (%s)", ins["instruction_id"], bd.isoformat())
                else:
                    reason = conf["reason"] if conf else "no confirmation from T2S"
                    self.db.update_instruction(ins["instruction_id"], "FAILED", None, reason, attempt=True)
                    ins.update(status="FAILED", fail_reason=reason)
                    failed.append(ins)
                    log.warning("Instruction %s FAILED at T2S: %s (will be recycled at the next EOD)",
                                ins["instruction_id"], reason)
        report = self._write_report(bd, settled + failed + held)
        next_bd = next_business_day(bd)
        self.db.set_state("business_date", next_bd.isoformat())
        self.db.commit()
        log.info("End of EOD for %s: %d settled, %d failed, %d held. T2S: %s. Next business date: %s",
                 bd.isoformat(), len(settled), len(failed), len(held), t2s_status, next_bd.isoformat())
        return {
            "business_date": bd.isoformat(),
            "settled": len(settled),
            "failed": len(failed),
            "not_settled": len(failed) + len(held),
            "t2s": t2s_status,
            "report_file": report,
            "next_business_date": next_bd.isoformat(),
        }

    def _write_outbound(self, bd, rows):
        folder = os.path.join(self.files_dir, "outbound")
        os.makedirs(folder, exist_ok=True)
        name = f"SI_{bd.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S%f')}.csv"
        with open(os.path.join(folder, name), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["instruction_id", "trade_id", "symbol", "qty", "amount", "intended_settlement_date"])
            for r in rows:
                w.writerow([r["instruction_id"], r["trade_id"], r["symbol"], r["qty"], r["amount"],
                            r["intended_settlement_date"]])
        log.info("Instruction file %s sent to T2S (%d instructions)", name, len(rows))
        return name

    def _process_at_t2s(self, out_file, bd):
        if self.t2s is None:
            raise RuntimeError("T2S client not configured")
        status, body = self.t2s.request("POST", "/api/process", {"file": out_file, "business_date": bd.isoformat()},
                                        timeout=15)
        if status != 200:
            raise RuntimeError(f"HTTP {status}: {body.get('error', body)}")
        path = os.path.join(self.files_dir, "inbound", body["confirmation_file"])
        with open(path, newline="", encoding="utf-8") as f:
            confirmations = {r["instruction_id"]: r for r in csv.DictReader(f)}
        log.info("Confirmation file %s received from T2S (%d rows)", body["confirmation_file"], len(confirmations))
        return confirmations

    def _write_report(self, bd: date, rows) -> str:
        os.makedirs(EOD_DIR, exist_ok=True)
        path = os.path.join(EOD_DIR, f"settlement_{bd.strftime('%Y%m%d')}.csv")
        fields = ["instruction_id", "trade_id", "symbol", "qty", "amount", "trade_date",
                  "intended_settlement_date", "status", "settled_on", "fail_reason"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow({k: (v.isoformat() if isinstance(v, date) else v) for k, v in r.items()})
        return path
