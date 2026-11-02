-- Esquema da base de dados do QA Lab (compatível com PostgreSQL e SQLite)

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
    executed_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)
