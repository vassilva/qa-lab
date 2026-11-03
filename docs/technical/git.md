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

## Publish on GitHub (optional)

1. Create an empty repository on GitHub (for example, `qa-lab`).
2. `git remote add origin https://github.com/<user>/qa-lab.git`
3. `git push -u origin main --tags` (and any branches you want to show).

The lab Jenkins keeps reading the local repository; connecting it to GitHub is an optional next step.
