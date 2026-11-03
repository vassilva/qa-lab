-- QA queries · TRADING database (qa_lab) · PostgreSQL
-- How to run: in the Trading container terminal  →  psql "$DATABASE_URL" -f db/qa_queries.sql
--             or one by one in Adminer (localhost:8081, database qa_lab) or in the page's SQL console ([Trading]).
-- Rule: an integrity check returns 0 rows when everything is fine.
-- Settlement checks are in db/qa_queries_settlement.sql. Checks ACROSS the two databases
-- (every trade has an instruction, amounts match) are done by GET /api/reconciliation:
-- each system has its own database, so no single SQL query can see both (DEF-013).

-- 1. Overview: orders by status and side
SELECT status, side, COUNT(*) AS orders, SUM(qty) AS quantity
FROM orders
GROUP BY status, side
ORDER BY status, side;

-- 2. Rejections by reason and symbol
SELECT reject_reason, symbol, COUNT(*) AS rejected
FROM orders
WHERE status = 'REJECTED'
GROUP BY reject_reason, symbol
ORDER BY rejected DESC;

-- 3. Volume and volume-weighted average price (VWAP) by symbol and day
SELECT trade_date, symbol, COUNT(*) AS trades, SUM(qty) AS volume,
       ROUND(SUM(qty * price) / NULLIF(SUM(qty), 0), 4) AS vwap
FROM trades
GROUP BY trade_date, symbol
ORDER BY trade_date, symbol;

-- 4. [Integrity] Executed quantity different from the quantity recorded on the order (DEF-003) → expected: 0 rows
SELECT o.order_id, o.qty, o.remaining, COALESCE(SUM(t.qty), 0) AS executed
FROM orders o
LEFT JOIN trades t ON o.order_id IN (t.buy_order_id, t.sell_order_id)
WHERE o.status <> 'REJECTED'
GROUP BY o.order_id, o.qty, o.remaining
HAVING o.qty - o.remaining <> COALESCE(SUM(t.qty), 0);

-- 5. [Integrity] Trade at a price different from the resting order's price (AC-N01, DEF-002) → expected: 0 rows
--    The resting order is the one that arrived first (lower identifier).
SELECT t.trade_id, t.price,
       CASE WHEN b.order_id < s.order_id THEN b.price ELSE s.price END AS book_price
FROM trades t
JOIN orders b ON b.order_id = t.buy_order_id
JOIN orders s ON s.order_id = t.sell_order_id
WHERE t.price <> CASE WHEN b.order_id < s.order_id THEN b.price ELSE s.price END;

-- 6. [Integrity] Trades whose event was never published to Kafka (outbox stuck) → expected: 0 rows
--    (a few seconds of delay are normal; rows that stay here mean Kafka or the publisher is down)
SELECT t.trade_id, e.event_id, e.attempts, e.last_error, e.created_at
FROM trades t
LEFT JOIN outbox_events e ON e.event_key = t.trade_id
WHERE e.event_id IS NULL OR e.published_at IS NULL;

-- 7. Current order book (what is still waiting), best price first
SELECT symbol, side, price, remaining, order_id
FROM orders
WHERE status IN ('NEW', 'PARTIALLY_FILLED') AND price IS NOT NULL
ORDER BY symbol, side, CASE WHEN side = 'BUY' THEN -price ELSE price END, order_id;
