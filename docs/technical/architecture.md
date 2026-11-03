# Integration architecture · QA Lab

The lab is **inspired** by Euronext's public architecture. It is not a replica of its systems.
It reproduces the kind of systems and integrations a post-trade QA engineer tests:
trading → messages → settlement → external system, with contracts, failures and reconciliation.

## Overview (one environment: QA or UAT)

```
                      ┌──────────────────────── TRADING (service "app") ─────────────────────────┐
  participant ──────► │ Order Entry Gateway → Matching Engine → Market Data    database: qa_lab   │
  (web page / API)    │        trade + event written in the SAME transaction (outbox)            │
                      └───────────────┬────────────────────────────────────────────────────────────┘
                                      │ publishes TradeExecuted v1 (contracts/trade-executed.v1.schema.json)
                                      ▼
                           ┌─────── Apache Kafka ───────┐
                           │ trades.executed            │
                           │ trades.executed.dlq (errors)│
                           └─────────────┬──────────────┘
                                         │ consumes (group settlement-service), validates the contract, idempotent
                                         ▼
                      ┌──────────────────────── SETTLEMENT ─────────────────────────────────┐
                      │ T+2 instructions · hold/release · end of day    database: settlement │
                      └───────────────┬───────────────────────────────▲──────────────────────┘
                         file SI_*.csv│                               │file CONF_*.csv
                                      ▼                               │
                      ┌────────────── T2S simulator (external system) ──────────────┐
                      │ normal · reject_symbol · reject_all · slow · unavailable     │
                      └──────────────────────────────────────────────────────────────┘
```

| Service | Container (QA) | Port QA / UAT | Database | Log |
| --- | --- | --- | --- | --- |
| Trading | `qa-lab-qa-app` | 8000 / 9000 (+ terminal 7681 / 7682) | `qa_lab` | `qa-lab.log` |
| Settlement | `qa-lab-qa-settlement` | 8100 / 9100 | `settlement` | `settlement.log` |
| T2S simulator | `qa-lab-qa-t2s` | 8200 / 9200 | — | `t2s-sim.log` |
| Kafka | `qa-lab-qa-kafka` | internal (`kafka:9092`) | — | `docker logs` |
| PostgreSQL | `qa-lab-qa-db` | 5433 / 5434 | `qa_lab` and `settlement` | — |
| Kafka topic setup (one-off) | `qa-lab-qa-kafka-init` | — | — | creates the topics, exits; `deploy.sh` checks exit code 0 and removes it |

The logs of the three services share one volume, `/var/log/qa-lab/`, and the Trading terminal can see all of them:
you can follow a trade end to end with `grep T00001 /var/log/qa-lab/*.log`.

## How it maps to what Euronext publishes

| In the lab | Public reference |
| --- | --- |
| Order Entry Gateway, Matching Engine, Market Data | Components of the Optiq platform (OEG, ME, MDG) in the technical documentation for members |
| Kafka for event-driven integration | Backend job ads for the Euronext Securities Settlement team (Porto): "Kafka (strong plus)" |
| APIs described in OpenAPI (`contracts/*.openapi.yaml`) | The same job ads: "RESTful APIs aligned with OpenAPI standards" |
| T+2 settlement with the TARGET2 calendar and T2S | Euronext Securities Porto: settlement in T2S, night-time and day-time cycles, recycling |
| Regression tests and cross-system reconciliation | Convergence project (migration of the settlement systems from mainframe to Java): proving the new system gives the same results |

## Integration patterns and how they are tested

| Pattern | Why it exists | How it is tested |
| --- | --- | --- |
| **Message contract** (JSON Schema) | Producer and consumer evolve in different teams | `tests/integration/test_integration.py` (6 invalid variations), AC-I01 |
| **Transactional outbox** | If Kafka fails, no trade is left without its event | Consumer paused → event pending → delivered later (AC-I04) |
| **At-least-once delivery + idempotency** | Kafka may deliver the same message twice | Same event sent again → 1 instruction (AC-I02) |
| **Dead letter queue** | One bad message must not block the good ones | Message outside the contract → `rejected_events` and `trades.executed.dlq` (AC-I03) |
| **File interface** | Common in banking and with external systems (T2S, custody) | `SI_*.csv` / `CONF_*.csv` files in `/var/lib/qa-lab/files` |
| **Recycling** | A failed instruction is retried in the next cycle | T2S rejects → FAILED → settles at the next end of day (AC-I05, AC-I06) |
| **Cross-system reconciliation** | Each system has its own database: differences only show when you compare | `GET /api/reconciliation` and the BDD reconciliation step |
| **Environment generation** | Events "in flight" from a previous test must not pollute the next one | An event from an old generation is ignored (pytest) |

## Looking at the messages in Kafka

```bash
# on your PC (PowerShell): messages in the topic, from the beginning
docker exec qa-lab-qa-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic trades.executed --from-beginning --timeout-ms 5000
# dead letter queue
docker exec qa-lab-qa-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic trades.executed.dlq --from-beginning --timeout-ms 5000
# consumer lag: how many messages Settlement has not processed yet
docker exec qa-lab-qa-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group settlement-service
```

## Local development and tests

| Where | Message bus | What for |
| --- | --- | --- |
| QA and UAT environments (Docker) | Kafka (`QA_LAB_KAFKA`) | The real thing |
| Local processes | Queue in an SQLite file (`QA_LAB_BUS_FILE`) | Run the three services separately without Kafka |
| pytest | In memory | Fast, deterministic tests in a single process |

The three implementations follow Kafka's semantics (commit only after processing, redelivery on failure).
The Kafka connector (`KafkaBus`) is validated in the pipeline, in the QA environment (first green run: build #7).
