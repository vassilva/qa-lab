# Defect management · QA Lab

Each defect is a `DEF-NNN.md` file with the same structure. At the end of the project (checklist item F1)
these defects are logged in a personal test Jira; the files stay as an offline copy.

## Lifecycle

```
New → In analysis → Confirmed → In progress → Fixed → In retest → Closed
                 ↘ Rejected (not a defect)          ↘ Reopened (the retest failed)
```

## Severity and priority (assessed separately)

| Severity (technical impact, set by QA) | Example |
| --- | --- |
| **Critical** | Execution at the wrong price, selling more shares than existed, settlement on the wrong date |
| **High** | An important business rule is broken, with a possible workaround |
| **Medium** | Wrong behaviour in edge cases, no financial loss |
| **Low** | Messages, texts, operational annoyances |

| Priority (urgency, set by the business/PO) | Meaning |
| --- | --- |
| **P1** | Blocks the release: fix before go |
| **P2** | Fix in this release if possible |
| **P3** | Can wait for a later release |

## Template

```markdown
# DEF-NNN · Short, specific title

| Field | Value |
| --- | --- |
| Status | New |
| Component | Order Entry Gateway / Matching Engine / Settlement / Integration / Pipeline / Environment |
| Severity | Critical / High / Medium / Low |
| Priority | P1 / P2 / P3 |
| Environment | QA / UAT · normal or challenge mode |
| Version | 0.x.x-<commit> |
| Acceptance criterion | AC-… |
| Risk | R-… |
| Detected by | BDD scenario / manual case / log analysis / pipeline |
| Date | YYYY-MM-DD |

## Summary
## Steps to reproduce
## Expected result
## Actual result
## Evidence (API, log, SQL)
## Analysis
```

## Logged defects

| ID | Title | Component | Severity | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| [DEF-001](DEF-001.md) | Quantity 10,000 is rejected (maximum limit not included) | Order Entry Gateway | Medium | P2 | Open (challenge mode) |
| [DEF-002](DEF-002.md) | Trade executed at the incoming order's price instead of the book price | Matching Engine | Critical | P1 | Open (challenge mode) |
| [DEF-003](DEF-003.md) | A partial fill does not reduce the sell order in the book: it sells more than it had | Matching Engine | Critical | P1 | Open (challenge mode) |
| [DEF-004](DEF-004.md) | Time priority reversed for buy orders at the same price | Matching Engine | Critical | P1 | Open (challenge mode) |
| [DEF-005](DEF-005.md) | Settlement calendar ignores TARGET2 holidays | Settlement | Critical | P1 | Open (challenge mode) |
| [DEF-006](DEF-006.md) | The BDD tests leave the QA environment with test data and a test date | Tests (BDD) | Low | P2 | Closed |
| [DEF-007](DEF-007.md) | The pipeline failure message says the version did not reach UAT, even when it did | Pipeline | Low | P3 | Closed |
| [DEF-008](DEF-008.md) | The pipeline runs on the old Jenkins while the tools are being updated | Environment / Pipeline | Medium | P2 | Closed (reopened in build #4; technical fix) |
| [DEF-009](DEF-009.md) | Image build fails: the ttyd package does not exist in Debian 12 | Environment / Build | High | P1 | Closed |
| [DEF-010](DEF-010.md) | Reconciliation query fails on PostgreSQL (alias used in HAVING) | Database | Medium | P2 | Closed |
| [DEF-011](DEF-011.md) | The database backup would fail: pg_dump 15 vs. PostgreSQL 16 server | Environment / Database | High | P1 | Closed |
| [DEF-012](DEF-012.md) | OpenAPI contract tests do not start in the pipeline: PyYAML missing from the image | Environment / Build | High | P1 | Closed |
| [DEF-013](DEF-013.md) | QA integrity queries still join tables that now live in different databases | Database / QA tooling | Medium | P2 | Closed |
| [DEF-014](DEF-014.md) | The tool update script deadlocks with a running pipeline (quiet down pauses the build) | Environment / Pipeline tooling | High | P1 | Closed |
| [DEF-015](DEF-015.md) | BDD starts before the Settlement Kafka consumer is ready after a redeploy (intermittent failure) | Integration / Deployment | High | P1 | Closed |
| [DEF-016](DEF-016.md) | Orphan settlement_instructions table left in the Trading database after the Settlement split | Database / Deployment | Low | P3 | Closed |
| [DEF-017](DEF-017.md) | Order with an invalid side returns HTTP 500, exposes database details and is not persisted | Order Entry Gateway / Database | Medium | P2 | Closed |

DEF-001 to DEF-005 only exist with **challenge mode** on (Jenkins → Build with Parameters → `CHALLENGE_MODE`).
They are training defects: the "fixed version" is the same image with challenge mode off.
DEF-006 to DEF-017 are real defects found while building the lab.
