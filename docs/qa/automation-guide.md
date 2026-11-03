# Test automation guide · QA Lab

How the automation is organised, and how to add a new test in 10 minutes.

## Frameworks and layers

| Layer | Framework | Folder | Runs against |
| --- | --- | --- | --- |
| Component (standalone) | pytest (fixtures, `parametrize`) | `tests/unit/` | In-memory code, no network or database |
| API + database | pytest + Flask test client | `tests/api/` | In-process application, temporary SQLite |
| Integration between services and contracts | pytest | `tests/integration/` | The three services in one process, in-memory bus, T2S simulator |
| Acceptance (BDD) | behave, Gherkin | `features/` + `features/steps/` | Real QA environment (REST API + PostgreSQL + Kafka), via `requests` |
| Smoke | Bash + `curl` + `jq` | `scripts/smoke.sh` | QA and UAT after each deployment |
| Data integrity | SQL | `db/qa_queries.sql`, `db/qa_queries_settlement.sql` | The environment's PostgreSQL |

Principles: the test pyramid (many fast component tests, fewer end-to-end tests);
each scenario is independent (it prepares its own data); deterministic tests (fixed dates, fixed seed in the generator);
never run destructive tests in UAT (protection in `features/environment.py`);
asynchronous results are awaited with polling and a time limit, never with fixed `sleep`s.

## BDD structure

```
features/
  01_order_validation.feature     Feature + acceptance criteria (AC-V..) + scenarios
  02_order_matching.feature       AC-N..
  03_settlement.feature           AC-L..
  04_integration.feature          AC-I..
  environment.py                  hooks: checks the environment, UAT protection, cleanup at the end
  steps/market_steps.py           steps for orders, trades, the book
  steps/settlement_steps.py       steps for settlement, EOD, reconciliation
  steps/integration_steps.py      steps for contract, duplicates, DLQ, Settlement and T2S failures
  steps/_helpers.py               eventually() (polling) and instruction lookup
```

Tags: priority (`@critical`, `@high`, `@medium`), traceability (`@AC-xxx`), area (`@gateway`, `@matching`,
`@settlement`, `@integration`), type (`@smoke`, `@boundary`, `@regression`).

## Adding a scenario (step by step)

1. Pick the acceptance criterion (or add a new one in the `.feature` file's "Acceptance criteria" section).
2. Write the scenario in business language, reusing existing steps:
   ```gherkin
   @AC-N01 @critical
   Scenario: A crossing sell executes at the price of the resting buy
     Given a clean market with business date "2026-11-02"
     And an existing order "B1" to buy 100 "GALP" at 15.20 EUR
     When order "S1" to sell 100 "GALP" at 15.10 EUR is submitted
     Then there is 1 trade of 100 shares at 15.20 EUR
   ```
3. Run only that scenario in the QA terminal: `BDD_TAGS=@AC-N01 bash scripts/run_tests.sh bdd`.
4. If a step is missing, behave prints the skeleton to implement; add it in `features/steps/`.
5. Regenerate the traceability matrix: `python3 scripts/traceability.py`. Commit, and Jenkins does the rest.

## Python support scripts

| Script | What it does |
| --- | --- |
| `scripts/test_summary.py` | Test report (Markdown + HTML): progress, coverage, criteria, risks, defects, GO/NO-GO recommendation |
| `scripts/traceability.py` | Generates the traceability matrix from the project files |
| `scripts/qa_artifacts.py` | Shared library: reads features, risks, manual cases, defects and JUnit reports |
| `scripts/generate_orders.py` | Generates reproducible orders (`--seed`) for exploration and volume, with response times |

## Flaky tests: house rules

No fixed `sleep` in the tests (the deployment waits for the healthcheck; asynchronous checks use `eventually`); data created by the scenario itself;
no dependency on today's date; an intermittent failure = a defect in the test, investigated like any other, never "run it again until it passes".
