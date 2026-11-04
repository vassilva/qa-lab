# Test strategy · QA Lab (mini exchange)

| | |
| --- | --- |
| System | QA Lab: Trading (Order Entry Gateway, Matching Engine, Market Data) → Kafka → T+2 Settlement → T2S simulator |
| Document version | 1.2 · 2026-11-03 (integration between systems, v0.5.0; English, v0.6.0) |
| Owner | Vicente (QA) |
| Requirements covered | Trading and settlement rules described in `README.md` |

## 1. Objectives

| ID | Objective | How it is measured |
| --- | --- | --- |
| OBJ-1 | No invalid order reaches the order book | 100% of the gateway validation rules covered by automated tests, including boundary values |
| OBJ-2 | Correct and fair executions (price-time priority, trade price, partial fills) | Every trading acceptance criterion passes in QA |
| OBJ-3 | Every trade settles on the right date (T+2, TARGET2 calendar) | Every settlement acceptance criterion passes; trades ↔ instructions reconciliation shows no differences |
| OBJ-4 | The version approved in QA is the one that goes to UAT | The pipeline promotes the same image; the UAT smoke test confirms the version |
| OBJ-5 | Clear information for the go/no-go decision | Test report and release checklist completed for every version |
| OBJ-6 | No trade is lost, duplicated or left unsettled between systems | Criteria AC-I01 to AC-I06 pass; Trading ↔ Settlement reconciliation shows no differences |

## 2. Scope

**In scope**
- Order validation in the Order Entry Gateway (quantity, price, tick size, bands, symbol, side).
- Order matching in the Matching Engine (price-time, trade price, partial fills, market orders, cancellations).
- Market Data: order book and list of trades published by the API.
- Settlement: instruction creation, T+2 date calculation, hold/release, end of day (EOD), CSV report.
- Data integrity in PostgreSQL (executed quantities, outbox, one instruction per trade).
- REST API (status codes, error messages) and OpenAPI contracts (`contracts/*.openapi.yaml`).
- Trading → Kafka → Settlement integration: TradeExecuted v1 event contract, idempotency, dead letter queue (DLQ), consumer unavailability.
- File interface with T2S (simulated): rejections, recycling, unavailability.
- Deployment and environment health (post-deployment smoke tests).

**Out of scope (this version)**
- Performance and latency testing (a real engine measures microseconds; this lab is not representative).
- Security (authentication, authorisation) and market protocols (FIX, SBE).
- Clearing (margins, counterparty risk) and real cash or securities.
- The real T2S: replaced by a controllable simulator (standard practice when integration-testing against external systems).
- Cross-browser compatibility of the web page (it is a support tool).

## 3. Approach: standalone component tests first, then end to end

Each component is first tested **in isolation** (standalone), with controlled data and no external dependencies.
Only then is the full flow tested in a real environment.

| Level | What it tests | How it is isolated | Tool | Where it runs |
| --- | --- | --- | --- | --- |
| Component: Gateway | Validation rules, boundary values | Real in-memory Matching Engine, no database or network | pytest (`tests/unit/test_trading.py`) | Pipeline, before deployment |
| Component: Matching Engine | Price-time, partial fills, market orders, state restore | No database; fixed business date | pytest | Pipeline, before deployment |
| Component: Settlement (calendar) | T+2, weekends, TARGET2 holidays, Easter | Pure functions, fixed dates | pytest (`tests/unit/test_settlement_calendar.py`) | Pipeline, before deployment |
| Integration: API + database | Flows through the API, persistence, reconciliation | Temporary SQLite, in-process test client | pytest (`tests/api/`) | Pipeline, before deployment |
| Integration between services | Event contract, idempotency, DLQ, outbox, T2S | The three services in one process, in-memory bus, T2S simulator | pytest (`tests/integration/`) | Pipeline, before deployment |
| API contract | Every route documented in OpenAPI | Flask routes compared with `contracts/` | pytest (`tests/integration/test_openapi.py`) | Pipeline, before deployment |
| System: QA environment | Business acceptance criteria, end to end, with real Kafka | Dedicated QA environment, reset before each scenario | behave / BDD (`features/`) | Pipeline, after the QA deployment |
| Acceptance: UAT environment | Right version, healthy service, essential flow | No destructive tests (UAT is protected) | smoke test + manual validation | Pipeline, after the UAT deployment |

