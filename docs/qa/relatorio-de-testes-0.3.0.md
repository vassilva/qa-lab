# Relatório de testes · versão 0.3.0-c200193

| | |
| --- | --- |
| Período | 2026-11-03 |
| Ambientes | QA (`localhost:8000`) e UAT (`localhost:9000`), PostgreSQL 16 (passa a 15 na versão 0.4.0, ver DEF-011) |
| Builds Jenkins | #2 (falha de infraestrutura) e #3 (aprovado) |
| Responsável | Vicente (QA) |

## 1. Resumo para decisão

**Recomendação: GO**, dado na aprovação do build #3 às 12:31.
Todos os testes automáticos passaram, a mesma versão foi confirmada em UAT e não há defeitos abertos que afetem esta versão.
A única falha do período (build #2) foi de infraestrutura, não do produto (DEF-008).

## 2. Progresso

| Atividade | Planeado | Executado | Passou | Falhou |
| --- | ---: | ---: | ---: | ---: |
| Testes de componente e API (pytest) | 41 | 41 | 41 | 0 |
| Cenários BDD em QA (behave, PostgreSQL) | 27 | 27 | 27 | 0 |
| Smoke QA e UAT | 2 | 2 | 2 | 0 |
| Casos manuais (`casos-de-teste-manuais.md`) | 10 | a registar | | |

## 3. Cobertura

- **Critérios de aceitação:** 15 de 15 com cenário automatizado e verdes (100%).
- **Riscos de negócio:** 13 de 13 cobertos; os 6 riscos críticos têm cenários `@critico` que correm em todas as versões.
- **Componentes:** Order Entry Gateway, Matching Engine e Settlement com testes standalone e de ponta a ponta.
- **Fora do âmbito:** desempenho, segurança, protocolos FIX/SBE, clearing (ver a estratégia de testes).

## 4. Defeitos

| Estado | Quantidade | Detalhe |
| --- | ---: | --- |
| Encontrados no período | 5 reais | DEF-006 a DEF-010 |
| Fechados | 5 | Correções validadas com reteste e regressão |
| Abertos que afetam a versão | 0 | |
| Defeitos de treino (modo desafio) | 5 | DEF-001 a DEF-005; não existem com o modo desafio desligado |

Com o modo desafio ligado, a regressão falha em 8 cenários, 7 critérios de aceitação e 6 riscos críticos ou altos,
e a versão **não passa para UAT**. Isto confirma que o gate de qualidade do pipeline funciona.

## 5. Riscos e observações

| Observação | Impacto | Ação |
| --- | --- | --- |
| Os testes BDD deixavam o QA com dados de teste (DEF-006) | Confusão para quem usa o QA a seguir | Corrigido: limpeza no fim dos testes |
| Atualizar as ferramentas enquanto o Jenkins verifica commits causa falsas falhas (DEF-008) | Builds vermelhos sem defeito no produto | Processo: atualizar ferramentas antes dos commits |
| Casos manuais ainda sem registo de execução | Cobertura da página web não evidenciada | Executar TC-M01 a TC-M10 na próxima versão |

## 6. Evidências

Jenkins (`localhost:8090`): builds #2 e #3, separador **Tests** e artefactos arquivados. Relatório HTML do QA em
`localhost:8000/reports/`. Rastreabilidade em [matriz-de-rastreabilidade.md](matriz-de-rastreabilidade.md).
