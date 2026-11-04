# One-time GitHub setup for the pull request workflow (needs the GitHub CLI: gh auth login).
#   - auto-merge allowed and branches deleted after the merge
#   - main protected: no direct push (not even the owner), merge only through a PR with the check green
# Usage (in the qa-lab folder): powershell -ExecutionPolicy Bypass -File scripts\github\setup_repo.ps1
param([string]$Repo = "vassilva/qa-lab")

Write-Host "==> Repository settings: allow auto-merge, delete branch after merge" -ForegroundColor Cyan
gh api -X PATCH "repos/$Repo" -F allow_auto_merge=true -F delete_branch_on_merge=true --silent
if ($LASTEXITCODE -ne 0) { Write-Host "Failed to change the repository settings" -ForegroundColor Red; exit 1 }

Write-Host "==> Protecting main (PR required, check 'Component and API tests' required)" -ForegroundColor Cyan
gh api -X PUT "repos/$Repo/branches/main/protection" --input "$PSScriptRoot\branch-protection.json" --silent
if ($LASTEXITCODE -ne 0) { Write-Host "Failed to protect main" -ForegroundColor Red; exit 1 }

Write-Host "Done. Check: https://github.com/$Repo/settings/branches" -ForegroundColor Green