Standalone tests give fast diagnosis: when a BDD scenario fails, the component tests show straight away whether the problem
is in the gateway, the engine or settlement.

**Testing asynchronous integrations.** There is a queue (Kafka) between Trading and Settlement: the result is not immediate.
The BDD steps wait by **polling up to a limit** (`eventually`, 15 s) instead of fixed `sleep`s, and fail with a
message that says what was missing. The T2S simulator has modes (`reject_symbol`, `unavailable`, `slow`…) to trigger
external-system failures in a repeatable way. Details in `docs/technical/architecture.md`.

**Manual and exploratory testing** complements automation: short exploratory sessions (30–45 min) for each new
feature, especially on the web page and with unusual order combinations.

## 4. Risk-based prioritisation

Scenarios are prioritised with the risk matrix (`docs/qa/risk-matrix.md`): risk = likelihood × impact.
Each BDD scenario has a priority tag, used to choose what to run when time is short:

| Tag | When it runs | Examples |
| --- | --- | --- |
| `@critical` | Always, for every version | Trade price, price-time priority, T+2 date, duplicate events |
| `@high` | Always in the full regression | Price and quantity rejections, hold/release, T2S rejections |
| `@medium` | Full regression | Cancelling a filled order, invalid business date |

Example, critical scenarios only: `BDD_TAGS=@critical bash scripts/run_tests.sh bdd`

## 5. Environments and test data

| Environment | Use | Data |
| --- | --- | --- |
| Pipeline (temporary container) | Component and API tests | Temporary SQLite, deleted at the end |
| QA (`localhost:8000`) | Full BDD regression | Reset before each scenario (`POST /api/reset`); business date set per scenario |
| UAT (`localhost:9000`) | Release acceptance | Data kept; destructive tests **blocked** by the framework itself |

Fixed test dates (e.g. Monday 2026-11-02, Friday 2026-11-06) make the settlement tests
reproducible, whatever day they run on.

## 6. Entry and exit criteria

**Entry (we can start testing a version in QA)**
- The image build finished and the component and API tests passed (100%).
- The QA deployment finished and the smoke test passed.

**Exit from QA (the version can go to UAT)**
- 100% of `@critical` and `@high` scenarios pass.
- No open defect of critical or high severity.
- Failing `@medium` scenarios have a logged defect and a decision from the owner.

**Exit from UAT (go/no-go)**
- The UAT smoke test passed and confirms the same version tested in QA.
- Release checklist (`docs/qa/release-checklist.md`) completed.
- Approval recorded in Jenkins ("Approval · Deploy to UAT?" stage, given after the QA regression).
- A failed UAT smoke stops the pipeline and rolls UAT back to the previous version (no broken UAT).

## 7. Defects and reporting

- Each defect is logged with steps to reproduce, expected vs. actual result, version, environment and evidence
  (log line with the component tag, order/trade/instruction IDs, SQL query).
- Severity (technical impact) and priority (business urgency) are assessed separately.
- The results of each run are kept in Jenkins (JUnit report and archived artifacts).

## 8. Risks of the test process itself

| Risk | Mitigation |
| --- | --- |
| Tests that depend on today's date | Business date set in each scenario |
| Tests that interfere with each other | QA environment reset before each scenario; no parallel pipeline runs |
| Destructive tests run in UAT by mistake | The BDD framework refuses to run against any environment other than QA or LOCAL |
| Unstable environment (false negative) | Smoke test before the regression; deployment only finishes with a healthy service |
| Flaky asynchronous tests | Polling with a time limit; environment "generation" so old events are ignored |

## 9. Tools

pytest · behave (BDD, Gherkin) · Jenkins · Docker · PostgreSQL · Apache Kafka · Git · Bash scripts · Python (requests).
AI tools support scenario design and documentation, always with human review.
