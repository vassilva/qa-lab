# Linux and Shell in the QA Lab

The QA and UAT environments are Linux servers (Debian 12). You get in through the browser terminal
(QA `localhost:7681`, UAT `localhost:7682`) or with `docker exec -it qa-lab-qa-app bash`, as you would with `ssh`.
The user is `qa`, without root privileges, as on a bank server. The three services write their logs to the same
shared folder, `/var/log/qa-lab/`: `qa-lab.log` (Trading), `settlement.log` and `t2s-sim.log`.

## Project scripts (Shell)

| Script | What it does | Shell concepts |
| --- | --- | --- |
| `scripts/smoke.sh` | Post-deployment smoke test | `curl`, `jq`, functions, `case`, `set -euo pipefail` |
| `scripts/deploy.sh` | Deploys a version to QA or UAT | arguments, validation, exported variables, `${VAR^^}`, loops |
| `scripts/wait_healthy.sh` | Waits until the container is healthy | `while` loop, arithmetic `(( ))`, timeouts |
| `scripts/run_tests.sh` | Runs pytest or behave and stores reports | arrays, `case`, exit codes |
| `scripts/analyze_logs.sh` | Log summary by component, rejections, trades, failed settlements, DLQ, errors | `grep`, `sed -E`, `awk`, `sort \| uniq -c`, arrays of files |
| `scripts/eod.sh` | End of day as a batch job, with report validation | exit codes per error type, `wc -l` |
| `scripts/backup_db.sh` | Compressed database backup with rotation | `pg_dump \| gzip`, `${VAR##*/}`, `ls -t \| tail`, `while read` |

## Exercises (in the QA terminal)

Prepare some data first: `python3 scripts/generate_orders.py --n 300`

| # | Question | Answer |
| --- | --- | --- |
| 1 | Where am I, who am I and which version runs here? | `pwd; whoami; echo $ENV_NAME $APP_VERSION` |
| 2 | Which application processes are running, and with which PID? | `ps -ef \| grep -E "app.server\|ttyd" \| grep -v grep` |
| 3 | Which ports is the service listening on? | `ss -tlnp` (8000 = application, 7681 = terminal) |
| 4 | Is the service healthy? Are the other systems? | `curl -s localhost:8000/health \| jq` and `curl -s localhost:8000/api/integration \| jq` |
| 5 | Watch the log live while you send an order on the page | `tail -f /var/log/qa-lab/qa-lab.log` (Ctrl+C to exit) |
| 6 | Follow a trade across the three services (Trading, Settlement, T2S) | `grep -h -e T00001 -e S00001 /var/log/qa-lab/*.log \| sort` |
| 7 | Look at the files exchanged with T2S | `ls -lt /var/lib/qa-lab/files/*/ \| head` · `cat /var/lib/qa-lab/files/inbound/CONF_*.csv` |
| 8 | How many orders were rejected? | `grep -c "REJECTED:" /var/log/qa-lab/qa-lab.log` |
| 9 | Rejections by reason, most frequent first | `grep "\[OEG\].*REJECTED:" /var/log/qa-lab/qa-lab.log \| sed -E 's/.*REJECTED: ([^(]+) \(.*/\1/' \| sort \| uniq -c \| sort -rn` |
| 10 | How many EDP shares were traded? | `grep "\[ME\] Trade" /var/log/qa-lab/qa-lab.log \| awk '$8=="EDP" {s+=$7} END {print s}'` |
| 11 | Which log lines are from today between 10:00 and 11:00? | `grep -h "^$(date +%F) 10:" /var/log/qa-lab/*.log` |
| 12 | Which end-of-day files exist and how much space do they use? | `ls -lh /var/log/qa-lab/eod/` and `du -sh /var/log/qa-lab` |
| 13 | How many instructions did the last end of day settle? | `ls -t /var/log/qa-lab/eod/*.csv \| head -1 \| xargs grep -c SETTLED` |
| 14 | Find files changed in the last 10 minutes | `find /var/log/qa-lab /var/lib/qa-lab -mmin -10 -type f` |
| 15 | Server disk space and memory | `df -h /` and `free -m` |
| 16 | Run the end of day and check the exit code | `bash scripts/eod.sh; echo "exit code: $?"` |
| 17 | Make a backup and confirm it is valid | `bash scripts/backup_db.sh && ls -lh /var/log/qa-lab/backups/` (in the `qa-lab-qa-settlement` container it backs up the `settlement` database) |
| 18 | Archive today's logs to attach to a defect | `tar -czf /tmp/evidence_$(date +%F).tar.gz /var/log/qa-lab/*.log /var/log/qa-lab/eod` |
| 19 | Full log summary | `bash scripts/analyze_logs.sh` |
| 20 | Why can't I write to `/etc`? | `ls -ld /etc` and `id`: the `qa` user is not root (least privilege principle) |
| 21 | Which packages and versions are installed? (e.g. PostgreSQL client, see DEF-011) | `psql --version; python --version; dpkg -l \| grep postgresql-client` |

## Incident scenario to practise

> "UAT stopped responding after the deployment."

1. `docker ps -a --filter name=qa-lab-uat` (on your PC): which containers are running? Healthy? (app, settlement, t2s, kafka, db)
2. `docker logs --tail 50 qa-lab-uat-app`: an error at startup?
3. On the server: `ps -ef | grep app.server`, `ss -tlnp`, `curl -v localhost:8000/health`.
4. `tail -50 /var/log/qa-lab/trading.out` and `grep -h ERROR /var/log/qa-lab/*.log`.
5. Other systems: `curl -s localhost:8000/api/integration | jq` (bus, outbox, Settlement, T2S).
6. Database: `pg_isready -d "$DATABASE_URL"` and `psql "$DATABASE_URL" -c "select 1"`.
7. Resources: `df -h`, `free -m`.
8. Write it down in the bug report: time, command, output, conclusion.
