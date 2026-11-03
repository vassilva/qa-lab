# Traceability matrix · QA Lab

Generated automatically by `scripts/traceability.py` on 2026-11-03. Do not edit by hand.

| Acceptance criterion | Risks | BDD scenarios | Manual cases | Defects |
| --- | --- | --- | --- | --- |
| **AC-V01** The quantity must be between 1 and 10,000 (inclusive) | R-07 (High) | Quantity limits (`features/01_order_validation.feature:17`) | TC-M03 | DEF-001 (Open (challenge mode)) |
| **AC-V02** The price must be positive, a multiple of 0.01 and within ±10% of the reference price (limits accepted) | R-08 (High) | Rejection for an invalid price (`features/01_order_validation.feature:29`)<br>Price band limits are accepted (`features/01_order_validation.feature:41`) | TC-M03 | — |
| **AC-V03** An order that is already fully filled cannot be cancelled | R-12 (Medium) | An order that is already filled cannot be cancelled (`features/01_order_validation.feature:51`) | TC-M04 | — |
| **AC-V04** Only known symbols are accepted | — | Unknown symbol is rejected (`features/01_order_validation.feature:58`) | — | — |
| **AC-N01** The trade is executed at the price of the order that was already resting in the book | R-01 (Critical) | A crossing buy executes at the price of the resting sell (`features/02_order_matching.feature:18`) | TC-M01 | DEF-002 (Open (challenge mode)) |
| **AC-N02** On a partial fill, the unfilled quantity stays in the book | R-04 (Critical) | A partial fill leaves the remainder in the book (`features/02_order_matching.feature:26`) | TC-M02 | DEF-003 (Open (challenge mode)) |
| **AC-N03** At the same price, the order that arrived first executes first | R-02 (Critical) | At the same price, the first to arrive executes first (`features/02_order_matching.feature:33`)<br>Best price has priority over arrival time (`features/02_order_matching.feature:41`) | — | DEF-004 (Open (challenge mode)) |
| **AC-N04** An order that does not cross stays in the book and creates no trade | R-11 (High) | An order that does not cross stays in the book (`features/02_order_matching.feature:50`) | — | — |
| **AC-N05** A market order without a counterparty is cancelled and does not rest in the book | R-10 (High) | A market order without a counterparty is cancelled (`features/02_order_matching.feature:57`) | — | — |
| **AC-L01** Each trade creates a PENDING instruction for T+2 business days (weekends do not count) | R-03 (Critical) | T+2 settlement date calculation (`features/03_settlement.feature:16`) | TC-M01 | — |
| **AC-L02** TARGET2 closing days (Christmas, Easter, 1 January, 1 May, 26 December) do not count | R-03 (Critical) | T+2 settlement date calculation (`features/03_settlement.feature:16`) | TC-M07 | DEF-005 (Open (challenge mode)) |
| **AC-L03** The end of day (EOD) only settles instructions that reached their intended settlement date | R-06 (Critical) | The instruction only settles at the end of day of its intended date (`features/03_settlement.feature:33`) | TC-M05 | DEF-013 (Closed) |
| **AC-L04** A held instruction is not settled until it is released | R-09 (High) | A held instruction is not settled until it is released (`features/03_settlement.feature:45`) | TC-M06 | — |
| **AC-L05** Every trade has a settlement instruction (cross-system reconciliation) | R-05 (Critical) | Reconciliation: every trade has a settlement instruction (`features/03_settlement.feature:56`) | TC-M08 | DEF-003 (Open (challenge mode)), DEF-010 (Closed), DEF-013 (Closed) |
| **AC-L06** The business date can only be a business day | R-13 (Medium) | The business date cannot be a weekend (`features/03_settlement.feature:66`) | TC-M07 | DEF-005 (Open (challenge mode)) |
| **AC-I01** Each trade publishes a TradeExecuted event that follows contract v1 | R-14 (Critical) | The trade reaches Settlement with the same data (`features/04_integration.feature:19`) | — | — |
| **AC-I02** An event delivered twice does not create a second instruction (idempotency) | R-15 (Critical) | A duplicate event does not create a second instruction (`features/04_integration.feature:26`) | — | — |
| **AC-I03** A message that breaks the contract goes to the dead letter queue and creates no instruction | R-17 (High) | A message outside the contract goes to the dead letter queue (`features/04_integration.feature:32`) | — | — |
| **AC-I04** If Settlement is unavailable, trading continues and the instructions arrive when it recovers | R-16 (Critical) | Settlement unavailable: trading continues and instructions arrive later (`features/04_integration.feature:38`) | — | — |
| **AC-I05** An instruction rejected by T2S becomes FAILED with the reason and is recycled at the next end of day | R-18 (High) | Rejection by T2S and recycling at the next end of day (`features/04_integration.feature:46`) | — | — |
| **AC-I06** If T2S is unavailable, nothing is settled and the instructions settle when it is back | R-19 (High) | T2S unavailable at end of day (`features/04_integration.feature:56`) | — | — |

## Coverage

- Acceptance criteria: **21**, with an automated scenario: **21** (100%).
- Business risks covered by criteria with a scenario: **19 of 19**.
- Manual test cases: **10** · Defects logged: **14**.
