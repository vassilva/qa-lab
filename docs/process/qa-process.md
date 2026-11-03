# QA process · from story to release

## Flow of a feature

| Phase | What QA does | Output | Criterion to move on |
| --- | --- | --- | --- |
| 1. Refinement | *Three amigos* session (BA + dev + QA): questions, examples, risks | Acceptance criteria in Gherkin | Definition of Ready met |
| 2. Test planning | Assess the risk, decide the levels (component, integration, BDD, manual), test data | Tagged scenarios (`@critical`…) and manual cases | Scenarios reviewed by the BA |
| 3. Development | Automate scenarios in parallel with the dev; review the PR from a testing point of view | BDD steps and component tests | Green pipeline on the branch |
| 4. Validation in QA | Automated regression + manual/exploratory testing of the feature | Logged defects, report | QA exit criteria (strategy, §6) |
| 5. Acceptance in UAT | Smoke, release checklist, validation with the business | Completed checklist | Go/no-go decision recorded in Jenkins |
| 6. After the release | Review escaped defects, update the regression, retrospective | Improvement actions | — |

## Definition of Ready (a story can enter the sprint)

- [ ] Clear business goal and known value
- [ ] Acceptance criteria written, testable and with examples (including edge cases)
- [ ] Risk assessed (likelihood × impact) and dependencies identified (other systems, message contracts)
- [ ] Test data and environment available or planned

## Definition of Done (a story is done)

- [ ] Code reviewed (pull request approved) and on `main`
- [ ] Component tests and BDD scenarios for the acceptance criteria automated and green in the pipeline
- [ ] Code coverage did not drop (pipeline report)
- [ ] Contracts (OpenAPI, event schema) updated if an interface changed
- [ ] No open defects of critical or high severity
- [ ] Traceability matrix regenerated; documentation updated
- [ ] Validated in UAT and approved at the go/no-go

## Roles

| Role | Quality responsibility |
| --- | --- |
| Business Analyst / PO | Business rules, acceptance criteria, defect priority, acceptance in UAT |
| Developer | Unit tests, fixes, technical analysis of defects |
| QA | Strategy, risk, acceptance automation, execution, defects, reporting, technical go/no-go |
| Team lead / PM | Scope decisions and accepted risk, release planning |

## Ceremonies QA takes part in

Refinement (three amigos) · planning · daily (blockers, critical defects) · sprint review (demo from UAT)
· retrospective (improvement actions for the test process).
