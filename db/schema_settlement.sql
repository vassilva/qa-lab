-- Base de dados do sistema SETTLEMENT (compatível com PostgreSQL e SQLite)
-- Sistema separado do Trading: recebe os negócios por mensagens (Kafka), nunca lê a base do Trading.

CREATE TABLE IF NOT EXISTS settlement_instructions (
    instruction_id           VARCHAR(20)   PRIMARY KEY,
    trade_id                 VARCHAR(20)   NOT NULL UNIQUE,      -- idempotência: no máximo 1 instrução por negócio
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

-- Mensagens que não respeitam o contrato: também enviadas para o tópico trades.executed.dlq
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

CREATE INDEX IF NOT EXISTS idx_si_status_isd ON settlement_instructions(status, intended_settlement_date)
