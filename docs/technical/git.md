# Git in the QA Lab

## Workflow

| Branch | Purpose | Example |
| --- | --- | --- |
| `main` | Always stable; every commit triggers the Jenkins pipeline | |
| `feature/<description>` | A new feature or documentation | `feature/arquitetura-integracao`, `feature/english` |
| `fix/DEF-NNN-<description>` | A defect fix, with the ID in the name | `fix/DEF-006-bdd-repoe-ambiente`, `fix/DEF-012` |

Branches are merged into `main` **without fast-forward** (`git merge --no-ff`), so the history shows
which work came from each branch. In a GitHub repository this is a **pull request** with a review
(see `docs/process/pull-request-template.md`).

**Commit messages:** a short first line in the imperative ("Fix…", "Add…"), with the defect ID
when there is one; the body explains why. (Commits before v0.6.0 are in Portuguese: Git history is not rewritten.)

## Look at this project's history

```bash
git log --oneline --graph --all     # branches and merges
git log --grep=DEF-006              # everything that touched a defect
git show --stat HEAD~1              # files changed in a commit
git blame features/environment.py   # who changed each line and in which commit
```

## Exercises (in VS Code, terminal in the project folder)

| # | Task | Commands |
| --- | --- | --- |
| 1 | Set your name and email (once) | `git config --global user.name "…"` · `git config --global user.email "…"` |
| 2 | Look at the status and the history | `git status` · `git log --oneline --graph` |
| 3 | Create a branch for a new scenario | `git switch -c feature/galp-order-scenario` |
| 4 | Add a BDD scenario, look at the diff and commit | `git diff` · `git add features/` · `git commit -m "Add scenario …"` |
| 5 | Go back to `main` and merge the branch | `git switch main` · `git merge --no-ff feature/galp-order-scenario` |
| 6 | Watch Jenkins trigger on its own (up to 2 minutes) | `localhost:8090` → "Started by an SCM change" |
| 7 | Cause a conflict: change the same line on two branches and merge | Resolve in VS Code, `git add`, `git commit` |
| 8 | Undo a commit that is already shared, without rewriting history | `git revert <commit>` |
| 9 | Park unfinished work to switch tasks | `git stash` · `git stash pop` |
| 10 | Tag the version approved in UAT | `git tag -a v0.6.0 -m "Approved in UAT"` · `git tag` |

**merge vs. rebase:** `merge` keeps the history as it happened (with a merge commit); `rebase` replays
the branch's commits on top of `main`, making it linear. Rule: never rebase commits that are already shared.

## GitHub workflow · pull requests

Repository: https://github.com/vassilva/qa-lab. **`main` is protected**: nobody pushes to it directly, not even the
owner. Every change arrives through a **pull request**.

| # | Step | Command |
| --- | --- | --- |
| 1 | Start from an up-to-date `main` | `git switch main` · `git pull` |
| 2 | Create a branch | `git switch -c fix/DEF-018-short-name` (or `feature/...`, `docs/...`) |
| 3 | Commit | `git add -A` · `git commit -m "fix(DEF-018): ..."` |
| 4 | Push the branch → **GitHub Actions build check** (~1 min) | `git push -u origin fix/DEF-018-short-name` |
| 5 | Open the pull request (template `.github/pull_request_template.md`) | `gh pr create --base main --fill` |
| 6 | Turn on auto-merge: GitHub merges as soon as the check is green | `gh pr merge --auto --merge` |
| 7 | Jenkins sees the merge (polls GitHub) → QA → **your approval** → UAT | http://localhost:8090 |
| 8 | Bring `main` back locally | `git switch main` · `git pull` |

```
push ─► GitHub Actions (build + 102 tests) ─► PR (no extra tests) ─► auto-merge
      ─► Jenkins: QA deploy → smoke → BDD regression → ⏸ approval → UAT deploy → smoke (✕ = rollback)
```

| Gate | Where | If it fails |
| --- | --- | --- |
| Build check (component + API tests) | GitHub Actions, on push | The PR cannot be merged |
| QA smoke + BDD regression | Jenkins, after the merge | The pipeline stops, the version never reaches UAT |
| QA approval "Deploy to UAT?" | Jenkins, `input` | No answer in 1 day or Abort = no UAT deploy |
| UAT smoke | Jenkins | Pipeline stops and UAT is rolled back to the previous version |

One-time setup (GitHub CLI): `powershell -ExecutionPolicy Bypass -File scripts\github\setup_repo.ps1`
(allows auto-merge, deletes merged branches, protects `main` with `scripts/github/branch-protection.json`).
A direct `git push` to `main` is then refused with `GH006: Protected branch update failed`.

**In a team** the protection would also require 1 approving review (`required_approving_review_count: 1`);
in this solo lab it is 0, because GitHub does not let the author approve their own pull request.

**Rollback and the database:** the rollback redeploys the previous image on the current database, so migrations
must stay backward compatible (add or relax, never remove in the same release: "expand and contract").
