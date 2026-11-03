# Cobertura de automação e plano de melhoria · QA Lab

## Onde estamos (versão 0.4.0)

| Medida | Valor | Como se mede |
| --- | --- | --- |
| Critérios de aceitação com cenário automatizado | **15 de 15 (100%)** | `scripts/rastreabilidade.py` |
| Riscos de negócio cobertos | **13 de 13** | Matriz de rastreabilidade |
| Cobertura de código (testes de componente e API) | **93%** (era 85%) | pytest-cov, no estágio "Testes de componente e API" |
| Testes automáticos | **63** de componente/API + **27** cenários BDD | Relatórios JUnit no Jenkins |
| Casos manuais automatizados total ou parcialmente | **8 de 10** | `casos-de-teste-manuais.md` |
| Tempo de feedback de um commit | ~2 minutos até QA validado | Duração dos estágios no Jenkins |
| Defeitos de treino detetados pela regressão | **5 de 5** (8 cenários falham em modo desafio) | Pipeline com `MODO_DESAFIO` |

## Melhoria já feita

| Data | Melhoria | Resultado |
| --- | --- | --- |
| 2026-11-03 | 21 testes de API para rotas sem cobertura (`tests/api/test_api_rotas.py`) | Cobertura 85% → 93%; `server.py` 72% → 92% |
| 2026-11-03 | Verificações de integridade em SQL (`db/consultas_qa.sql`) | Detetam DEF-002 e DEF-003 diretamente na base de dados |
| 2026-11-03 | Limpeza do ambiente depois dos testes BDD (DEF-006) | QA fica limpo e com a data do dia |
| 2026-11-03 | Relatório HTML com cobertura de critérios, riscos e defeitos | Decisão go/no-go com informação estruturada |

## Lacunas e próximos passos (por prioridade de risco)

| # | Lacuna | Risco | Ação proposta | Esforço |
| --- | --- | --- | --- | --- |
| 1 | As verificações SQL não correm no pipeline | R-04, R-05 | Estágio "QA · Integridade de dados" que corre `db/consultas_qa.sql` e falha se alguma verificação devolver linhas | Baixo |
| 2 | O conteúdo do CSV do fecho do dia não é verificado automaticamente | R-06 | Cenário BDD que corre `scripts/eod.sh` e valida o ficheiro | Baixo |
| 3 | A página web só é testada manualmente | Baixo | 3 testes de interface com Playwright (TC-M01, TC-M02, TC-M04) | Médio |
| 4 | Testes de volume inexistentes | T-03 | `scripts/gerar_ordens.py --n 5000` no pipeline noturno, com limite de tempo de resposta (p95) | Baixo |
| 5 | Sem testes de mutação | Qualidade dos testes | Usar o modo desafio como "mutantes" conhecidos: a regressão tem de falhar sempre | Já possível, falta automatizar |

Regra de melhoria contínua: cada defeito encontrado fora da automação gera um teste automático novo,
ou uma justificação escrita de porque não vale a pena.
