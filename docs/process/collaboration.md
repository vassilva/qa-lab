# Collaboration with the team · QA Lab

## With whom and how

| With | When | How QA contributes | Artifact |
| --- | --- | --- | --- |
| Business analysts | Refinement, UAT | Turn rules into concrete examples; ask about edge cases | Acceptance criteria in Gherkin |
| Developers | Development, defects | Reproducible bug reports; joint root-cause analysis; PR reviews | Bug reports, PR comments |
| Fellow QAs | Always | Scenario reviews, pair testing, sharing reusable BDD steps | Test pull requests |
| Other system teams | Interface changes | Agree message contracts and test them on both sides | JSON Schema, OpenAPI, contract tests |
| Team lead / PM | Planning, release | Risks and coverage in business language; go/no-go recommendation | Test report, risk matrix |
| Operations | Deployment, incidents | Smoke tests, component-tagged logs, diagnostic scripts | `smoke.sh`, `analyze_logs.sh` |

## Example: *three amigos* session for T+2 settlement

**Participants:** BA (post-trade), developer (settlement), QA. **Duration:** 30 minutes.

| QA question | Answer / decision | Result |
| --- | --- | --- |
| Does T+2 count calendar days or business days? | TARGET2 business days | AC-L01, AC-L02 |
| Which holidays? Portuguese ones too? | Only TARGET2 closing days (10 June does not count) | Test `test_business_day` with 10 June |
| A trade on Christmas Eve settles when? | 28/12 (25 and 26 are holidays, 27 is a Sunday) | Example in the BDD outline |
| What happens to an instruction on hold on its intended date? | It stays unsettled and shows in the EOD report | AC-L04, log warning |
| Can there be two instructions for the same trade? | Never | UNIQUE constraint in the database + AC-I02 |
| Can the business date be a Saturday? | No | AC-L06 |

Value of the session: 6 ambiguous rules became testable examples **before** any code existed.

## Communicating a critical defect (example message)

> **DEF-003 (critical, P1):** on partial fills, the sell order is not reduced in the book and can execute more than the
> order quantity (100 → 140 in the test). Impact: short selling and settlement fails. Reproducible in QA in
> challenge mode, steps and evidence in the bug report. Recommendation: **no-go** until it is fixed. Available to go through it with the
> developer at 2 pm.

Characteristics: business impact first, then the evidence, the recommendation and the next step.

## Templates

- Bug report: `docs/defects/README.md`
- Pull request: `docs/process/pull-request-template.md` (also in `.github/pull_request_template.md`)
