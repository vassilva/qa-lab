-- QA queries · SETTLEMENT database (settlement) · PostgreSQL
-- How to run: in the Settlement container  →  docker exec -it qa-lab-qa-settlement bash
--                                              psql "$DATABASE_URL" -f db/qa_queries_settlement.sql
--             or one by one in Adminer (localhost:8081, database settlement) or in the page's SQL console ([Settlement]).
-- Rule: an integrity check returns 0 rows when everything is fine.

-- 1. Instructions by status
SELECT status, COUNT(*) AS instructions, SUM(amount) AS amount_eur
FROM settlement_instructions
GROUP BY status
ORDER BY status;

-- 2. [Integrity] Instructions settled before their intended settlement date (AC-L03) → expected: 0 rows
SELECT instruction_id, intended_settlement_date, settled_on
FROM settlement_instructions
WHERE status = 'SETTLED' AND settled_on < intended_settlement_date;

-- 3. [Integrity] More than one instruction for the same trade (idempotency, AC-I02) → expected: 0 rows
--    (the UNIQUE constraint on trade_id should make this impossible; the query proves it)
SELECT trade_id, COUNT(*) AS instructions
FROM settlement_instructions
GROUP BY trade_id
HAVING COUNT(*) > 1;

-- 4. Settlements overdue against the current business date
SELECT s.instruction_id, s.intended_settlement_date, s.status, s.fail_reason
FROM settlement_instructions s
WHERE s.status <> 'SETTLED'
  AND s.intended_settlement_date < (SELECT CAST(state_value AS DATE) FROM system_state WHERE state_key = 'business_date');

-- 5. Failed instructions waiting for recycling (rejected by T2S or no confirmation)
SELECT instruction_id, trade_id, symbol, attempts, fail_reason, updated_at
FROM settlement_instructions
WHERE status = 'FAILED'
ORDER BY attempts DESC, instruction_id;

-- 6. Settlement calendar for the coming days (amount to settle by date)
SELECT intended_settlement_date, status, COUNT(*) AS instructions, SUM(amount) AS amount_eur
FROM settlement_instructions
WHERE status <> 'SETTLED'
GROUP BY intended_settlement_date, status
ORDER BY intended_settlement_date;

-- 7. Messages rejected by the contract (also in the trades.executed.dlq topic)
SELECT id, reason, received_at
FROM rejected_events
ORDER BY id DESC;
