-- Consultas de QA · QA Lab (PostgreSQL)
-- Como correr: no terminal do ambiente  →  psql "$DATABASE_URL" -f db/consultas_qa.sql
--              ou uma a uma no Adminer (localhost:8081) ou na consola SQL da página.
-- Regra: uma verificação de integridade devolve 0 linhas quando está tudo bem.

-- 1. Visão geral: ordens por estado e lado
SELECT status, side, COUNT(*) AS ordens, SUM(qty) AS quantidade
FROM orders
GROUP BY status, side
ORDER BY status, side;

-- 2. Rejeições por motivo e símbolo
SELECT reject_reason, symbol, COUNT(*) AS rejeitadas
FROM orders
WHERE status = 'REJECTED'
GROUP BY reject_reason, symbol
ORDER BY rejeitadas DESC;

-- 3. Volume e preço médio ponderado (VWAP) por símbolo e dia
SELECT trade_date, symbol, COUNT(*) AS negocios, SUM(qty) AS volume,
       ROUND(SUM(qty * price) / NULLIF(SUM(qty), 0), 4) AS vwap
FROM trades
GROUP BY trade_date, symbol
ORDER BY trade_date, symbol;

-- 4. [Integridade] Negócios sem instrução de liquidação (AC-L05) → esperado: 0 linhas
SELECT t.trade_id, t.trade_date
FROM trades t
LEFT JOIN settlement_instructions s ON s.trade_id = t.trade_id
WHERE s.instruction_id IS NULL;

-- 5. [Integridade] Quantidade executada diferente da registada na ordem (DEF-003) → esperado: 0 linhas
SELECT o.order_id, o.qty, o.remaining, COALESCE(SUM(t.qty), 0) AS executado
FROM orders o
LEFT JOIN trades t ON o.order_id IN (t.buy_order_id, t.sell_order_id)
WHERE o.status <> 'REJECTED'
GROUP BY o.order_id, o.qty, o.remaining
HAVING o.qty - o.remaining <> COALESCE(SUM(t.qty), 0);

-- 6. [Integridade] Montante da instrução diferente de quantidade × preço do negócio → esperado: 0 linhas
SELECT s.instruction_id, s.amount, t.qty * t.price AS esperado
FROM settlement_instructions s
JOIN trades t ON t.trade_id = s.trade_id
WHERE ABS(s.amount - t.qty * t.price) > 0.01;

-- 7. [Integridade] Negócio a preço diferente do da ordem que já estava no livro (AC-N01, DEF-002) → esperado: 0 linhas
--    A ordem que estava no livro é a que chegou primeiro (identificador mais baixo).
SELECT t.trade_id, t.price,
       CASE WHEN b.order_id < s.order_id THEN b.price ELSE s.price END AS preco_do_livro
FROM trades t
JOIN orders b ON b.order_id = t.buy_order_id
JOIN orders s ON s.order_id = t.sell_order_id
WHERE t.price <> CASE WHEN b.order_id < s.order_id THEN b.price ELSE s.price END;

-- 8. [Integridade] Instruções liquidadas antes da data prevista (AC-L03) → esperado: 0 linhas
SELECT instruction_id, intended_settlement_date, settled_on
FROM settlement_instructions
WHERE status = 'SETTLED' AND settled_on < intended_settlement_date;

-- 9. Liquidações em atraso face à data de negócio atual
SELECT s.instruction_id, s.intended_settlement_date, s.status
FROM settlement_instructions s
WHERE s.status <> 'SETTLED'
  AND s.intended_settlement_date < (SELECT CAST(state_value AS DATE) FROM system_state WHERE state_key = 'business_date');

-- 10. Calendário de liquidações dos próximos dias (montante a liquidar por data)
SELECT intended_settlement_date, status, COUNT(*) AS instrucoes, SUM(amount) AS montante_eur
FROM settlement_instructions
WHERE status <> 'SETTLED'
GROUP BY intended_settlement_date, status
ORDER BY intended_settlement_date;

-- 11. Livro de ordens atual (o que ainda está à espera), melhor preço primeiro
SELECT symbol, side, price, remaining, order_id
FROM orders
WHERE status IN ('NEW', 'PARTIALLY_FILLED') AND price IS NOT NULL
ORDER BY symbol, side, CASE WHEN side = 'BUY' THEN -price ELSE price END, order_id;
