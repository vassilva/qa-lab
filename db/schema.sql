-- TRADING system database (compatible with PostgreSQL and SQLite)
-- The application creates these tables at startup if they do not exist yet.

CREATE TABLE IF NOT EXISTS orders (
    order_id      VARCHAR(20)   PRIMARY KEY,
    symbol        VARCHAR(10)   NOT NULL,
    side          VARCHAR(10)   NOT NULL,                -- BUY or SELL (a REJECTED order keeps what was sent, DEF-017)
    qty           INTEGER       NOT NULL,
    price         NUMERIC(12,4),               -- NULL = market order
    remaining     INTEGER       NOT NULL,
    status        VARCHAR(20)   NOT NULL,
    reject_reason VARCHAR(100),
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT orders_side_check CHECK (side IN ('BUY', 'SELL') OR status = 'REJECTED')
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

-- "Transactional outbox" pattern: the event is stored in the SAME transaction as the trade
-- and published to Kafka afterwards. If Kafka is down, nothing is lost: it stays pending here.
CREATE TABLE IF NOT EXISTS outbox_events (
    event_id      VARCHAR(32)   PRIMARY KEY,
    topic         VARCHAR(100)  NOT NULL,
    event_key     VARCHAR(50)   NOT NULL,
    payload       TEXT          NOT NULL,
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at  TIMESTAMP,
    attempts      INTEGER       NOT NULL DEFAULT 0,
    last_error    VARCHAR(300)
);

CREATE TABLE IF NOT EXISTS system_state (
    state_key   VARCHAR(50)  PRIMARY KEY,
    state_value VARCHAR(200) NOT NULL
);

-- Applied schema migrations (see db/migrations/): each one runs once per database
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(100) PRIMARY KEY,
    applied_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);

CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox_events(published_at)
