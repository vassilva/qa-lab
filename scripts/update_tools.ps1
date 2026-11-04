# Updates Jenkins and Adminer without interrupting builds (technical fix for DEF-008, corrected by DEF-014).
#
# Usage (PowerShell, in the project folder):
#   powershell -ExecutionPolicy Bypass -File scripts\update_tools.ps1 -PauseOnly   # 1. before bringing in new code
#   powershell -ExecutionPolicy Bypass -File scripts\update_tools.ps1              # 2. afterwards: rebuild, restart, resume
#   powershell -ExecutionPolicy Bypass -File scripts\update_tools.ps1 -ResumeOnly  # only re-enable the pipeline
#
# The pipeline job is disabled (no new builds) and the script waits for running builds to finish.
# Only then are the tools rebuilt. At the end the job is enabled again and picks up the new commit.
param([switch]$PauseOnly, [switch]$ResumeOnly)

$ErrorActionPreference = "Continue"   # docker writes progress to stderr; exit codes are checked explicitly

function Invoke-JenkinsCtl([string]$Action) {
    docker cp scripts/jenkins_ctl.py qa-lab-jenkins:/tmp/jenkins_ctl.py | Out-Null
    docker exec qa-lab-jenkins python3 /tmp/jenkins_ctl.py $Action | ForEach-Object { Write-Host $_ }
    return [int]$LASTEXITCODE
}

if (-not $ResumeOnly) {
    if ((Invoke-JenkinsCtl "pause") -ne 0) {
        Write-Host "Update cancelled: there are still builds running in Jenkins." -ForegroundColor Yellow
        exit 1
    }
    if ($PauseOnly) {
        Write-Host "Pipeline paused. Bring in the new code, then run this script again without -PauseOnly." -ForegroundColor Green
        exit 0
    }
    docker compose up -d --build
}

# Jenkins may be restarting: retry for up to 3 minutes
$restarted = $false
for ($i = 1; $i -le 36; $i++) {
    $code = Invoke-JenkinsCtl "resume"
    if ($code -eq 0) {
        Write-Host "Tools updated. The pipeline accepts builds again." -ForegroundColor Green
        exit 0
    }
    if ($code -eq 3 -and -not $restarted) {
        # DEF-018: a job created by configuration as code on the first start is not loaded until a restart
        Write-Host "Restarting Jenkins once so it loads the pipeline job (DEF-018)..." -ForegroundColor Yellow
        docker restart qa-lab-jenkins | Out-Null
        $restarted = $true
    }
    Start-Sleep -Seconds 5
}
Write-Host "Jenkins did not answer. When it is up, run: scripts\update_tools.ps1 -ResumeOnly" -ForegroundColor Yellow
exit 1
