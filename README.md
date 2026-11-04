# QA Lab · Post-trade test environment

A hands-on lab I built to practise the daily work of a **Techno-Functional QA Engineer in capital markets**:
a mini stock exchange where a trade travels **order → matching → Kafka event → T+2 settlement → T2S (simulated)**,
tested end to end through **APIs, databases and Linux servers**, in **QA and UAT** environments, with a **Jenkins CI/CD pipeline** and a go/no-go gate.

> Personal learning project. The architecture is *inspired* by public information about exchange and post-trade systems.
> It is not affiliated with, nor a copy of, any company's systems. All passwords in this repo are local lab defaults.

### At a glance

| | |
| --- | --- |
| **System under test** | 3 Python services (Trading, Settlement, T2S simulator) · Apache Kafka · PostgreSQL · Docker |
| **Environments** | QA (full automated regression) and UAT (acceptance and go/no-go), same image promoted |
| **Automation** | 102 pytest tests (86% code coverage) · 33 BDD scenarios covering 21 acceptance criteria · post-deploy smoke |
| **Pipeline** | Jenkins: build → component/API tests → QA deploy, smoke, BDD → UAT deploy, smoke → go/no-go |
| **Quality docs** | Test strategy, risk matrix, manual test cases, traceability matrix, test reports, release checklist |
| **Defects** | 17 bug reports (`docs/defects/`), found while building and running the lab, each with evidence, root cause and retest |

### What it shows

| Skill | Where to look |
| --- | --- |
| Functional + technical testing of a business flow (settlement, T+2, TARGET2 calendar, recycling) | `features/03_settlement.feature`, `docs/qa/manual-test-cases.md` |
| API testing and contracts (OpenAPI, JSON Schema) | `contracts/`, `tests/integration/` |
| Integration testing: Kafka, outbox, idempotency, dead letter queue, file interface | `features/04_integration.feature`, `docs/technical/architecture.md` |
| SQL data validation and reconciliation across two databases | `db/qa_queries.sql`, `db/qa_queries_settlement.sql` |
| Linux investigation: logs, files, Kafka CLI | `docs/technical/linux-and-shell.md` |
| BDD and test automation in Python | `features/`, `tests/`, `docs/qa/automation-guide.md` |
| Risk-based test strategy and traceability | `docs/qa/test-strategy.md`, `docs/qa/risk-matrix.md`, `docs/qa/traceability-matrix.md` |
| Clear, reproducible bug reports | `docs/defects/` (e.g. DEF-015: tests started before the Kafka consumer was ready) |
| CI/CD and release decision | `Jenkinsfile`, `scripts/deploy.sh`, `scripts/smoke.sh`, `docs/qa/release-checklist.md` |

