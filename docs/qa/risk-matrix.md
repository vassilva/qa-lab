# Risk matrix · QA Lab

**Risk = likelihood × impact**, each on a scale of 1 to 3.

| Score | Priority | Scenario tag | Rule |
| --- | --- | --- | --- |
| 6 – 9 | Critical | `@critical` | Always runs; a failure blocks the release |
| 3 – 4 | High | `@high` | Runs in the full regression; a failure blocks the release |
| 1 – 2 | Medium | `@medium` | Runs in the full regression; a failure needs a decision from the owner |

**Impact:** 3 = financial loss, regulatory breach or market halted · 2 = wrong operation but correctable · 1 = annoyance, no financial effect.
**Likelihood:** 3 = complex or frequently changed logic · 2 = moderate logic · 1 = simple and stable logic.

## Business risks

| ID | Risk | Component | L | I | Score | Priority | Acceptance criteria |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | Trade executed at the wrong price (incoming order's price instead of the resting order's) | Matching Engine | 3 | 3 | 9 | Critical | AC-N01 |
| R-02 | Order at the same price executes out of arrival order (time priority) | Matching Engine | 3 | 3 | 9 | Critical | AC-N03 |
| R-03 | Wrong settlement date (weekend or TARGET2 holiday not taken into account) | Settlement | 3 | 3 | 9 | Critical | AC-L01, AC-L02 |
| R-04 | Partial fill updates the remaining quantity incorrectly | Matching Engine | 2 | 3 | 6 | Critical | AC-N02 |
| R-05 | Trade without a settlement instruction (reconciliation break) | Settlement / Integration | 2 | 3 | 6 | Critical | AC-L05 |
| R-06 | Instruction settled before its intended date | Settlement | 2 | 3 | 6 | Critical | AC-L03 |
| R-07 | Order with an invalid quantity enters the book (10,000 boundary) | Order Entry Gateway | 2 | 2 | 4 | High | AC-V01 |
| R-08 | Order outside the price bands or tick size enters the book | Order Entry Gateway | 2 | 2 | 4 | High | AC-V02 |
| R-09 | Held instruction gets settled | Settlement | 2 | 2 | 4 | High | AC-L04 |
| R-10 | Market order without a counterparty stays in the book | Matching Engine | 1 | 3 | 3 | High | AC-N05 |
| R-11 | Order that does not cross gets executed | Matching Engine | 1 | 3 | 3 | High | AC-N04 |
| R-12 | Filled order can be cancelled | Order Entry Gateway | 1 | 2 | 2 | Medium | AC-V03 |
| R-13 | Business date set to a non-business day | Settlement | 1 | 2 | 2 | Medium | AC-L06 |
| R-14 | Trade event in a format Settlement does not expect (broken contract) | Integration | 2 | 3 | 6 | Critical | AC-I01 |
| R-15 | Event delivered twice creates a duplicate instruction (double settlement) | Integration / Settlement | 2 | 3 | 6 | Critical | AC-I02 |
| R-16 | Trade lost when Settlement or Kafka is down | Integration | 2 | 3 | 6 | Critical | AC-I04 |
| R-17 | An invalid message blocks the consumption of the next ones | Integration / Settlement | 2 | 2 | 4 | High | AC-I03 |
| R-18 | Instruction rejected by T2S is forgotten (not recycled) | Settlement / T2S | 2 | 2 | 4 | High | AC-I05 |
| R-19 | Instructions marked as settled without T2S confirmation | Settlement / T2S | 1 | 3 | 3 | High | AC-I06 |

## Technical and delivery risks

| ID | Risk | L | I | Score | Mitigation |
| --- | --- | --- | --- | --- | --- |
| T-01 | The version in UAT is not the one tested in QA | 2 | 3 | 6 | The pipeline promotes the same image; the UAT smoke test confirms the version |
| T-02 | State lost after a service restart | 2 | 3 | 6 | Restore from PostgreSQL; test `test_state_restore` |
| T-03 | Environment unavailable after deployment | 2 | 2 | 4 | Container healthcheck + active wait in the deployment + smoke test |
| T-04 | Destructive tests run in UAT | 1 | 3 | 3 | The BDD framework refuses to run outside QA/LOCAL |
| T-05 | Flaky integration tests because of asynchrony | 2 | 2 | 4 | Polling with a time limit (`eventually`), environment generation to ignore old events |
| T-06 | The Kafka connector is not exercised by the fast tests | 2 | 2 | 4 | The BDD tests in QA use real Kafka; the smoke test checks `bus_ok` |

## Quick read

The nine critical risks sit in **three places**: price and execution order in the Matching Engine,
the settlement date, and the hand-over of the trade between systems (contract, duplicates, losses). That is where most of the test effort goes.
If there is only time for a short round, run `@critical` (about 1 minute).
