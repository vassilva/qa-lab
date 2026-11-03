-- Esquema da base de dados do QA Lab (compatível com PostgreSQL e SQLite)
-- A aplicação cria estas tabelas no arranque, se ainda não existirem.

CREATE TABLE IF NOT EXISTS orders (
    order_id      VARCHAR(20)   PRIMARY KEY,
    symbol        VARCHAR(10)   NOT NULL,
    side          VARCHAR(4)    NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty           INTEGER       NOT NULL,
    price         NUMERIC(12,4),               -- NULL = ordem de mercado
    remaining     INTEGER       NOT NULL,
    status        VARCHAR(20)   NOT NULL,
    reject_reason VARCHAR(100),
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    trade_id      VARCHAR(20)   PRIMARY KEY,
    symbol        VARCHAR(10)   NOT NULL,
    buy_order_id  VARCHAR(20)   NOT NULL REFERENCES orders(order_id),
    sell_order_id VARCHAR(20)   NOT NULL REFERENCES orders(order_id),
    qty           INTEGER       NOT NULL CHECK (qty > 0),
    price         NUMERIC(12,4) NOT NULL,
    trade_date    DATE          NOT NULL,
    executed_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settlement_instructions (
    instruction_id           VARCHAR(20)   PRIMARY KEY,
    trade_id                 VARCHAR(20)   NOT NULL UNIQUE REFERENCES trades(trade_id),
    symbol                   VARCHAR(10)   NOT NULL,
    qty                      INTEGER       NOT NULL,
    amount                   NUMERIC(16,2) NOT NULL,
    trade_date               DATE          NOT NULL,
    intended_settlement_date DATE          NOT NULL,
    status                   VARCHAR(20)   NOT NULL CHECK (status IN ('PENDING', 'ON_HOLD', 'SETTLED')),
    settled_on               DATE,
    updated_at               TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_state (
    state_key   VARCHAR(50)  PRIMARY KEY,
    state_value VARCHAR(200) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);

CREATE INDEX IF NOT EXISTS idx_si_status_isd ON settlement_instructions(status, intended_settlement_date)