**Quick start:** see [Getting started](#getting-started-windows-powershell-in-vs-code). Progress of each skill is also shown on the lab's **/checklist** page.

## Architecture

Three separate services, each with its own database, connected by Kafka and by files
(details in `docs/technical/architecture.md`):

```
Trading (OEG → ME → Market Data) ──Kafka: trades.executed──► T+2 Settlement ──SI/CONF files──► T2S simulator
        database qa_lab              (DLQ: trades.executed.dlq)      database settlement
```

| Component | File | What it does |
| --- | --- | --- |
| Order Entry Gateway (OEG) | `app/gateway.py` | Receives and validates orders: quantity, tick size, price bands, symbol |
| Matching Engine (ME) | `app/matching_engine.py` | Matches orders by price-time priority, partial fills, market orders |
| Trading (API, Market Data, outbox) | `app/server.py` | API, order book, trades; publishes TradeExecuted through the outbox |
| Message bus | `app/bus.py` | Kafka in the environments; file or memory in local tests |
| Event contract | `contracts/trade-executed.v1.schema.json` | JSON Schema of TradeExecuted v1 |
| Settlement | `app/settlement_service.py`, `app/settlement.py` | Consumes the events; T+2 instructions, TARGET2, hold/release, end of day, recycling |
| T2S simulator | `app/t2s_simulator.py` | Confirms or rejects instructions by file; failure modes |
| API contracts | `contracts/*.openapi.yaml` | OpenAPI 3 for the three services |
| Databases | `db/schema.sql`, `db/schema_settlement.sql` | `qa_lab` (orders, trades, outbox) and `settlement` (instructions, rejected events) |

## Environments and tools

| | QA | UAT |
| --- | --- | --- |
| Purpose | Full automated tests for every version | Release acceptance and go/no-go decision |
| Mini exchange | http://localhost:8000 | http://localhost:9000 |
| Linux terminal | http://localhost:7681 | http://localhost:7682 |
| PostgreSQL (VS Code, SQL client) | `localhost:5433` | `localhost:5434` |
| Settlement (API) | http://localhost:8100 | http://localhost:9100 |
| T2S simulator (API) | http://localhost:8200 | http://localhost:9200 |
| Containers | `qa-lab-qa-{app,settlement,t2s,kafka,db}` | `qa-lab-uat-{app,settlement,t2s,kafka,db}` |

Shared:
- **Jenkins** http://localhost:8090 (user `admin`, password `admin`)
- **Adminer** http://localhost:8081 (system PostgreSQL · server `qa-lab-qa-db` or `qa-lab-uat-db` · user `qa` · password `qa` · database `qa_lab` or `settlement`)

Databases: user `qa`, password `qa`, databases `qa_lab` (Trading) and `settlement`.

## Pipeline (Jenkinsfile)

```
Prepare → Build image → Component and API tests
  → QA · Deploy → QA · Smoke → QA · BDD regression
  → UAT · Deploy → UAT · Smoke → UAT · Test summary → UAT · Go/No-go
```

The image is built **once** (`qa-lab:<version>-<commit>`) and the same image is promoted from QA to UAT.
Jenkins polls the repository every 2 minutes: every `git commit` triggers the pipeline. There is also a nightly
regression in QA (weekdays, ~02:00) that is not promoted to UAT. Parameters: `REGRESSION` (full/critical) and `CHALLENGE_MODE`.

Docker Desktop shows three groups: **`qa`**, **`uat`** and **`qa-lab-tools`** (Jenkins + Adminer).

## Tests

| Level | Where | How to run |
| --- | --- | --- |
| Components and API (standalone) | `tests/` (pytest) | `bash scripts/run_tests.sh unit` |
| Integration between services and contracts | `tests/integration/` (pytest) | included in `unit` |
| BDD acceptance (Gherkin) | `features/` (behave) | `bash scripts/run_tests.sh bdd` (QA only) |
| Critical only | | `BDD_TAGS=@critical bash scripts/run_tests.sh bdd` |
| One acceptance criterion | | `BDD_TAGS=@AC-L03 bash scripts/run_tests.sh bdd` |
| Post-deploy smoke | `scripts/smoke.sh` | `bash scripts/smoke.sh` |
| Data integrity (Trading) | `db/qa_queries.sql` | `psql "$DATABASE_URL" -f db/qa_queries.sql` |
| Data integrity (Settlement) | `db/qa_queries_settlement.sql` | in the Settlement container: `psql "$DATABASE_URL" -f db/qa_queries_settlement.sql` |
| Test report | `scripts/test_summary.py` | `python3 scripts/test_summary.py reports` → `localhost:8000/reports/` |
| Traceability | `scripts/traceability.py` | `python3 scripts/traceability.py` |

Today: **102** pytest tests (86% code coverage) and **33** BDD scenarios (21 acceptance criteria, 100% automated).

The BDD scenarios reset the data, so they **refuse to run in UAT**.
In Jenkins, **Build with Parameters** lets you choose a `full` or `critical` regression.

All documentation is in `docs/` and in the index at **`localhost:8000/docs/`**: quality (strategy, risk, manual cases,
reports, traceability, automation, AI), defects, technical guides (architecture, Linux, SQL, Git, Jenkins), process and onboarding.

## Getting started (Windows, PowerShell in VS Code)

Prerequisites: Docker Desktop running, and Git.

```powershell
docker network create qa-lab-net        # first time only
docker compose up -d --build            # Jenkins + Adminer (takes a few minutes the first time)
```

Docker Desktop needs **~6 GB of memory** (Settings → Resources): each environment has Kafka and three services.

**Updating the lab to a new version** (prevents DEF-008 and DEF-014):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update_tools.ps1 -PauseOnly   # 1. pause the pipeline (running builds finish)
# 2. replace the project files and commit
powershell -ExecutionPolicy Bypass -File scripts\update_tools.ps1              # 3. rebuild, restart Jenkins and resume the pipeline
```

Then open http://localhost:8090, sign in with `admin` / `admin`, open **qa-lab-pipeline** and click
**Build Now**. The pipeline builds the image and creates the QA and UAT environments. At the end it waits for your
approval (go/no-go).

Useful commands:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"   # what is running
docker exec -it qa-lab-qa-app bash                                # open a shell on the QA server (like ssh)
docker logs qa-lab-uat-app                                        # UAT startup messages
docker exec qa-lab-qa-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic trades.executed --from-beginning --timeout-ms 5000   # messages in Kafka
docker compose -p qa down                                         # stop QA (data is kept)
docker compose down                                               # stop Jenkins and Adminer
```

Inside the Linux server (browser terminal or `docker exec`):

```bash
tail -f /var/log/qa-lab/qa-lab.log            # Trading log, with [OEG] [ME] [API] tags
tail -f /var/log/qa-lab/settlement.log        # Settlement log (consumer, EOD)
grep -h T00001 /var/log/qa-lab/*.log          # one trade followed across the three services
ls /var/log/qa-lab/eod/                       # end-of-day CSV reports
bash scripts/smoke.sh                         # smoke test
bash scripts/run_tests.sh unit                # unit and API tests
```

## Business rules

**Trading**
- Symbols and reference prices (EUR): BCP 0.65 · EDP 4.50 · GALP 15.20 · NOS 3.80.
- Limit orders (with a price) or market orders (no price).
- Quantity from 1 to 10,000; price a multiple of 0.01; price within ±10% of the reference (limits included).
- Price-time priority; the trade happens at the price of the order already resting in the book.
- Partial fill: the remainder stays in the book. A market order with no counterparty is cancelled.

**Settlement**
- Each trade creates a settlement instruction for T+2 business days.
- Business days: Monday to Friday, except TARGET2 closing days (1 Jan, Good Friday,
  Easter Monday, 1 May, 25 and 26 Dec).
- Statuses: `PENDING` → `SETTLED`; `ON_HOLD` (hold) does not settle until released (release);
  `FAILED` when T2S rejects it or does not answer: it is recycled at the next end of day.
- At end of day, Settlement sends an `SI_*.csv` file to T2S and reads the `CONF_*.csv` confirmation.
- The end of day (EOD) settles the instructions that are due, writes `eod/settlement_YYYYMMDD.csv`
  and moves the business date to the next business day.

**Challenge mode:** with `QA_LAB_CHALLENGE=1` the application gets hidden defects, to practise
defect analysis and reporting.

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Status, environment, version and database |
| GET | `/api/symbols` | Symbols and reference prices |
| POST | `/api/orders` | New order: `{"symbol":"EDP","side":"BUY","qty":100,"price":4.50}` (no `price` = market order) |
| DELETE | `/api/orders/<id>` | Cancel an order |
| GET | `/api/orders?status=FILLED` | List orders |
| GET | `/api/book/<symbol>` | Order book |
| GET | `/api/trades` | Trades |
| GET / POST | `/api/business-date` | Get or change the business date: `{"date":"2026-11-06"}` (business days only) |
| GET | `/api/settlement/instructions?status=PENDING` | Settlement instructions |
| POST | `/api/settlement/instructions/<id>/hold` · `/release` | Hold or release an instruction |
| POST | `/api/eod` | End of day |
| POST | `/api/query` | Read-only SQL query: `{"sql":"SELECT ..."}` |
| GET | `/api/integration` | Status of the message bus, outbox, Settlement and T2S |
| GET | `/api/reconciliation` | Differences between trades (Trading) and instructions (Settlement) |
| POST | `/api/t2s/mode` | T2S simulator mode: `{"mode":"reject_symbol","symbol":"GALP"}` (QA only) |
| POST | `/api/reset` | Delete the environment data (Trading, Settlement and T2S) |

Full contracts: `contracts/trading.openapi.yaml`, `settlement.openapi.yaml`, `t2s-simulator.openapi.yaml`.

## Structure

```
app/                 application components and web pages (app/static)
contracts/           event JSON Schema and OpenAPI for the three services
db/                  database schemas (qa_lab, settlement) and QA queries
docker/              container startup
envs/                QA and UAT environment configuration
features/            BDD scenarios (Gherkin) and automated steps (features/steps)
docs/                qa/ defects/ technical/ process/ onboarding/ (index at /docs/)
jenkins/             the lab's Jenkins (configuration as code)
scripts/             deploy, smoke, tests, report, traceability, logs, EOD, backup, order generator
tests/               pytest tests (unit, API, integration)
Jenkinsfile          CI/CD pipeline
docker-compose.yml   Jenkins + Adminer
docker-compose.env.yml  definition of one environment (used for QA and UAT)
checklist.json       status of the job description features
```
