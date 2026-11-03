# Estratégia de testes · QA Lab (mini bolsa)

| | |
| --- | --- |
| Sistema | QA Lab: Order Entry Gateway, Matching Engine, Market Data, Settlement T+2 |
| Versão do documento | 1.0 · 2026-11-03 |
| Responsável | Vicente (QA) |
| Requisitos cobertos | Regras de negociação e de liquidação descritas no `README.md` |

## 1. Objetivos

| ID | Objetivo | Como se mede |
| --- | --- | --- |
| OBJ-1 | Garantir que nenhuma ordem inválida chega ao livro de ordens | 100% das regras de validação do gateway cobertas por testes automáticos, incluindo valores-fronteira |
| OBJ-2 | Garantir execuções corretas e justas (prioridade preço-tempo, preço do negócio, execuções parciais) | Todos os critérios de aceitação de negociação passam em QA |
| OBJ-3 | Garantir que cada negócio é liquidado na data certa (T+2, calendário TARGET2) | Todos os critérios de aceitação de liquidação passam; reconciliação negócios ↔ instruções sem diferenças |
| OBJ-4 | Garantir que a versão aprovada em QA é a mesma que vai para UAT | O pipeline promove a mesma imagem; smoke em UAT confirma a versão |
| OBJ-5 | Dar informação clara para a decisão go/no-go | Relatório de testes e checklist de release preenchidos em cada versão |

## 2. Âmbito

**Dentro do âmbito**
- Validação de ordens no Order Entry Gateway (quantidade, preço, tick size, bandas, símbolo, lado).
- Cruzamento de ordens no Matching Engine (preço-tempo, preço do negócio, parciais, ordens de mercado, cancelamentos).
- Market Data: livro de ordens e lista de negócios publicados pela API.
- Settlement: criação de instruções, cálculo da data T+2, hold/release, fecho do dia (EOD), relatório CSV.
- Integridade dos dados em PostgreSQL (reconciliação negócios ↔ instruções, quantidades executadas).
- API REST (códigos de resposta, mensagens de erro).
- Implantação e saúde dos ambientes (smoke tests pós-deploy).

**Fora do âmbito (nesta versão)**
- Testes de desempenho e latência (um motor real mede microssegundos; aqui não é representativo).
- Segurança (autenticação, autorização) e protocolos de mercado (FIX, SBE).
- Clearing (margens, risco de contraparte) e dinheiro/títulos reais.
- Compatibilidade entre browsers da página web (é uma ferramenta de apoio).

## 3. Abordagem: testes standalone por componente, depois de ponta a ponta

Cada componente é primeiro testado **isolado** (standalone), com dados controlados e sem dependências externas.
Só depois se testa o fluxo completo num ambiente real.

| Nível | O que testa | Como fica isolado | Ferramenta | Onde corre |
| --- | --- | --- | --- | --- |
| Componente: Gateway | Regras de validação, valores-fronteira | Matching Engine real em memória, sem base de dados nem rede | pytest (`tests/unit/test_trading.py`) | Pipeline, antes do deploy |
| Componente: Matching Engine | Preço-tempo, parciais, ordens de mercado, restauro do estado | Sem base de dados; data de negócio fixa | pytest | Pipeline, antes do deploy |
| Componente: Settlement (calendário) | T+2, fins de semana, feriados TARGET2, Páscoa | Funções puras, datas fixas | pytest (`tests/unit/test_settlement_calendar.py`) | Pipeline, antes do deploy |
| Integração: API + base de dados | Fluxos pela API, persistência, reconciliação | SQLite temporário, cliente de teste em processo | pytest (`tests/api/`) | Pipeline, antes do deploy |
| Sistema: ambiente QA | Critérios de aceitação de negócio, de ponta a ponta | Ambiente QA dedicado, reiniciado antes de cada cenário | behave / BDD (`features/`) | Pipeline, depois do deploy em QA |
| Aceitação: ambiente UAT | Versão certa, serviço saudável, fluxo essencial | Sem testes destrutivos (o UAT está protegido) | smoke test + validação manual | Pipeline, depois do deploy em UAT |

