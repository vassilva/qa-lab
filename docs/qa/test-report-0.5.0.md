# Test report · version 0.5.0-d825d59

| | |
| --- | --- |
| Period | 2026-11-03 |
| Environments | QA (`localhost:8000`) and UAT (`localhost:9000`): Trading, Settlement, T2S simulator, Apache Kafka 3.9, PostgreSQL 15 |
| Jenkins builds | #6 (failed: DEF-012) and #7 (approved) |
| Owner | Vicente (QA) |

## 1. Summary for decision

**Recommendation: GO**, given when build #7 was approved at 14:45.
First version with the integration architecture (Trading → Kafka → Settlement → T2S). All automated tests passed
**with real Kafka** in QA, the same image was confirmed in UAT and no open defect affects the version.
Build #6 failed before deployment because of a library missing from the image (DEF-012); the version reached neither QA nor UAT.

## 2. Progress

| Activity | Planned | Run | Passed | Failed |
| --- | ---: | ---: | ---: | ---: |
| Component, API, integration and contract tests (pytest) | 86 | 86 | 86 | 0 |
| BDD scenarios in QA (behave, PostgreSQL, Kafka) | 33 | 33 | 33 | 0 |
| QA and UAT smoke (incl. bus, Settlement and T2S) | 2 | 2 | 2 | 0 |

Code coverage: 85.7% (the Kafka connector is covered by the BDD run in QA, not by pytest).

## 3. Coverage

- **Acceptance criteria:** 21 of 21 with an automated scenario, all green (100%); 6 of them new (AC-I01 to AC-I06).
- **Business risks:** 19 of 19 covered; the 9 critical risks have `@critical` scenarios.
- **Integration:** event contract, duplicate delivery, dead letter queue, consumer down, T2S rejection and T2S unavailable.

## 4. Defects

| Status | Count | Detail |
| --- | ---: | --- |
| Found in the period | 2 real | DEF-012 (pipeline), DEF-013 (QA tooling, found after the release during review) |
| Reopened | 1 | DEF-008, closed with a technical fix |
| Open and affecting the version | 0 | |

## 5. Evidence

Jenkins builds #6 and #7 (console output, **Tests** tab). Kafka consumer group check:
`kafka-consumer-groups.sh --describe --group settlement-service` → LAG 0.
