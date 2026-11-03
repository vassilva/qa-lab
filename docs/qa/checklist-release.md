# Checklist de validação de release (go/no-go)

Preencher para cada versão antes de aprovar o estágio **"Aprovação go/no-go"** no Jenkins.

| Campo | Valor |
| --- | --- |
| Versão | `0.x.x-<commit>` (ver o nome do build no Jenkins) |
| Data | |
| Responsável QA | |

## 1. Qualidade da versão (QA)

- [ ] Testes de componente e API: 100% passados (estágio "Testes de componente e API")
- [ ] Smoke QA passou
- [ ] Regressão BDD em QA: 100% dos cenários `@critico` e `@alto` passados
- [ ] Cenários `@medio` falhados (se existirem) têm defeito registado e decisão tomada
- [ ] Sem defeitos abertos de severidade crítica ou alta
- [ ] "Resumo de testes" no Jenkins com recomendação **GO**

## 2. Implantação (UAT)

- [ ] O selo da página UAT (`localhost:9000`) mostra **a mesma versão** que foi testada em QA
- [ ] Smoke UAT passou (serviço UP, ligado ao PostgreSQL, ordem aceite, settlement disponível)
- [ ] `/health` em UAT responde `"status": "UP"` e `"challenge_mode": false`

## 3. Validação funcional em UAT (manual, 5–10 minutos)

- [ ] Enviar uma venda e uma compra que cruzam: o negócio aparece ao preço da ordem que estava no livro
- [ ] O negócio gera uma instrução de liquidação com a data T+2 correta
- [ ] Uma ordem inválida (ex.: quantidade 10 001) é rejeitada com motivo claro
- [ ] O fecho do dia (EOD) corre e o relatório CSV aparece em `/var/log/qa-lab/eod/` (terminal UAT, `localhost:7682`)
- [ ] O log não tem erros inesperados: `grep -c ERROR /var/log/qa-lab/qa-lab.log`

## 4. Decisão

| Decisão | Critério |
| --- | --- |
| **GO** | Todos os pontos das secções 1 a 3 confirmados |
| **GO com riscos aceites** | Só falham pontos `@medio` / menores, com defeito registado e aceitação do responsável |
| **NO-GO** | Qualquer falha `@critico` ou `@alto`, versão diferente em UAT, ou serviço instável |

Decisão: ______  Justificação: ____________________________________________
