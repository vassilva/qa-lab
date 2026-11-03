# Pull request template

```markdown
## What and why
<!-- One or two sentences. Link to the story or the defect: DEF-NNN / AC-XNN -->

## How it was tested
- [ ] Component tests added/updated (`tests/`)
- [ ] BDD scenario covering the acceptance criterion (`features/`), with a priority tag and `@AC-…`
- [ ] For a defect: the new test fails without the fix and passes with it
- [ ] Green pipeline (QA · BDD regression)

## Impact and risk
<!-- Components touched, risk matrix entries affected, contract changes (OpenAPI / event schema), data migration, configuration changes -->

## Reviewer checklist (QA)
- [ ] The acceptance criteria are covered
- [ ] Edge cases considered
- [ ] Useful logs for diagnosis (with the component tag)
- [ ] Documentation and traceability matrix updated
```
