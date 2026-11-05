# BDD scenarios (Gherkin) and how to run them

The Gherkin scenarios are in `features/*.feature` and run with **behave** against a running environment (QA by default).
They reset the environment before each scenario, so they **refuse to run in UAT**.
The pytest tests in `tests/unit`, `tests/api` and `tests/integration` have no Gherkin: see the last section.

## How to run

| What | From PowerShell (inside the QA server) | Local, in the project folder (`.venv` active, `$env:BASE_URL="http://localhost:8000"`) |
| --- | --- | --- |
| Every scenario | `docker exec qa-lab-qa-app behave features` | `behave features` |
| One feature file | `docker exec qa-lab-qa-app behave features/03_settlement.feature` | `behave features/03_settlement.feature` |
| One acceptance criterion | `docker exec qa-lab-qa-app behave --tags @AC-L03 features` | `behave --tags @AC-L03 features` |
| Critical only | `docker exec qa-lab-qa-app behave --tags @critical features` | `behave --tags @critical features` |
| Two tags together | `docker exec qa-lab-qa-app behave --tags "@critical and @settlement" features` | same with `behave` |
| By scenario name | `docker exec qa-lab-qa-app behave -n "duplicate event" features` | `behave -n "duplicate event" features` |
| One scenario by line | `docker exec qa-lab-qa-app behave features/03_settlement.feature:33` | `behave features/03_settlement.feature:33` |
| With reports (like Jenkins) | `docker exec qa-lab-qa-app bash scripts/run_tests.sh bdd` | `bash scripts/run_tests.sh bdd` (Git Bash) |

Inside the QA server the scenarios use the code of the **deployed version**; locally they use the steps in your folder against the QA environment.

## Order validation in the Order Entry Gateway

File `features/01_order_validation.feature` · run it: `docker exec qa-lab-qa-app behave features/01_order_validation.feature`

Background (runs before every scenario of this file):

```gherkin
Background:
  Given a clean market with business date "2026-11-02"
```

### Quantity limits

Run: `docker exec qa-lab-qa-app behave features/01_order_validation.feature:17` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-V01 features`

```gherkin
@AC-V01 @high @boundary
Scenario Outline: Quantity limits
  When order "B1" to buy <quantity> "EDP" at 4.50 EUR is submitted
  Then order "B1" has status "<status>"

  Examples:
    | quantity | status   |
    | 0        | REJECTED |
    | 1        | NEW      |
    | 10000    | NEW      |
    | 10001    | REJECTED |
```

### Rejection for an invalid price

Run: `docker exec qa-lab-qa-app behave features/01_order_validation.feature:29` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-V02 features`

```gherkin
@AC-V02 @high
Scenario Outline: Rejection for an invalid price
  When order "B1" to buy 100 "EDP" at <price> EUR is submitted
  Then order "B1" is rejected with reason "<reason>"

  Examples:
    | price | reason                     |
    | 4.505 | Price not on tick size     |
    | 4.96  | Price outside price bands  |
    | 4.04  | Price outside price bands  |
    | 0     | Invalid price              |
```

### Price band limits are accepted

Run: `docker exec qa-lab-qa-app behave features/01_order_validation.feature:41` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-V02 features`

```gherkin
@AC-V02 @high @boundary
Scenario Outline: Price band limits are accepted
  When order "B1" to buy 100 "EDP" at <price> EUR is submitted
  Then order "B1" has status "NEW"

  Examples:
    | price |
    | 4.05  |
    | 4.95  |
```

### An order that is already filled cannot be cancelled

Run: `docker exec qa-lab-qa-app behave features/01_order_validation.feature:51` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-V03 features`

```gherkin
@AC-V03 @medium
Scenario: An order that is already filled cannot be cancelled
  Given an existing order "S1" to sell 100 "EDP" at 4.50 EUR
  And an existing order "B1" to buy 100 "EDP" at 4.50 EUR
  When the participant tries to cancel order "S1"
  Then the cancellation is refused
```

