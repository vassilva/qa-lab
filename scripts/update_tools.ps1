# Updates Jenkins and Adminer without interrupting builds (technical fix for DEF-008).
#
# Usage (PowerShell, in the project folder):
#   powershell -ExecutionPolicy Bypass -File scripts\update_tools.ps1 -PauseOnly   # 1. before bringing in new code
#   powershell -ExecutionPolicy Bypass -File scripts\update_tools.ps1              # 2. afterwards: pause (if needed), rebuild and restart
#
# Jenkins stops starting new builds and waits for running builds to finish.
# Only then are the tools rebuilt. After the restart, Jenkins accepts builds again on its own.
param([switch]$PauseOnly)

$ErrorActionPreference = "Stop"

docker cp scripts/jenkins_ctl.py qa-lab-jenkins:/tmp/jenkins_ctl.py
docker exec qa-lab-jenkins python3 /tmp/jenkins_ctl.py quiet-down
if ($LASTEXITCODE -ne 0) {
    Write-Host "Update cancelled: there are still builds running in Jenkins." -ForegroundColor Yellow
    exit 1
}

if ($PauseOnly) {
    Write-Host "Jenkins paused. Bring in the new code, then run this script again without -PauseOnly." -ForegroundColor Green
    exit 0
}

docker compose up -d --build
docker exec qa-lab-jenkins python3 /tmp/jenkins_ctl.py resume 2>$null
Write-Host "Tools updated. Jenkins accepts builds again." -ForegroundColor Green
