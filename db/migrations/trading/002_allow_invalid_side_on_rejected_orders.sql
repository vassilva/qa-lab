-- postgres-only
-- DEF-017 · An order rejected for an invalid side (e.g. "" or "HOLD") could not be stored: the column only
-- accepted BUY/SELL, so the API answered 500 and the rejected order was lost from the audit trail.
-- Now a REJECTED order keeps the side it was sent with (up to 10 characters, longer values are refused
-- by the API with 400 before any order is created). Accepted orders are still BUY or SELL only.
ALTER TABLE orders ALTER COLUMN side TYPE VARCHAR(10);
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_side_check;
ALTER TABLE orders ADD CONSTRAINT orders_side_check CHECK (side IN ('BUY', 'SELL') OR status = 'REJECTED');