Os testes standalone dão diagnóstico rápido: quando um cenário BDD falha, os testes de componente dizem logo se o problema
está no gateway, no motor ou na liquidação.

**Testes manuais e exploratórios** complementam a automação: sessões exploratórias curtas (30–45 min) por funcionalidade
nova, sobretudo na página web e em combinações de ordens pouco habituais.

## 4. Priorização por risco

Os cenários são priorizados pela matriz de risco (`docs/qa/matriz-de-risco.md`): risco = probabilidade × impacto.
Cada cenário BDD tem uma etiqueta de prioridade, usada para escolher o que correr quando o tempo é curto:

| Etiqueta | Quando corre | Exemplos |
| --- | --- | --- |
| `@critico` | Sempre, em todas as versões | Preço do negócio, prioridade preço-tempo, data T+2 |
| `@alto` | Sempre na regressão completa | Rejeições por preço e quantidade, hold/release |
| `@medio` | Regressão completa | Cancelamento de ordem executada, data de negócio inválida |

Exemplo, só os críticos: `BDD_TAGS=@critico bash scripts/run_tests.sh bdd`

## 5. Ambientes e dados de teste

| Ambiente | Uso | Dados |
| --- | --- | --- |
| Pipeline (contentor temporário) | Testes de componente e de API | SQLite temporário, apagado no fim |
| QA (`localhost:8000`) | Regressão BDD completa | Reiniciado antes de cada cenário (`POST /api/reset`); data de negócio fixada por cenário |
| UAT (`localhost:9000`) | Aceitação da release | Dados mantidos; testes destrutivos **bloqueados** pelo próprio framework |

Datas de teste fixas (ex.: segunda-feira 2026-11-02, sexta-feira 2026-11-06) tornam os testes de liquidação
reproduzíveis, qualquer que seja o dia em que correm.

## 6. Critérios de entrada e saída

**Entrada (podemos começar a testar uma versão em QA)**
- O build da imagem terminou e os testes de componente e de API passaram (100%).
- O deploy em QA terminou e o smoke test passou.

**Saída de QA (a versão pode ir para UAT)**
- 100% dos cenários `@critico` e `@alto` passam.
- Nenhum defeito aberto de severidade crítica ou alta.
- Cenários `@medio` que falhem têm defeito registado e decisão do responsável.

**Saída de UAT (go/no-go)**
- Smoke test em UAT passou e confirma a mesma versão testada em QA.
- Checklist de release (`docs/qa/checklist-release.md`) preenchido.
- Aprovação registada no Jenkins (estágio "Aprovação go/no-go").

## 7. Defeitos e reporting

- Cada defeito é registado com passos para reproduzir, resultado esperado vs. obtido, versão, ambiente e evidências
  (log com a etiqueta do componente, IDs de ordem/negócio/instrução, query SQL).
- Severidade (impacto técnico) e prioridade (urgência de negócio) são avaliadas em separado.
- Os resultados de cada execução ficam no Jenkins (relatório JUnit e artefactos arquivados).

## 8. Riscos do próprio processo de teste

| Risco | Mitigação |
| --- | --- |
| Testes dependentes da data do dia | Data de negócio fixada em cada cenário |
| Testes que interferem uns com os outros | Ambiente QA reiniciado antes de cada cenário; pipeline sem execuções em paralelo |
| Testes destrutivos correrem em UAT por engano | O framework BDD recusa correr num ambiente que não seja QA ou LOCAL |
| Ambiente instável (falso negativo) | Smoke test antes da regressão; deploy só termina com o serviço saudável |

## 9. Ferramentas

pytest · behave (BDD, Gherkin em português) · Jenkins · Docker · PostgreSQL · Git · scripts Bash · Python (requests).
Ferramentas de IA apoiam o desenho de cenários e a documentação, sempre com revisão humana.