### Unknown symbol is rejected

Run: `docker exec qa-lab-qa-app behave features/01_order_validation.feature:58` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-V04 features`

```gherkin
@AC-V04 @medium
Scenario: Unknown symbol is rejected
  When order "B1" to buy 100 "XPTO" at 4.50 EUR is submitted
  Then order "B1" is rejected with reason "Unknown symbol"
```

## Order matching in the Matching Engine

File `features/02_order_matching.feature` · run it: `docker exec qa-lab-qa-app behave features/02_order_matching.feature`

Background (runs before every scenario of this file):

```gherkin
Background:
  Given a clean market with business date "2026-11-02"
```

### A crossing buy executes at the price of the resting sell

Run: `docker exec qa-lab-qa-app behave features/02_order_matching.feature:18` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-N01 features`

```gherkin
@AC-N01 @critical @smoke
Scenario: A crossing buy executes at the price of the resting sell
  Given an existing order "S1" to sell 100 "EDP" at 4.50 EUR
  When order "B1" to buy 100 "EDP" at 4.55 EUR is submitted
  Then order "B1" has status "FILLED"
  And there is 1 trade of 100 shares at 4.50 EUR
  And the ask side of "EDP" is empty
```

### A partial fill leaves the remainder in the book

Run: `docker exec qa-lab-qa-app behave features/02_order_matching.feature:26` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-N02 features`

```gherkin
@AC-N02 @critical
Scenario: A partial fill leaves the remainder in the book
  Given an existing order "S1" to sell 100 "EDP" at 4.50 EUR
  When order "B1" to buy 40 "EDP" at 4.50 EUR is submitted
  Then order "B1" has status "FILLED"
  And order "S1" has status "PARTIALLY_FILLED" with 60 remaining
```

### At the same price, the first to arrive executes first

Run: `docker exec qa-lab-qa-app behave features/02_order_matching.feature:33` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-N03 features`

```gherkin
@AC-N03 @critical
Scenario: At the same price, the first to arrive executes first
  Given an existing order "B1" to buy 100 "EDP" at 4.48 EUR
  And an existing order "B2" to buy 100 "EDP" at 4.48 EUR
  When order "S1" to sell 100 "EDP" at 4.48 EUR is submitted
  Then order "B1" has status "FILLED"
  And order "B2" has status "NEW"
```

### Best price has priority over arrival time

Run: `docker exec qa-lab-qa-app behave features/02_order_matching.feature:41` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-N03 features`

```gherkin
@AC-N03 @critical
Scenario: Best price has priority over arrival time
  Given an existing order "S1" to sell 100 "EDP" at 4.52 EUR
  And an existing order "S2" to sell 100 "EDP" at 4.51 EUR
  When order "B1" to buy 100 "EDP" at 4.55 EUR is submitted
  Then order "S2" has status "FILLED"
  And order "S1" has status "NEW"
  And there is 1 trade of 100 shares at 4.51 EUR
```

### An order that does not cross stays in the book

Run: `docker exec qa-lab-qa-app behave features/02_order_matching.feature:50` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-N04 features`

```gherkin
@AC-N04 @high
Scenario: An order that does not cross stays in the book
  Given an existing order "S1" to sell 100 "EDP" at 4.52 EUR
  When order "B1" to buy 100 "EDP" at 4.50 EUR is submitted
  Then order "B1" has status "NEW"
  And there are no trades
```

### A market order without a counterparty is cancelled

Run: `docker exec qa-lab-qa-app behave features/02_order_matching.feature:57` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-N05 features`

```gherkin
@AC-N05 @high
Scenario: A market order without a counterparty is cancelled
  When order "B1" to buy 100 "EDP" at market is submitted
  Then order "B1" has status "CANCELLED"
  And the bid side of "EDP" is empty
