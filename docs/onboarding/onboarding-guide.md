# Onboarding guide · new QA team member

A 5-day plan for someone with no domain experience to become autonomous in the QA Lab.
Each day has a goal, short reading and a hands-on exercise. A more experienced team member pairs with them (pair testing).

| Day | Goal | Read | Do |
| --- | --- | --- | --- |
| 1 | Understand the business | `README.md` (business rules), `docs/qa/test-strategy.md` | On the mini exchange: run TC-M01 and TC-M02 and explain why the trade is at 4.50 |
| 2 | Environments, architecture and Linux | `docs/technical/architecture.md`, `docs/technical/linux-and-shell.md` | Exercises 1 to 10 in the QA terminal; follow an order through the three services' logs |
| 3 | Automated tests | `docs/qa/automation-guide.md` | Run `run_tests.sh unit` and `bdd`; add a BDD scenario on a Git branch |
| 4 | Defects | `docs/defects/README.md`, DEF-002 and DEF-003 | Pipeline with `CHALLENGE_MODE`; reproduce DEF-004 on your own and write the bug report |
| 5 | Release | `docs/qa/release-checklist.md`, `docs/technical/jenkins.md` | Follow a full pipeline, fill in the checklist and present the go/no-go to the team |

## Quick glossary

| Term | Meaning |
| --- | --- |
| Order book | List of buy and sell orders waiting, sorted by price and arrival |
| Price-time priority | The best price executes first; at the same price, whoever arrived first |
| Partial fill | Only part of the quantity is executed; the rest stays in the book |
| Market order | No price: executes against whatever is there; what is left is cancelled |
| Tick size | Minimum price increment (0.01 here) |
| Price bands | ±10% limit around the reference price |
| T+2 | Settlement two business days after the trade |
| TARGET2 / T2S | European payment system / securities settlement system; their holidays are not business days |
| EOD | End of day: batch processes that settle and produce reports |
| Hold / release | Hold back and release a settlement instruction |
| Kafka topic | A named stream of messages; producers write to it, consumers read at their own pace |
| Idempotency | Processing the same message twice has the same effect as processing it once |
| Dead letter queue (DLQ) | Where messages that cannot be processed go, so they do not block the others |
| Reconciliation | Comparing two systems' records to find missing or different items |
| Smoke test | A quick check of the essentials after a deployment |
| Regression | Re-testing what already worked, after a change |
| Go / no-go | Decision to release (or not) a version |

## Good practices we expect

1. Reproduce before reporting; a defect without steps is not a defect, it is a guess.
2. Ask early: a question in refinement costs minutes, in UAT it costs days.
3. Never test destructively in UAT; never use real data or corporate systems in tests.
4. Leave the environments as you found them.
5. Write for whoever decides: impact first, technical detail afterwards.
