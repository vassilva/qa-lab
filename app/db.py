"""
Persistence: orders, trades, settlement instructions, outbox and system state.

- With DATABASE_URL (e.g. postgresql://qa:qa@db:5432/qa_lab) it uses PostgreSQL.
- Without DATABASE_URL it uses a local SQLite file (useful for fast unit tests).

The SQL is written to be compatible with both engines.
"""

import os
import sqlite3
import threading
from datetime import date
from decimal import Decimal

from app.model import Order, Trade

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_FILE = os.path.join(BASE_DIR, "db", "schema.sql")
SETTLEMENT_SCHEMA_FILE = os.path.join(BASE_DIR, "db", "schema_settlement.sql")


class Database:
    def __init__(self, url=None, sqlite_path=None, schema_file=SCHEMA_FILE, sqlite_env="QA_LAB_SQLITE",
                 default_sqlite="qa_lab.db"):
        self.url = url if url is not None else os.environ.get("DATABASE_URL", "")
        self.schema_file = schema_file
        self.is_postgres = self.url.startswith(("postgres://", "postgresql://"))
        self._lock = threading.RLock()
        if self.is_postgres:
            self._connect_postgres()
        else:
            path = sqlite_path or os.environ.get(sqlite_env, os.path.join(BASE_DIR, "data", default_sqlite))
            if path != ":memory:":
                os.makedirs(os.path.dirname(path), exist_ok=True)
            self.conn = sqlite3.connect(path, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()

    @property
    def engine_name(self):
        return "postgresql" if self.is_postgres else "sqlite"

    def _connect_postgres(self):
        import psycopg  # installed in the container from requirements.txt
        try:
            self.conn = psycopg.connect(self.url, autocommit=False)
        except psycopg.OperationalError as exc:
            if "does not exist" not in str(exc):
                raise
            # Each system has its own database: create it on first use (e.g. "settlement")
            base, _, dbname = self.url.rpartition("/")
            dbname = dbname.split("?")[0]
            with psycopg.connect(base + "/postgres", autocommit=True) as admin:
                admin.execute(f'CREATE DATABASE "{dbname}"')
            self.conn = psycopg.connect(self.url, autocommit=False)

    # ------------------------------------------------------------------ utilities
    def execute(self, statement, params=None):
        with self._lock:
            if self.is_postgres and self.conn.closed:
                self._connect_postgres()      # connection lost (e.g. PostgreSQL restarted)
            cur = self.conn.cursor()
            if params:
                if self.is_postgres:
                    cur.execute(statement.replace("?", "%s"), params)
                else:
                    cur.execute(statement, [p.isoformat() if isinstance(p, date) else p for p in params])
            else:
                cur.execute(statement)
            return cur

    def _rows(self, statement, params=None):
        with self._lock:
            cur = self.execute(statement, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, [_plain(v) for v in row])) for row in cur.fetchall()]

    def commit(self):
        with self._lock:
            self.conn.commit()

    def rollback(self):
        with self._lock:
            self.conn.rollback()

    def create_schema(self):
        with open(self.schema_file, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if not ln.strip().startswith("--")]
        with self._lock:
            for statement in [s.strip() for s in "\n".join(lines).split(";") if s.strip()]:
                self.execute(statement)
            self.commit()

    def reset(self):
        with self._lock:
            for table in self.tables():
                if table != "system_state":
                    self.execute(f"DELETE FROM {table}")
            self.commit()

    def tables(self):
        with open(self.schema_file, encoding="utf-8") as f:
            import re
            return re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", f.read())[::-1]   # children before parents

    def ping(self):
        try:
            with self._lock:
                self.execute("SELECT 1").fetchone()
                self.rollback()
            return True
        except Exception:  # noqa: BLE001
            try:
                self.rollback()
            except Exception:  # noqa: BLE001
                pass
            return False

    # ------------------------------------------------------------------ orders and trades
    def save_order(self, o):
        self.execute(
            """INSERT INTO orders (order_id, symbol, side, qty, price, remaining, status, reject_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (order_id) DO UPDATE SET
                 remaining = excluded.remaining,
                 status = excluded.status,
                 updated_at = CURRENT_TIMESTAMP""",
            (o.order_id, o.symbol, o.side, o.qty, o.price, o.remaining, o.status, o.reject_reason),
        )

    def save_trade(self, t):
        self.execute(
            """INSERT INTO trades (trade_id, symbol, buy_order_id, sell_order_id, qty, price, trade_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (trade_id) DO NOTHING""",
            (t.trade_id, t.symbol, t.buy_order_id, t.sell_order_id, t.qty, t.price, date.fromisoformat(t.trade_date)),
        )

    def load_orders(self):
        orders = []
        for r in self._rows("SELECT order_id, symbol, side, qty, price, remaining, status, reject_reason "
                            "FROM orders ORDER BY order_id"):
            o = Order(r["order_id"], r["symbol"], r["side"], int(r["qty"]),
                      None if r["price"] is None else float(r["price"]))
            o.remaining, o.status, o.reject_reason = int(r["remaining"]), r["status"], r["reject_reason"]
            orders.append(o)
        return orders

    def load_trades(self):
        return [Trade(r["trade_id"], r["symbol"], r["buy_order_id"], r["sell_order_id"], int(r["qty"]),
                      float(r["price"]), str(r["trade_date"]))
                for r in self._rows("SELECT trade_id, symbol, buy_order_id, sell_order_id, qty, price, trade_date "
                                    "FROM trades ORDER BY trade_id")]

    # ------------------------------------------------------------------ settlement
    def insert_instruction(self, i):
        self.execute(
            """INSERT INTO settlement_instructions
                 (instruction_id, trade_id, event_id, symbol, qty, amount, buy_order_id, sell_order_id,
                  trade_date, intended_settlement_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (i["instruction_id"], i["trade_id"], i["event_id"], i["symbol"], i["qty"], i["amount"], i["buy_order_id"],
             i["sell_order_id"], i["trade_date"], i["intended_settlement_date"], i["status"]),
        )

    def update_instruction(self, instruction_id, status, settled_on, fail_reason=None, attempt=False):
        self.execute(
            f"""UPDATE settlement_instructions
               SET status = ?, settled_on = ?, fail_reason = ?, updated_at = CURRENT_TIMESTAMP
                   {", attempts = attempts + 1" if attempt else ""}
               WHERE instruction_id = ?""",
            (status, settled_on, fail_reason, instruction_id),
        )

    def instruction_for_trade(self, trade_id):
        rows = self._rows(f"SELECT {self._SI_COLUMNS} FROM settlement_instructions WHERE trade_id = ?", (trade_id,))
        return rows[0] if rows else None

    def insert_rejected_event(self, reason, payload):
        row = self._rows("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM rejected_events")[0]
        self.execute("INSERT INTO rejected_events (id, reason, payload) VALUES (?, ?, ?)", (row["n"], reason[:500], payload))

    def list_rejected_events(self):
        return self._rows("SELECT id, received_at, reason, payload FROM rejected_events ORDER BY id DESC")

    # ------------------------------------------------------------------ outbox (Trading)
    def insert_outbox(self, event_id, topic, key, payload):
        self.execute("INSERT INTO outbox_events (event_id, topic, event_key, payload) VALUES (?, ?, ?, ?)",
                     (event_id, topic, key, payload))

    def pending_outbox(self, limit=100):
        return self._rows("SELECT event_id, topic, event_key, payload, attempts FROM outbox_events "
                          "WHERE published_at IS NULL ORDER BY created_at, event_id LIMIT ?", (limit,))

    def mark_published(self, event_id):
        self.execute("UPDATE outbox_events SET published_at = CURRENT_TIMESTAMP, attempts = attempts + 1, "
                     "last_error = NULL WHERE event_id = ?", (event_id,))

    def mark_failed(self, event_id, error):
        self.execute("UPDATE outbox_events SET attempts = attempts + 1, last_error = ? WHERE event_id = ?",
                     (error[:300], event_id))

    def outbox_event_for_trade(self, trade_id):
        rows = self._rows("SELECT event_id, payload FROM outbox_events WHERE event_key = ?", (trade_id,))
        return rows[0] if rows else None

    def outbox_stats(self):
        r = self._rows("SELECT COUNT(*) AS total, "
                       "SUM(CASE WHEN published_at IS NULL THEN 1 ELSE 0 END) AS pendentes, "
                       "MAX(published_at) AS ultima_publicacao FROM outbox_events")[0]
        return {"total": int(r["total"] or 0), "pending": int(r["pendentes"] or 0), "last_published_at": r["ultima_publicacao"]}

    _SI_COLUMNS = ("instruction_id, trade_id, event_id, symbol, qty, amount, buy_order_id, sell_order_id, trade_date, "
                   "intended_settlement_date, status, fail_reason, attempts, settled_on")

    def get_instruction(self, instruction_id):
        rows = self._rows(f"SELECT {self._SI_COLUMNS} FROM settlement_instructions WHERE instruction_id = ?",
                          (instruction_id,))
        return rows[0] if rows else None

    def list_instructions(self, status=None):
        if status:
            return self._rows(f"SELECT {self._SI_COLUMNS} FROM settlement_instructions WHERE status = ? "
                              "ORDER BY instruction_id DESC", (status,))
        return self._rows(f"SELECT {self._SI_COLUMNS} FROM settlement_instructions ORDER BY instruction_id DESC")

    def due_instructions(self, business_date):
        return self._rows(f"SELECT {self._SI_COLUMNS} FROM settlement_instructions "
                          "WHERE status IN ('PENDING', 'FAILED', 'ON_HOLD') AND intended_settlement_date <= ? "
                          "ORDER BY instruction_id", (business_date,))

    # ------------------------------------------------------------------ system state
    def get_state(self, key):
        rows = self._rows("SELECT state_value FROM system_state WHERE state_key = ?", (key,))
        return rows[0]["state_value"] if rows else None

    def set_state(self, key, value):
        self.execute(
            """INSERT INTO system_state (state_key, state_value) VALUES (?, ?)
               ON CONFLICT (state_key) DO UPDATE SET state_value = excluded.state_value""",
            (key, value),
        )

    # ------------------------------------------------------------------ SQL console
    def run_query(self, sql):
        """Runs a read-only query (SELECT/WITH) and returns columns and rows."""
        statement = sql.strip().rstrip(";").strip()
        if not statement.lower().startswith(("select", "with")) or ";" in statement:
            raise ValueError("Only SELECT queries are allowed (one at a time).")
        with self._lock:
            try:
                cur = self.execute(statement)
                cols = [d[0] for d in cur.description]
                rows = [[_plain(v) for v in r] for r in cur.fetchmany(500)]
            finally:
                self.rollback()  # the console never changes data
        return cols, rows


def _plain(value):
    """Converts PostgreSQL types (Decimal, dates) into plain JSON values."""
    if value is None or isinstance(value, (int, float, str)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
