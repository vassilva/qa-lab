-- SETTLEMENT system database (compatible with PostgreSQL and SQLite)
-- A system separate from Trading: receives trades as messages (Kafka) and never reads the Trading database.

CREATE TABLE IF NOT EXISTS settlement_instructions (
    instruction_id           VARCHAR(20)   PRIMARY KEY,
    trade_id                 VARCHAR(20)   NOT NULL UNIQUE,      -- idempotency: at most 1 instruction per trade
    event_id                 VARCHAR(32)   NOT NULL,
    symbol                   VARCHAR(10)   NOT NULL,
    qty                      INTEGER       NOT NULL,
    amount                   NUMERIC(16,2) NOT NULL,
    buy_order_id             VARCHAR(20)   NOT NULL,
    sell_order_id            VARCHAR(20)   NOT NULL,
    trade_date               DATE          NOT NULL,
    intended_settlement_date DATE          NOT NULL,
    status                   VARCHAR(20)   NOT NULL CHECK (status IN ('PENDING', 'ON_HOLD', 'FAILED', 'SETTLED')),
    fail_reason              VARCHAR(200),
    attempts                 INTEGER       NOT NULL DEFAULT 0,
    settled_on               DATE,
    received_at              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Messages that break the contract: also sent to the trades.executed.dlq topic
CREATE TABLE IF NOT EXISTS rejected_events (
    id           INTEGER       PRIMARY KEY,
    received_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason       VARCHAR(500)  NOT NULL,
    payload      TEXT          NOT NULL
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

CREATE INDEX IF NOT EXISTS idx_si_status_isd ON settlement_instructions(status, intended_settlement_date)
