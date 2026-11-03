# Atualiza o Jenkins e o Adminer sem interromper builds (correcao tecnica do DEF-008).
#
# Uso (PowerShell, na pasta do projeto):
#   powershell -ExecutionPolicy Bypass -File scripts\atualizar_ferramentas.ps1 -SoPausar   # 1. antes de trazer codigo novo
#   powershell -ExecutionPolicy Bypass -File scripts\atualizar_ferramentas.ps1             # 2. depois: pausa (se preciso), reconstroi e reinicia
#
# O Jenkins deixa de arrancar builds novos e espera que os builds em curso terminem.
# So depois as ferramentas sao reconstruidas. Ao reiniciar, o Jenkins volta a aceitar builds sozinho.
param([switch]$SoPausar)

$ErrorActionPreference = "Stop"

docker cp scripts/jenkins_ctl.py qa-lab-jenkins:/tmp/jenkins_ctl.py
docker exec qa-lab-jenkins python3 /tmp/jenkins_ctl.py quiet-down
if ($LASTEXITCODE -ne 0) {
    Write-Host "Atualizacao cancelada: ainda ha builds em curso no Jenkins." -ForegroundColor Yellow
    exit 1
}

if ($SoPausar) {
    Write-Host "Jenkins em pausa. Traz o codigo novo e depois corre este script sem -SoPausar." -ForegroundColor Green
    exit 0
}

docker compose up -d --build
Write-Host "Ferramentas atualizadas. O Jenkins reinicia e volta a aceitar builds." -ForegroundColor Green
