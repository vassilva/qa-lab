# Defect investigation and fix validation · QA Lab

How QA works with developers and fellow QAs from the defect to its closure.

## Flow

| Step | Who | What | Evidence |
| --- | --- | --- | --- |
| 1. Reproduce | QA | Reproduce with the fewest steps, in a clean environment | Steps in the bug report |
| 2. Isolate | QA | Find the component with the tagged logs (`[OEG]`, `[ME]`, `[SETTLEMENT]`), component tests and SQL | "Evidence" section |
| 3. Analyse with the dev | QA + Dev | Short session (15 min): confirm the cause, the impact and the scope of the fix | "Analysis" section |
| 4. Fix on a branch | Dev | Branch `fix/DEF-NNN-description`, with a test that reproduces the defect | Pull request |
| 5. Review | QA + Dev | Pull request review: do the fix and the new test cover the acceptance criterion? | PR comments |
| 6. Retest | QA | Repeat the bug report steps on the fixed version | Status "In retest" → "Closed" |
| 7. Regression | Pipeline | Full regression in QA to make sure nothing else broke | Green build in Jenkins |

Rule: **a defect only closes with evidence of retest and regression**, never just because "the dev said it is fixed".

## Real cases from this project

### DEF-006 · The BDD tests left the QA environment dirty
- **Investigation:** in build #3, the QA smoke showed business date 2026-11-06, but UAT showed 2026-11-03.
  The difference pointed to the last BDD scenario (`AC-L06`), which uses 2026-11-06.
- **Analysis:** the scenarios clean up before each test, but nobody cleaned up at the end. Extra risk discussed in the analysis:
  an automatic cleanup must never run in UAT.
- **Fix:** branch `fix/DEF-006-bdd-repoe-ambiente`, with an `after_all` hook that resets QA and only runs after confirming
  that the environment is not UAT.
- **Retest:** run the BDD regression and then `curl localhost:8000/api/business-date` → today's date; `GET /api/orders` → empty list.
- **Regression:** 27 scenarios and 41 component tests green (at the time).

### DEF-007 · Misleading failure message in the pipeline
- **Fix:** branch `fix/DEF-007-mensagem-falha-pipeline`.
- **Retest:** force a failure in a UAT stage (e.g. stop the UAT container during the build) and confirm the message does not
  claim the version did not reach UAT.

### DEF-012 · "Works on my machine": a library missing from the image
- **Investigation:** build #6 stopped while collecting the tests (`No module named 'yaml'`); locally all 86 tests passed.
- **Analysis:** the library was installed system-wide on the development machine but not declared in `requirements.txt`.
- **Fix and retest:** branch `fix/DEF-012`; build #7 ran the 86 tests inside the image and passed end to end.

### DEF-001 to DEF-005 · Challenge mode defects
- **Investigation:** the pipeline with `CHALLENGE_MODE` fails in "QA · BDD regression" and **does not go to UAT** (the quality gate works).
  Each failed scenario was reproduced manually through the API and confirmed in the logs and in the database.
- **"Fix" validation:** a new build with `CHALLENGE_MODE` off (equivalent to the fixed version). The same scenarios pass,
  which proves the tests detect the defect when it exists and pass when it does not.

## See the history in Git

```bash
git log --oneline --graph --all          # fix/... and feature/... branches and the merges
git show --stat <commit>                 # files changed by a fix
```