```

## T+2 settlement of trades

File `features/03_settlement.feature` · run it: `docker exec qa-lab-qa-app behave features/03_settlement.feature`

### T+2 settlement date calculation

Run: `docker exec qa-lab-qa-app behave features/03_settlement.feature:16` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-L01 features`

```gherkin
@AC-L01 @AC-L02 @critical
Scenario Outline: T+2 settlement date calculation
  Given a clean market with business date "<trade date>"
  When a trade of 100 "EDP" at 4.50 EUR is executed
  Then a settlement instruction is created for "<settlement date>" with status "PENDING"

  Examples: Normal business days and weekends
    | trade date | settlement date | note                       |
    | 2026-11-02 | 2026-11-04      | Monday → Wednesday         |
    | 2026-11-05 | 2026-11-09      | Thursday → Monday          |
    | 2026-11-06 | 2026-11-10      | Friday → Tuesday           |

  Examples: TARGET2 holidays
    | trade date | settlement date | note                       |
    | 2026-12-23 | 2026-12-28      | Christmas and 26 December  |
    | 2027-03-25 | 2027-03-31      | Good Friday and Easter     |
```

### The instruction only settles at the end of day of its intended date

Run: `docker exec qa-lab-qa-app behave features/03_settlement.feature:33` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-L03 features`

```gherkin
@AC-L03 @critical @smoke
Scenario: The instruction only settles at the end of day of its intended date
  Given a clean market with business date "2026-11-06"
  And a trade of 100 "EDP" at 4.50 EUR is executed
  When the end of day is run
  Then the instruction has status "PENDING"
  And the business date becomes "2026-11-09"
  When the end of day is run
  Then the instruction has status "PENDING"
  When the end of day is run
  Then the instruction is settled on "2026-11-10"
```

### A held instruction is not settled until it is released

Run: `docker exec qa-lab-qa-app behave features/03_settlement.feature:45` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-L04 features`

```gherkin
@AC-L04 @high
Scenario: A held instruction is not settled until it is released
  Given a clean market with business date "2026-11-02"
  And a trade of 100 "EDP" at 4.50 EUR is executed
  When the instruction is put on hold
  And the end of day is run 3 times
  Then the instruction has status "ON_HOLD"
  When the instruction is released
  And the end of day is run
  Then the instruction is settled on "2026-11-05"
```

### Reconciliation: every trade has a settlement instruction

Run: `docker exec qa-lab-qa-app behave features/03_settlement.feature:56` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-L05 features`

```gherkin
@AC-L05 @critical
Scenario: Reconciliation: every trade has a settlement instruction
  Given a clean market with business date "2026-11-02"
  And an existing order "S1" to sell 300 "GALP" at 15.20 EUR
  And an existing order "B1" to buy 100 "GALP" at 15.20 EUR
  And an existing order "B2" to buy 200 "GALP" at 15.25 EUR
  Then there are 2 trades
  And every trade has a settlement instruction
  And the executed quantity of each order matches the trades
```

### The business date cannot be a weekend

Run: `docker exec qa-lab-qa-app behave features/03_settlement.feature:66` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-L06 features`

```gherkin
@AC-L06 @medium
Scenario: The business date cannot be a weekend
  Given a clean market with business date "2026-11-06"
  When someone tries to set the business date to "2026-11-07"
  Then the request is refused with status 400
  And the business date is still "2026-11-06"
```

## Integration between Trading, Settlement and T2S

File `features/04_integration.feature` · run it: `docker exec qa-lab-qa-app behave features/04_integration.feature`

Background (runs before every scenario of this file):

```gherkin
Background:
  Given a clean market with business date "2026-11-02"
```

### The trade reaches Settlement with the same data

Run: `docker exec qa-lab-qa-app behave features/04_integration.feature:19` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-I01 features`

```gherkin
@AC-I01 @critical @smoke
Scenario: The trade reaches Settlement with the same data
  When a trade of 100 "EDP" at 4.50 EUR is executed
  Then the published event follows the TradeExecuted v1 contract
  And a settlement instruction is created for "2026-11-04" with status "PENDING"
  And Trading and Settlement reconcile with no differences
