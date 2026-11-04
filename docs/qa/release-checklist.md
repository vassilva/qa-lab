# Release validation checklist (go/no-go)

Fill in for each version before approving the **"Approval · Deploy to UAT?"** stage in Jenkins
(after the QA smoke and BDD regression). After the approval, a failed UAT smoke stops the pipeline and rolls UAT back.

| Field | Value |
| --- | --- |
| Version | `0.x.x-<commit>` (see the build name in Jenkins) |
| Date | |
| QA owner | |

## 1. Version quality (QA)

- [ ] Component and API tests: 100% passed ("Component and API tests" stage)
- [ ] QA smoke passed
- [ ] BDD regression in QA: 100% of `@critical` and `@high` scenarios passed
- [ ] Failed `@medium` scenarios (if any) have a logged defect and a decision
- [ ] No open defects of critical or high severity
- [ ] "UAT · Test summary" in Jenkins with recommendation **GO**

## 2. Deployment (UAT)

- [ ] The UAT page badge (`localhost:9000`) shows **the same version** that was tested in QA
- [ ] UAT smoke passed (service UP, connected to PostgreSQL, order accepted, Kafka, Settlement and T2S available)
- [ ] `/health` in UAT responds `"status": "UP"` and `"challenge_mode": false`

## 3. Functional validation in UAT (manual, 5–10 minutes)

- [ ] Send a sell and a buy that cross: the trade shows at the resting order's price
- [ ] The trade creates a settlement instruction with the right T+2 date (it arrives through Kafka within seconds)
- [ ] **Reconcile systems** shows `"ok": true`
- [ ] An invalid order (e.g. quantity 10,001) is rejected with a clear reason
- [ ] The end of day (EOD) runs and the CSV report appears in `/var/log/qa-lab/eod/` (UAT terminal, `localhost:7682`)
- [ ] The logs have no unexpected errors: `grep -c ERROR /var/log/qa-lab/*.log`

## 4. Decision

| Decision | Criterion |
| --- | --- |
| **GO** | Every point in sections 1 to 3 confirmed |
| **GO with accepted risks** | Only `@medium` / minor points fail, with a logged defect and the owner's acceptance |
| **NO-GO** | Any `@critical` or `@high` failure, a different version in UAT, or an unstable service |

Decision: ______  Rationale: ____________________________________________
