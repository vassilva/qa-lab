# Test report · version 0.3.0-c200193

| | |
| --- | --- |
| Period | 2026-11-03 |
| Environments | QA (`localhost:8000`) and UAT (`localhost:9000`), PostgreSQL 16 (moved to 15 in version 0.4.0, see DEF-011) |
| Jenkins builds | #2 (infrastructure failure) and #3 (approved) |
| Owner | Vicente (QA) |

## 1. Summary for decision

**Recommendation: GO**, given when build #3 was approved at 12:31.
All automated tests passed, the same version was confirmed in UAT and there are no open defects affecting this version.
The only failure in the period (build #2) was an infrastructure failure, not a product failure (DEF-008).

## 2. Progress

| Activity | Planned | Run | Passed | Failed |
| --- | ---: | ---: | ---: | ---: |
| Component and API tests (pytest) | 41 | 41 | 41 | 0 |
| BDD scenarios in QA (behave, PostgreSQL) | 27 | 27 | 27 | 0 |
| QA and UAT smoke | 2 | 2 | 2 | 0 |
| Manual cases (`manual-test-cases.md`) | 10 | to be logged | | |

## 3. Coverage

- **Acceptance criteria:** 15 of 15 with an automated scenario, all green (100%).
- **Business risks:** 13 of 13 covered; the 6 critical risks have `@critical` scenarios that run for every version.
- **Components:** Order Entry Gateway, Matching Engine and Settlement with standalone and end-to-end tests.
- **Out of scope:** performance, security, FIX/SBE protocols, clearing (see the test strategy).

## 4. Defects

| Status | Count | Detail |
| --- | ---: | --- |
| Found in the period | 6 real | DEF-006 to DEF-011 |
| Closed | 6 | Fixes validated with retest and regression |
| Open and affecting the version | 0 | |
| Training defects (challenge mode) | 5 | DEF-001 to DEF-005; they do not exist with challenge mode off |

With challenge mode on, the regression fails in 8 scenarios, 7 acceptance criteria and 6 critical or high risks,
and the version **does not go to UAT**. This confirms that the pipeline's quality gate works.

## 5. Risks and observations

| Observation | Impact | Action |
| --- | --- | --- |
| The BDD tests left QA with test data (DEF-006) | Confusion for whoever uses QA next | Fixed: cleanup at the end of the tests |
| Updating the tools while Jenkins polls for commits causes false failures (DEF-008) | Red builds with no product defect | Process: update the tools before the commits (later replaced by a technical fix) |
| Manual cases not yet logged | Web page coverage not evidenced | Run TC-M01 to TC-M10 in the next version |

## 6. Evidence

Jenkins (`localhost:8090`): builds #2 and #3, **Tests** tab and archived artifacts. QA HTML report at
`localhost:8000/reports/`. Traceability in [traceability-matrix.md](traceability-matrix.md).
