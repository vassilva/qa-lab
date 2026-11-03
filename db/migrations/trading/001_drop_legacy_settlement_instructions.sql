-- DEF-016 · Until v0.4 the settlement instructions lived in the Trading database (qa_lab).
-- Since v0.5 Settlement is a separate service with its own database (settlement), but environments
-- upgraded from v0.4 still had the old, unused table here. It was verified empty in QA (0 rows):
-- the real instructions are in settlement.settlement_instructions.
DROP TABLE IF EXISTS settlement_instructions;
