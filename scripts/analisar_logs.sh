#!/usr/bin/env bash
# Resumo do log da aplicação: atividade por componente, rejeições por motivo, negócios por símbolo,
# erros e liquidações falhadas. Útil para investigar defeitos e para o relatório do dia.
#
# Uso: bash scripts/analisar_logs.sh [ficheiro-de-log] [AAAA-MM-DD]
#      (por omissão: /var/log/qa-lab/qa-lab.log, todas as datas)
set -euo pipefail

LOG="${1:-${QA_LAB_LOG_DIR:-/var/log/qa-lab}/qa-lab.log}"
DAY="${2:-}"

if [[ ! -r "$LOG" ]]; then
  echo "ERRO: não consigo ler o log $LOG" >&2
  exit 1
fi

# Filtra por data, se indicada (as linhas começam por AAAA-MM-DD)
lines() { if [[ -n "$DAY" ]]; then grep "^$DAY" "$LOG" || true; else cat "$LOG"; fi; }

section() { printf '\n== %s\n' "$1"; }

echo "Análise de $LOG${DAY:+ (dia $DAY)} · $(lines | wc -l) linhas"

section "Linhas por componente e nível"
lines | awk '{print $4, $3}' | sort | uniq -c | sort -rn

section "Ordens rejeitadas por motivo"
lines | grep "REJEITADA" | sed -E 's/.*REJEITADA: ([^(]+) \(.*/\1/' | sort | uniq -c | sort -rn || true

section "Negócios por símbolo (quantidade de negócios · ações)"
lines | grep -E "\[ME\] Negócio" | awk '{sym=$8; qty=$7; n[sym]++; q[sym]+=qty} END {for (s in n) printf "%-6s %4d negócios · %8d ações\n", s, n[s], q[s]}' | sort || true

section "Instruções não liquidadas na data prevista"
lines | grep "NÃO liquidada" || echo "nenhuma"

section "Erros"
lines | grep -E " (ERROR|CRITICAL) " || echo "nenhum"
