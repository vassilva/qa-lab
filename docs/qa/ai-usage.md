# Use of AI tools in QA · QA Lab

This lab was built with help from an AI assistant (Claude). The log below shows **where** AI helped,
**what** I validated and **which rules** I follow. Responsibility for the result is always human.

## Where AI was used

| Activity (job requirement) | Example in this project | How it was validated |
| --- | --- | --- |
| Test design | Boundary value proposals (10,000 / 10,001, bands 4.05 / 4.95) and holiday dates (Christmas, Easter 2027) | Checked against the README rules and the TARGET2 calendar; tests running |
| Test case generation | First version of the Gherkin scenarios from the acceptance criteria | Reviewed one by one; each scenario runs in QA and fails when the defect exists (challenge mode) |
| Defect analysis | Reading long Jenkins logs (e.g. DEF-008, the timestamp comparison that revealed the race condition) | Confirmed with `python3 --version` in the container and with a new build |
| Documentation | Structure of the test strategy, the risk matrix and the bug reports | Reviewed and adjusted to the project's reality |
| Reporting | HTML report generator and traceability matrix | Outputs compared with the real Jenkins results |
| Automation development | behave steps, Shell and Python scripts | Run locally and in the pipeline before any commit |
| Knowledge discovery | Euronext's public architecture (Optiq, Euronext Clearing, T2S) as inspiration | Official sources checked; the project says "inspired by", never "replica" |

## AI mistakes caught by human review

| Situation | What was wrong | How it was caught |
| --- | --- | --- |
| `ttyd` package in the Dockerfile (DEF-009) | Assumed the package existed in Debian 12 | The build failed; the log was read and fixed |
| Query with an alias in HAVING (DEF-010) | Worked on SQLite, failed on PostgreSQL | Validation on the same engine as production |
| Count of acceptance criteria | A draft said 21; there were 15 at the time | Counted with `grep` in the `.feature` files |
| SQL price check (query 7) | The first version did not detect DEF-002 | Query tested with challenge mode data |
| PostgreSQL versions (DEF-011) | Client 15 and server 16 incompatible for backups | Compatibility review before using the script |
| Missing library in the image (DEF-012) | Tests passed on the AI's machine, which had PyYAML installed | The pipeline ran the tests inside the image |
| QA queries after the architecture change (DEF-013) | The SQL file still assumed a single database | Found during review while translating the project |

## Rules I follow

1. **Never put confidential data** (customer data, company data, credentials, proprietary code) into AI tools
   that are not approved. Real example: in this project I refused to use the corporate Jira the tool had access to; the defects
   go to a personal test Jira (item F1).
2. **Everything AI produces is a draft:** it only enters the project after it has been run and reviewed.
3. **Validate in the real environment:** what passes in a simplified environment can fail in the real one (DEF-010, DEF-011, DEF-012).
4. **Traceability:** important decisions are written down (bug reports, reports), not only in the conversation with the AI.
5. **Business knowledge is mine:** AI speeds things up, but market rules and risks are validated by someone who knows them.

## v0.5.0 · Integration architecture

- AI helped design the integration patterns (outbox, idempotency, DLQ, recycling) and the failure scenarios.
- An acknowledged limit: Kafka could not run in the environment where the AI worked. The code was validated locally with
  an equivalent bus (file/memory) and the real Kafka connector is validated by the pipeline, in the QA environment (build #7: 33/33 with real Kafka).
  This was written down in the risk matrix (T-06) instead of being hidden.

## v0.6.0 · English translation

- AI translated the code, tests, pipeline and documentation. The translation was checked by running the full test suite
  (86 pytest + 33 BDD scenarios) and by scanning the repository for leftover Portuguese text.
