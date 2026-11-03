# Matriz de risco · QA Lab

**Risco = probabilidade × impacto**, cada um numa escala de 1 a 3.

| Pontuação | Prioridade | Etiqueta nos cenários | Regra |
| --- | --- | --- | --- |
| 6 – 9 | Crítica | `@critico` | Corre sempre; uma falha bloqueia a release |
| 3 – 4 | Alta | `@alto` | Corre na regressão completa; uma falha bloqueia a release |
| 1 – 2 | Média | `@medio` | Corre na regressão completa; uma falha exige decisão do responsável |

**Impacto:** 3 = perda financeira, erro regulatório ou mercado parado · 2 = operação errada mas corrigível · 1 = incómodo, sem efeito financeiro.
**Probabilidade:** 3 = lógica complexa ou alterada com frequência · 2 = lógica moderada · 1 = lógica simples e estável.

## Riscos de negócio

| ID | Risco | Componente | P | I | Risco | Prioridade | Critérios de aceitação |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | Negócio executado ao preço errado (da ordem que chega em vez da que estava no livro) | Matching Engine | 3 | 3 | 9 | Crítica | AC-N01 |
| R-02 | Ordem com o mesmo preço executa fora da ordem de chegada (prioridade tempo) | Matching Engine | 3 | 3 | 9 | Crítica | AC-N03 |
| R-03 | Data de liquidação errada (fim de semana ou feriado TARGET2 não considerados) | Settlement | 3 | 3 | 9 | Crítica | AC-L01, AC-L02 |
| R-04 | Execução parcial atualiza mal a quantidade por executar | Matching Engine | 2 | 3 | 6 | Crítica | AC-N02 |
| R-05 | Negócio sem instrução de liquidação (falha de reconciliação) | Settlement / BD | 2 | 3 | 6 | Crítica | AC-L05 |
| R-06 | Instrução liquidada antes da data prevista | Settlement | 2 | 3 | 6 | Crítica | AC-L03 |
| R-07 | Ordem com quantidade inválida entra no livro (fronteira de 10 000) | Order Entry Gateway | 2 | 2 | 4 | Alta | AC-V01 |
| R-08 | Ordem fora das bandas de preço ou do tick size entra no livro | Order Entry Gateway | 2 | 2 | 4 | Alta | AC-V02 |
| R-09 | Instrução retida (hold) é liquidada | Settlement | 2 | 2 | 4 | Alta | AC-L04 |
| R-10 | Ordem de mercado sem contraparte fica pendurada no livro | Matching Engine | 1 | 3 | 3 | Alta | AC-N05 |
| R-11 | Ordem que não cruza é executada | Matching Engine | 1 | 3 | 3 | Alta | AC-N04 |
| R-12 | Ordem já executada pode ser cancelada | Order Entry Gateway | 1 | 2 | 2 | Média | AC-V03 |
| R-13 | Data de negócio definida para um dia não útil | Settlement | 1 | 2 | 2 | Média | AC-L06 |

## Riscos técnicos e de entrega

| ID | Risco | P | I | Risco | Mitigação |
| --- | --- | --- | --- | --- | --- |
| T-01 | A versão em UAT não é a testada em QA | 2 | 3 | 6 | O pipeline promove a mesma imagem; smoke em UAT confirma a versão |
| T-02 | Estado perdido após reinício do serviço | 2 | 3 | 6 | Restauro a partir do PostgreSQL; teste `test_restauro_do_estado` |
| T-03 | Ambiente indisponível depois do deploy | 2 | 2 | 4 | Healthcheck do contentor + espera ativa no deploy + smoke test |
| T-04 | Testes destrutivos correm em UAT | 1 | 3 | 3 | O framework BDD recusa correr fora de QA/LOCAL |

## Leitura rápida

Os seis riscos críticos concentram-se em **dois sítios**: o preço e a ordem de execução no Matching Engine,
e a data de liquidação. É aí que está a maior parte do esforço de teste. Se só houver tempo para uma ronda curta,
corre `@critico` (cerca de 1 minuto).
