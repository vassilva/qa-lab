# Investigação e validação de correções · QA Lab

Como o QA trabalha com developers e colegas de QA desde o defeito até ao fecho.

## Fluxo

| Passo | Quem | O quê | Evidência |
| --- | --- | --- | --- |
| 1. Reproduzir | QA | Reproduzir com o mínimo de passos, num ambiente limpo | Passos no bug report |
| 2. Isolar | QA | Identificar o componente com os logs por etiqueta (`[OEG]`, `[ME]`, `[SETTLEMENT]`), testes de componente e SQL | Secção "Evidências" |
| 3. Analisar com o dev | QA + Dev | Sessão curta (15 min): confirmar a causa, o impacto e o âmbito da correção | Secção "Análise" |
| 4. Corrigir num ramo | Dev | Ramo `fix/DEF-NNN-descricao`, com teste que reproduz o defeito | Pull request |
| 5. Rever | QA + Dev | Revisão do pull request: a correção e o teste novo cobrem o critério de aceitação? | Comentários no PR |
| 6. Reteste | QA | Repetir os passos do bug report na versão corrigida | Estado "Em reteste" → "Fechado" |
| 7. Regressão | Pipeline | Regressão completa em QA para garantir que nada mais partiu | Build verde no Jenkins |

Regra: **um defeito só fecha com evidência de reteste e de regressão**, nunca só porque "o dev disse que está corrigido".

## Casos reais deste projeto

### DEF-006 · Os testes BDD deixavam o ambiente QA sujo
- **Investigação:** no build #3, o Smoke QA mostrou a data de negócio 2026-11-06, mas o UAT mostrou 2026-11-03.
  A diferença apontou para o último cenário BDD (`AC-L06`), que usa 2026-11-06.
- **Análise:** os cenários limpam antes de cada teste, mas ninguém limpava no fim. Risco extra discutido na análise:
  uma limpeza automática nunca pode correr em UAT.
- **Correção:** ramo `fix/DEF-006-bdd-repoe-ambiente`, com um hook `after_all` que reinicia o QA e só corre depois de confirmado
  que o ambiente não é UAT.
- **Reteste:** correr a regressão BDD e depois `curl localhost:8000/api/business-date` → data de hoje; `GET /api/orders` → lista vazia.
- **Regressão:** 27 cenários e 41 testes de componente verdes.

### DEF-007 · Mensagem de falha enganadora no pipeline
- **Correção:** ramo `fix/DEF-007-mensagem-falha-pipeline`.
- **Reteste:** forçar uma falha num estágio UAT (por exemplo, parar o contentor UAT durante o build) e confirmar que a mensagem não
  afirma que a versão não chegou a UAT.

### DEF-001 a DEF-005 · Defeitos do modo desafio
- **Investigação:** o pipeline com `MODO_DESAFIO` falha em "QA · Regressão BDD" e **não passa para UAT** (o gate de qualidade funciona).
  Cada cenário falhado foi reproduzido manualmente pela API e confirmado nos logs e na base de dados.
- **Validação da "correção":** novo build com `MODO_DESAFIO` desligado (equivale à versão corrigida). Os mesmos cenários passam,
  o que prova que os testes detetam o defeito quando existe e passam quando não existe.

## Ver o histórico no Git

```bash
git log --oneline --graph --all          # ramos fix/... e feature/... e os merges
git show --stat <commit>                 # ficheiros alterados numa correção
```
