-- Base de dados do sistema TRADING (compatível com PostgreSQL e SQLite)
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

-- Padrão "transactional outbox": o evento é gravado na MESMA transação que o negócio
-- e publicado no Kafka depois. Se o Kafka estiver em baixo, nada se perde: fica pendente aqui.
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

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);

CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox_events(published_at)
