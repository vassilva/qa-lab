"""
Persistência das ordens e negócios.

- Por omissão usa PostgreSQL (variável DATABASE_URL, ex.: postgresql://qa:qa@postgres:5432/qa_lab).
- Sem DATABASE_URL usa um ficheiro SQLite local (útil para correr testes rapidamente).

O SQL é escrito de forma compatível com os dois motores.
"""

import os
import sqlite3
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_FILE = os.path.join(BASE_DIR, "db", "schema.sql")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQLITE_PATH = os.environ.get("QA_LAB_SQLITE", os.path.join(BASE_DIR, "data", "qa_lab.db"))


class Database:
    def __init__(self, url=None):
        self.url = url if url is not None else DATABASE_URL
        self.is_postgres = self.url.startswith(("postgres://", "postgresql://"))
        self._lock = threading.Lock()
        if self.is_postgres:
            import psycopg  # instalado via requirements.txt
            self.conn = psycopg.connect(self.url, autocommit=False)
        else:
            os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
            self.conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
        self.create_schema()

    # ------------------------------------------------------------------ utilitários
    def _sql(self, statement):
        # SQLite usa "?" como marcador; PostgreSQL (psycopg) usa "%s"
        return statement.replace("?", "%s") if self.is_postgres else statement

    def execute(self, statement, params=()):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(self._sql(statement), params)
            return cur

    def commit(self):
        with self._lock:
            self.conn.commit()

    def create_schema(self):
        with open(SCHEMA_FILE, encoding="utf-8") as f:
            script = f.read()
        with self._lock:
            cur = self.conn.cursor()
            for statement in [s.strip() for s in script.split(";") if s.strip()]:
                cur.execute(statement)
            self.conn.commit()

    def reset(self):
        self.execute("DELETE FROM trades")
        self.execute("DELETE FROM orders")
        self.commit()

    # ------------------------------------------------------------------ escrita
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
            """INSERT INTO trades (trade_id, symbol, buy_order_id, sell_order_id, qty, price)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (trade_id) DO NOTHING""",
            (t.trade_id, t.symbol, t.buy_order_id, t.sell_order_id, t.qty, t.price),
        )

    # ------------------------------------------------------------------ leitura
    def run_query(self, sql):
        """Executa uma query só de leitura (SELECT/WITH) e devolve colunas e linhas."""
        statement = sql.strip().rstrip(";").strip()
        if not statement.lower().startswith(("select", "with")) or ";" in statement:
            raise ValueError("Só são permitidas queries SELECT (uma de cada vez).")
        try:
            cur = self.execute(statement)
            cols = [d[0] for d in cur.description]
            rows = [[_plain(v) for v in r] for r in cur.fetchmany(500)]
        finally:
            with self._lock:
                self.conn.rollback()  # nunca deixa a transação aberta
        return cols, rows

    def ping(self):
        try:
            self.execute("SELECT 1").fetchone()
            return True
        except Exception:  # noqa: BLE001
            return False


def _plain(value):
    """Converte tipos do PostgreSQL (Decimal, datas) em valores simples para JSON."""
    if value is None or isinstance(value, (int, float, str)):
        return value
    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            return float(value)
    except ImportError:
        pass
    return str(value)
