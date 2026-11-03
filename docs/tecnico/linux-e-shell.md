# Linux e Shell no QA Lab

Os ambientes QA e UAT são servidores Linux (Debian 12). Entra-se pelo terminal no browser
(QA `localhost:7681`, UAT `localhost:7682`) ou com `docker exec -it qa-lab-qa-app bash`, como num `ssh`.
O utilizador é `qa`, sem privilégios de root, como num servidor de banco.

## Scripts do projeto (Shell)

| Script | Faz | Conceitos de Shell |
| --- | --- | --- |
| `scripts/smoke.sh` | Smoke test pós-deploy | `curl`, `jq`, funções, `case`, `set -euo pipefail` |
| `scripts/deploy.sh` | Deploy de uma versão em QA ou UAT | argumentos, validação, variáveis exportadas, `${VAR^^}` |
| `scripts/wait_healthy.sh` | Espera até o contentor estar saudável | ciclo `while`, aritmética `(( ))`, timeouts |
| `scripts/run_tests.sh` | Corre pytest ou behave e guarda relatórios | arrays, `case`, códigos de saída |
| `scripts/analisar_logs.sh` | Resumo do log por componente, rejeições, negócios, erros | `grep`, `sed -E`, `awk`, `sort \| uniq -c` |
| `scripts/eod.sh` | Fecho do dia como job batch, com validação do relatório | códigos de saída por tipo de erro, `wc -l` |
| `scripts/backup_db.sh` | Backup comprimido da base de dados com rotação | `pg_dump \| gzip`, `ls -t \| tail`, `while read` |

## Exercícios (no terminal de QA)

Prepara dados primeiro: `python3 scripts/gerar_ordens.py --n 300`

| # | Pergunta | Resposta |
| --- | --- | --- |
| 1 | Onde estou, quem sou e que versão corre aqui? | `pwd; whoami; echo $ENV_NAME $APP_VERSION` |
| 2 | Que processos da aplicação estão a correr e com que PID? | `ps -ef \| grep -E "app.server\|ttyd" \| grep -v grep` |
| 3 | Em que portas está o serviço à escuta? | `ss -tlnp` (8000 = aplicação, 7681 = terminal) |
| 4 | O serviço está saudável? | `curl -s localhost:8000/health \| jq` |
| 5 | Ver o log em tempo real enquanto envias uma ordem na página | `tail -f /var/log/qa-lab/qa-lab.log` (Ctrl+C para sair) |
| 5b | Seguir um negócio pelos três serviços (Trading, Settlement, T2S) | `grep -h T00001 /var/log/qa-lab/*.log \| sort` |
| 5c | Ver os ficheiros trocados com o T2S | `ls -lt /var/lib/qa-lab/files/ \| head` · `cat /var/lib/qa-lab/files/CONF_*.csv` |
| 6 | Quantas ordens foram rejeitadas? | `grep -c REJEITADA /var/log/qa-lab/qa-lab.log` |
| 7 | Rejeições por motivo, da mais frequente para a menos | `grep REJEITADA /var/log/qa-lab/qa-lab.log \| sed -E 's/.*REJEITADA: ([^(]+) \(.*/\1/' \| sort \| uniq -c \| sort -rn` |
| 8 | Seguir uma ordem por todos os componentes | `grep -w O00010 /var/log/qa-lab/qa-lab.log` |
| 9 | Quantas ações de EDP foram negociadas? | `grep "\[ME\] Negócio" /var/log/qa-lab/qa-lab.log \| awk '$8=="EDP" {s+=$7} END {print s}'` |
| 10 | Que linhas do log são de hoje entre as 10h e as 11h? | `grep "^$(date +%F) 10:" /var/log/qa-lab/qa-lab.log` |
| 11 | Que ficheiros de fecho do dia existem e quanto ocupam? | `ls -lh /var/log/qa-lab/eod/` e `du -sh /var/log/qa-lab` |
| 12 | Quantas instruções liquidou o último fecho do dia? | `ls -t /var/log/qa-lab/eod/*.csv \| head -1 \| xargs grep -c SETTLED` |
| 13 | Encontrar ficheiros alterados nos últimos 10 minutos | `find /var/log/qa-lab -mmin -10 -type f` |
| 14 | Espaço em disco e memória do servidor | `df -h /` e `free -m` |
| 15 | Correr o fecho do dia e ver o código de saída | `bash scripts/eod.sh; echo "código: $?"` |
| 16 | Fazer um backup e confirmar que é válido | `bash scripts/backup_db.sh && ls -lh /var/log/qa-lab/backups/` (no contentor `qa-lab-qa-settlement` faz o backup da base `settlement`) |
| 17 | Arquivar os logs de hoje para anexar a um defeito | `tar -czf /tmp/evidencias_$(date +%F).tar.gz /var/log/qa-lab/qa-lab.log /var/log/qa-lab/eod` |
| 18 | Resumo completo do log | `bash scripts/analisar_logs.sh` |
| 19 | Porque é que não consigo escrever em `/etc`? | `ls -ld /etc` e `id`: o utilizador `qa` não é root (princípio do menor privilégio) |
| 20 | Que pacotes e versões estão instalados? (ex.: cliente PostgreSQL, ver DEF-011) | `psql --version; python --version; dpkg -l \| grep postgresql-client` |

## Cenário de incidente para treinar

> "O UAT deixou de responder depois do deploy."

1. `docker ps -a --filter name=qa-lab-uat` (no teu PC): o contentor está a correr? Saudável?
2. `docker logs --tail 50 qa-lab-uat-app`: erro no arranque?
3. No servidor: `ps -ef | grep app.server`, `ss -tlnp`, `curl -v localhost:8000/health`.
4. `tail -50 /var/log/qa-lab/server.log` e `grep ERROR /var/log/qa-lab/qa-lab.log`.
5. Base de dados: `pg_isready -d "$DATABASE_URL"` e `psql "$DATABASE_URL" -c "select 1"`.
6. Recursos: `df -h`, `free -m`.
7. Registar no bug report: hora, comando, saída, conclusão.
