# Automation coverage and improvement plan · QA Lab

## Where we are (version 0.6.0)

| Measure | Value | How it is measured |
| --- | --- | --- |
| Acceptance criteria with an automated scenario | **21 of 21 (100%)** | `scripts/traceability.py` |
| Business risks covered | **19 of 19** | Traceability matrix |
| Code coverage (component and API tests) | **86%** (93% in v0.4.0; the difference is the Kafka connector, tested only in the QA environment) | pytest-cov, in the "Component and API tests" stage |
| Automated tests | **87** pytest (component, API, integration, contracts) + **33** BDD scenarios | JUnit reports in Jenkins |
| Manual cases fully or partly automated | **8 of 10** | `manual-test-cases.md` |
| Feedback time for a commit | ~2 minutes until QA is validated | Stage durations in Jenkins |
| Training defects caught by the regression | **5 of 5** (8 scenarios fail in challenge mode) | Pipeline with `CHALLENGE_MODE` |

## Improvements already made

| Date | Improvement | Result |
| --- | --- | --- |
| 2026-11-03 | 21 API tests for routes without coverage (`tests/api/test_api_routes.py`) | Coverage 85% → 93%; `server.py` 72% → 92% |
| 2026-11-03 | SQL integrity checks (`db/qa_queries.sql`) | Detect DEF-002 and DEF-003 straight in the database |
| 2026-11-03 | Environment cleanup after the BDD tests (DEF-006) | QA stays clean and with today's date |
| 2026-11-03 | HTML report with criteria coverage, risks and defects | Go/no-go decision with structured information |
| 2026-11-03 | Integration tests and OpenAPI contract test (v0.5.0) | 6 new acceptance criteria (AC-I), every route documented |
| 2026-11-03 | QA queries split per database (DEF-013) | Integrity checks work again after the architecture change |

## Gaps and next steps (by risk priority)

| # | Gap | Risk | Proposed action | Effort |
| --- | --- | --- | --- | --- |
| 1 | The SQL checks do not run in the pipeline (DEF-013 went unnoticed for that reason) | R-04, R-05 | "QA · Data integrity" stage that runs both query files and fails if any check returns rows | Low |
| 2 | The content of the end-of-day CSV is not checked automatically | R-06 | BDD scenario that runs `scripts/eod.sh` and validates the file | Low |
| 3 | The web page is only tested manually | Low | 3 UI tests with Playwright (TC-M01, TC-M02, TC-M04) | Medium |
| 4 | No volume tests | T-03 | `scripts/generate_orders.py --n 5000` in the nightly pipeline, with a response-time limit (p95) | Low |
| 5 | No mutation testing | Test quality | Use challenge mode as known "mutants": the regression must always fail | Already possible, not yet automated |
| 6 | Consumer lag is not monitored | R-16 | Check the `settlement-service` consumer group lag in the smoke test | Low |

Continuous improvement rule: every defect found outside the automation creates a new automated test,
or a written reason why it is not worth it.
