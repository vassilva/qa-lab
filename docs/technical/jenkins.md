# Jenkins in the QA Lab

The lab Jenkins runs at `localhost:8090` (admin / admin) and is defined **as code**:

| File | What it defines |
| --- | --- |
| `jenkins/Dockerfile` | Image: Jenkins LTS + Docker client + Python |
| `jenkins/plugins.txt` | Plugins (Pipeline, Git, JUnit, Configuration as Code, Job DSL, Timestamper, Dark Theme) |
| `jenkins/casc.yaml` | User, security, dark theme and the `qa-lab-pipeline` job (polls Git every 2 minutes) |
| `Jenkinsfile` | The pipeline, versioned with the code |

Deleting Jenkins and creating it again gives exactly the same result, with no manual clicks.
To update it safely (without killing a running build): `scripts\update_tools.ps1` (see DEF-008 and DEF-014).

## Pipeline

```
Prepare → Build image → Component and API tests
  → QA · Deploy → QA · Smoke → QA · BDD regression
  → UAT · Deploy → UAT · Smoke → UAT · Test summary → UAT · Go/No-go
```

| Concept | Where it is in the Jenkinsfile |
| --- | --- |
| Quality gate | Any failure in "QA · …" stops the pipeline: the version does not reach UAT |
| Artifact promotion | The image `qa-lab:<version>-<commit>` is built once and promoted |
| Parameters | `REGRESSION` (full/critical) and `CHALLENGE_MODE` (hidden defects in QA) |
| Triggers | Commit (pollSCM every 2 min), manual, and `cron('H 2 * * 1-5')`: nightly regression in QA |
| Conditional execution | `when { not { triggeredBy 'TimerTrigger' } }`: the nightly regression does not go to UAT |
| Manual approval | `input` stage "UAT · Go/No-go", with a 1-day timeout |
| Reports | `junit` (Tests tab and trend), `archiveArtifacts` (HTML report, coverage) |
| Post actions | `post { always / success / failure }` |
| No parallel runs | `disableConcurrentBuilds()`: two deployments never overlap |

## Exercises

1. **Build with Parameters** → `critical`: compare the regression stage time with the full regression.
2. **Build with Parameters** → `CHALLENGE_MODE`: the pipeline should stop at "QA · BDD regression". Open the **Tests** tab and find the 8 failed scenarios.
3. On a green build, download the artifact `reports/qa/index.html` and open the report.
4. **Restart from Stage**: on a build that failed because of infrastructure, repeat only from the stage that failed.
5. **Replay**: change the final `echo` in the browser and run it, without committing. What is it for, and why does it not replace a commit?
6. Commit a BDD scenario that fails on purpose and watch: it fails in QA, nothing reaches UAT. Then `git revert`.
7. Explain the difference between `pollSCM` and a webhook (GitHub notifies Jenkins) and why polling is used here.

Note: after renaming the parameters in v0.6.0, the first build after the update uses the defaults; from then on,
**Build with Parameters** shows `REGRESSION` and `CHALLENGE_MODE`.
