# Gestão de defeitos · QA Lab

Cada defeito é um ficheiro `DEF-NNN.md` com a mesma estrutura. No fim do projeto (item F1 do checklist)
estes defeitos são registados num Jira pessoal de testes; os ficheiros mantêm-se como cópia offline.

## Ciclo de vida

```
Novo → Em análise → Confirmado → Em correção → Corrigido → Em reteste → Fechado
                 ↘ Rejeitado (não é defeito)      ↘ Reaberto (o reteste falhou)
```

## Severidade e prioridade (avaliadas em separado)

| Severidade (impacto técnico, define o QA) | Exemplo |
| --- | --- |
| **Crítica** | Execução ao preço errado, venda de mais ações do que existiam, liquidação na data errada |
| **Alta** | Regra de negócio importante violada, com contorno possível |
| **Média** | Comportamento errado em casos-limite, sem perda financeira |
| **Baixa** | Mensagens, textos, incómodos operacionais |

| Prioridade (urgência, define o negócio/PO) | Significado |
| --- | --- |
| **P1** | Bloqueia a release: corrigir antes do go |
| **P2** | Corrigir nesta release, se possível |
| **P3** | Pode ficar para uma release seguinte |

## Template

```markdown
# DEF-NNN · Título curto e específico

| Campo | Valor |
| --- | --- |
| Estado | Novo |
| Componente | Order Entry Gateway / Matching Engine / Settlement / Pipeline / Ambiente |
| Severidade | Crítica / Alta / Média / Baixa |
| Prioridade | P1 / P2 / P3 |
| Ambiente | QA / UAT · modo normal ou desafio |
| Versão | 0.x.x-<commit> |
| Critério de aceitação | AC-… |
| Risco | R-… |
| Detetado por | Cenário BDD / caso manual / análise de log / pipeline |
| Data | AAAA-MM-DD |

## Resumo
## Passos para reproduzir
## Resultado esperado
## Resultado obtido
## Evidências (API, log, SQL)
## Análise
```

## Defeitos registados

| ID | Título | Componente | Severidade | Prioridade | Estado |
| --- | --- | --- | --- | --- | --- |
| [DEF-001](DEF-001.md) | Quantidade 10 000 é rejeitada (limite máximo não incluído) | Order Entry Gateway | Média | P2 | Aberto (modo desafio) |
| [DEF-002](DEF-002.md) | Negócio executado ao preço da ordem que chega, em vez do preço do livro | Matching Engine | Crítica | P1 | Aberto (modo desafio) |
| [DEF-003](DEF-003.md) | Execução parcial não reduz a venda no livro: vende mais do que existia | Matching Engine | Crítica | P1 | Aberto (modo desafio) |
| [DEF-004](DEF-004.md) | Prioridade tempo invertida nas compras com o mesmo preço | Matching Engine | Crítica | P1 | Aberto (modo desafio) |
| [DEF-005](DEF-005.md) | Calendário de liquidação ignora os feriados TARGET2 | Settlement | Crítica | P1 | Aberto (modo desafio) |
| [DEF-006](DEF-006.md) | Os testes BDD deixam o ambiente QA com dados e data de teste | Testes (BDD) | Baixa | P2 | Fechado |
| [DEF-007](DEF-007.md) | Mensagem de falha do pipeline diz que a versão não chegou a UAT, mesmo quando chegou | Pipeline | Baixa | P3 | Fechado |
| [DEF-008](DEF-008.md) | Pipeline corre no Jenkins antigo durante a atualização das ferramentas | Ambiente / Pipeline | Média | P2 | Fechado (reaberto no build #4; correção técnica) |
| [DEF-009](DEF-009.md) | Build da imagem falha: pacote ttyd não existe no Debian 12 | Ambiente / Build | Alta | P1 | Fechado |
| [DEF-010](DEF-010.md) | Query de reconciliação falha em PostgreSQL (alias usado no HAVING) | Base de dados | Média | P2 | Fechado |
| [DEF-011](DEF-011.md) | Backup falharia: pg_dump 15 incompatível com o servidor PostgreSQL 16 | Ambiente / Base de dados | Alta | P1 | Fechado |

Os DEF-001 a DEF-005 só existem com o **modo desafio** ligado (Jenkins → Build with Parameters → `MODO_DESAFIO`).
São defeitos de treino: a "versão corrigida" é a mesma imagem com o modo desafio desligado.
Os DEF-006 a DEF-011 são reais, encontrados durante a construção do laboratório.
