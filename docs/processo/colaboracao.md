# Colaboração com a equipa · QA Lab

## Com quem e como

| Com | Quando | Como o QA contribui | Artefacto |
| --- | --- | --- | --- |
| Business analysts | Refinamento, UAT | Transformar regras em exemplos concretos; perguntar pelos casos-limite | Critérios de aceitação em Gherkin |
| Developers | Desenvolvimento, defeitos | Bug reports reproduzíveis; análise conjunta da causa; revisão de PRs | Bug reports, comentários no PR |
| Colegas de QA | Sempre | Revisão de cenários, pair testing, partilha de passos BDD reutilizáveis | Pull requests de testes |
| Team lead / PM | Planeamento, release | Riscos e cobertura em linguagem de negócio; recomendação go/no-go | Relatório de testes, matriz de risco |
| Operações | Deploy, incidentes | Smoke tests, logs com etiquetas de componente, scripts de diagnóstico | `smoke.sh`, `analisar_logs.sh` |

## Exemplo: sessão *three amigos* da liquidação T+2

**Participantes:** BA (pós-negociação), developer (settlement), QA. **Duração:** 30 minutos.

| Pergunta do QA | Resposta / decisão | Resultado |
| --- | --- | --- |
| T+2 conta dias de calendário ou dias úteis? | Dias úteis TARGET2 | AC-L01, AC-L02 |
| Que feriados? Os portugueses também? | Só os de fecho TARGET2 (o 10 de junho não conta) | Teste `test_dia_util` com 10 de junho |
| Um negócio na véspera de Natal liquida quando? | 28/12 (25 e 26 feriado, 27 domingo) | Exemplo no esquema BDD |
| O que acontece a uma instrução retida na data prevista? | Fica por liquidar e aparece no relatório do EOD | AC-L04, alerta no log |
| Pode haver duas instruções para o mesmo negócio? | Nunca | Restrição UNIQUE na base de dados + AC-L05 |
| A data de negócio pode ser um sábado? | Não | AC-L06 |

Valor da sessão: 6 regras ambíguas tornaram-se exemplos testáveis **antes** de existir código.

## Comunicar um defeito crítico (exemplo de mensagem)

> **DEF-003 (crítico, P1):** em execuções parciais, a venda não é reduzida no livro e pode executar mais do que a
> quantidade da ordem (100 → 140 no teste). Impacto: venda a descoberto e falhas de liquidação. Reproduzível em QA em
> modo desafio, passos e evidências no bug report. Recomendação: **no-go** até à correção. Disponível para analisar com o
> developer às 14h.

Características: impacto em linguagem de negócio primeiro, depois a evidência, a recomendação e o próximo passo.

## Templates

- Bug report: `docs/defeitos/README.md`
- Pull request: `docs/processo/template-pull-request.md` (também em `.github/pull_request_template.md`)
