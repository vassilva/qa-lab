"""
Persistência: ordens, negócios, instruções de liquidação e estado do sistema.

- Com DATABASE_URL (ex.: postgresql://qa:qa@db:5432/qa_lab) usa PostgreSQL.
- Sem DATABASE_URL usa um ficheiro SQLite local (útil para testes unitários rápidos).

O SQL é escrito de forma compatível com os dois motores.
"""

import os
import sqlite3
import threading
from datetime import date
from decimal import Decimal

from app.model import Order, Trade

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_FILE = os.path.join(BASE_DIR, "db", "schema.sql")


class Database:
    def __init__(self, url=None, sqlite_path=None):
        self.url = url if url is not None else os.environ.get("DATABASE_URL", "")
        self.is_postgres = self.url.startswith(("postgres://", "postgresql://"))
        self._lock = threading.RLock()
        if self.is_postgres:
            self._connect_postgres()
        else:
            path = sqlite_path or os.environ.get("QA_LAB_SQLITE", os.path.join(BASE_DIR, "data", "qa_lab.db"))
            if path != ":memory:":
                os.makedirs(os.path.dirname(path), exist_ok=True)
            self.conn = sqlite3.connect(path, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()

    @property
    def engine_name(self):
        return "postgresql" if self.is_postgres else "sqlite"

    def _connect_postgres(self):
        import psycopg  # instalado no contentor via requirements.txt
        self.conn = psycopg.connect(self.url, autocommit=False)

    # ------------------------------------------------------------------ utilitários
    def execute(self, statement, params=None):
        with self._lock:
            if self.is_postgres and self.conn.closed:
                self._connect_postgres()      # ligação perdida (ex.: PostgreSQL reiniciado)
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
        with open(SCHEMA_FILE, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if not ln.strip().startswith("--")]
        with self._lock:
            for statement in [s.strip() for s in "\n".join(lines).split(";") if s.strip()]:
                self.execute(statement)
            self.commit()

    def reset(self):
        with self._lock:
            for table in ("settlement_instructions", "trades", "orders", "system_state"):
                self.execute(f"DELETE FROM {table}")
            self.commit()

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

    # ------------------------------------------------------------------ ordens e negócios
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

    # ------------------------------------------------------------------ liquidação
    def insert_instruction(self, i):
        self.execute(
            """INSERT INTO settlement_instructions
                 (instruction_id, trade_id, symbol, qty, amount, trade_date, intended_settlement_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (i["instruction_id"], i["trade_id"], i["symbol"], i["qty"], i["amount"], i["trade_date"],
             i["intended_settlement_date"], i["status"]),
        )

    def update_instruction(self, instruction_id, status, settled_on):
        self.execute(
            """UPDATE settlement_instructions
               SET status = ?, settled_on = ?, updated_at = CURRENT_TIMESTAMP
               WHERE instruction_id = ?""",
            (status, settled_on, instruction_id),
        )

    _SI_COLUMNS = ("instruction_id, trade_id, symbol, qty, amount, trade_date, intended_settlement_date, "
                   "status, settled_on")

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
                          "WHERE status <> 'SETTLED' AND intended_settlement_date <= ? "
                          "ORDER BY instruction_id", (business_date,))

    # ------------------------------------------------------------------ estado do sistema
    def get_state(self, key):
        rows = self._rows("SELECT state_value FROM system_state WHERE state_key = ?", (key,))
        return rows[0]["state_value"] if rows else None

    def set_state(self, key, value):
        self.execute(
            """INSERT INTO system_state (state_key, state_value) VALUES (?, ?)
               ON CONFLICT (state_key) DO UPDATE SET state_value = excluded.state_value""",
            (key, value),
        )

    # ------------------------------------------------------------------ consola SQL
    def run_query(self, sql):
        """Executa uma query só de leitura (SELECT/WITH) e devolve colunas e linhas."""
        statement = sql.strip().rstrip(";").strip()
        if not statement.lower().startswith(("select", "with")) or ";" in statement:
            raise ValueError("Só são permitidas queries SELECT (uma de cada vez).")
        with self._lock:
            try:
                cur = self.execute(statement)
                cols = [d[0] for d in cur.description]
                rows = [[_plain(v) for v in r] for r in cur.fetchmany(500)]
            finally:
                self.rollback()  # a consola nunca altera dados
        return cols, rows


def _plain(value):
    """Converte tipos do PostgreSQL (Decimal, datas) em valores simples para JSON."""
    if value is None or isinstance(value, (int, float, str)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