```

### A duplicate event does not create a second instruction

Run: `docker exec qa-lab-qa-app behave features/04_integration.feature:26` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-I02 features`

```gherkin
@AC-I02 @critical
Scenario: A duplicate event does not create a second instruction
  Given a trade of 100 "EDP" at 4.50 EUR is executed
  When the trade event is delivered again
  Then the trade still has a single settlement instruction
```

### A message outside the contract goes to the dead letter queue

Run: `docker exec qa-lab-qa-app behave features/04_integration.feature:32` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-I03 features`

```gherkin
@AC-I03 @high
Scenario: A message outside the contract goes to the dead letter queue
  When a message with quantity 0 and no event identifier is published
  Then the message appears in the Settlement rejected events
  And there are no settlement instructions
```

### Settlement unavailable: trading continues and instructions arrive later

Run: `docker exec qa-lab-qa-app behave features/04_integration.feature:38` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-I04 features`

```gherkin
@AC-I04 @critical
Scenario: Settlement unavailable: trading continues and instructions arrive later
  Given Settlement has stopped consuming events
  When a trade of 100 "GALP" at 15.20 EUR is executed without waiting for Settlement
  Then the reconciliation shows the trade missing in Settlement
  When Settlement starts consuming events again
  Then Trading and Settlement reconcile with no differences
```

### Rejection by T2S and recycling at the next end of day

Run: `docker exec qa-lab-qa-app behave features/04_integration.feature:46` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-I05 features`

```gherkin
@AC-I05 @high
Scenario: Rejection by T2S and recycling at the next end of day
  Given a trade of 100 "EDP" at 4.50 EUR is executed
  And T2S rejects the instructions for "EDP"
  When the end of day is run 3 times
  Then the instruction has status "FAILED"
  When T2S is back to normal
  And the end of day is run
  Then the instruction is settled on "2026-11-05"
```

### T2S unavailable at end of day

Run: `docker exec qa-lab-qa-app behave features/04_integration.feature:56` · or by criterion: `docker exec qa-lab-qa-app behave --tags @AC-I06 features`

```gherkin
@AC-I06 @high
Scenario: T2S unavailable at end of day
  Given a trade of 100 "NOS" at 3.80 EUR is executed
  And T2S is unavailable
  When the end of day is run 3 times
  Then the instruction has status "FAILED"
  When T2S is back to normal
  And the end of day is run
  Then the instruction is settled on "2026-11-05"
```

## pytest tests (no Gherkin)

| Folder | What it tests | Command (local, `.venv` active) |
| --- | --- | --- |
| `tests/unit` | each component alone: gateway, matching engine, T+2 calendar, migrations | `python -m pytest tests/unit -v` |
| `tests/api` | REST endpoints: orders, validations, DEF-017 | `python -m pytest tests/api -v` |
| `tests/integration` | between services: event contract, idempotency, DLQ | `python -m pytest tests/integration -v` |
| everything | 102 tests | `python -m pytest tests -q` |

Inside the QA server: `docker exec qa-lab-qa-app python -m pytest tests -q`.

## Running the pytest tests from VS Code (Testing panel)

1. Create the virtual environment once: `python -m venv .venv` · `.venv\Scripts\Activate.ps1` · `pip install -r requirements.txt`.
2. Create `.vscode/settings.json` (personal, not versioned: `.vscode/` is in `.gitignore`):
   ```json
   {
     "python.testing.pytestEnabled": true,
     "python.testing.unittestEnabled": false,
     "python.testing.pytestArgs": ["tests"],
     "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"
   }
   ```
3. Ctrl+Shift+P → *Developer: Reload Window*, then open the Testing panel (flask icon) and click ▶ Run Tests.
