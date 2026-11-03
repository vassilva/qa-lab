# Retrospective and continuous improvement · QA Lab

Retrospective of building the lab (2–3 November 2026), with real facts from the project.

## What went well

- The quality gate works: with defects active, the regression fails and nothing reaches UAT.
- Promoting the same image from QA to UAT removed the question "is what we tested what got installed?".
- Validating SQL on the same engine as production caught an error before it reached an environment (DEF-010).
- Reading the logs carefully (build times vs. update times) avoided "fixing" code that had no defect (DEF-008).
- The real Kafka integration passed first time in the pipeline (build #7), because the bus semantics had been tested locally.

## What went less well

| Fact | Cause | Lesson |
| --- | --- | --- |
| The image build failed the first time (DEF-009) | A dependency assumed without checking | Check package availability in the target distribution |
| The pipeline ran on the old Jenkins, twice (DEF-008) | Infrastructure update running in parallel with the automatic trigger | A process rule was not enough: make it impossible (quiet down script) |
| Tests left QA dirty (DEF-006) | There was setup but no cleanup | Each suite leaves the environment as it found it |
| Misleading failure message (DEF-007) | Generic text that claimed something not always true | Messages must not claim what they do not know |
| Docker group names were confusing (`qa-lab` looked like an environment) | Default name taken from the folder | Give groups explicit names: `qa`, `uat`, `qa-lab-tools` |
| PostgreSQL client and server on different versions (DEF-011) | Images chosen separately | Check the compatibility of operational tools (backups) |
| "Works on my machine" (DEF-012) | A library installed locally but not declared | Run the tests in the same image that gets promoted |
| QA queries broke after the architecture change (DEF-013) | Tooling outside the test suite was not reviewed | An architecture change includes the QA tooling, not just code and tests |
| A link to the corporate Jira was about to be used for test data | The tool had access | Test data never goes into corporate systems; personal Jira (F1) |

## Improvement actions

| # | Action | Owner | Status |
| --- | --- | --- | --- |
| A1 | Cleanup at the end of the BDD tests, with UAT protection | QA | ✓ Done (DEF-006) |
| A2 | Jenkins stages grouped by environment (QA · / UAT ·) | QA | ✓ Done |
| A3 | Groups `qa`, `uat`, `qa-lab-tools`, with automatic migration in the deployment | QA | ✓ Done |
| A4 | Measure code coverage in the pipeline and raise it from 85% to 93% | QA | ✓ Done |
| A5 | HTML report with criteria, risks and defects for the go/no-go | QA | ✓ Done |
| A6 | SQL integrity checks as a pipeline stage | QA | Planned (automation plan #1) |
| A7 | UI tests with Playwright for 3 manual cases | QA | Planned (automation plan #3) |
| A8 | Log the defects in a personal test Jira | QA | Planned (F1) |
| A9 | Safe tool update script (pause job → rebuild → resume) | QA | ✓ Done (DEF-008, corrected by DEF-014) |

## Metrics to track between releases

Defects found in QA vs. in UAT (defect leakage) · time from commit to QA validated · coverage of acceptance
criteria and of code · flaky scenarios (should be 0) · average time to fix by severity.
