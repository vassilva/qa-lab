# Processo de QA · da história à release

## Fluxo de uma funcionalidade

| Fase | O que o QA faz | Saída | Critério para avançar |
| --- | --- | --- | --- |
| 1. Refinamento | Sessão *three amigos* (BA + dev + QA): perguntas, exemplos, riscos | Critérios de aceitação em Gherkin | Definition of Ready cumprida |
| 2. Planeamento de testes | Classificar o risco, decidir níveis (componente, BDD, manual), dados de teste | Cenários etiquetados (`@critico`…) e casos manuais | Cenários revistos pelo BA |
| 3. Desenvolvimento | Automatizar cenários em paralelo com o dev; rever o PR do ponto de vista dos testes | Passos BDD e testes de componente | Pipeline verde no ramo |
| 4. Validação em QA | Regressão automática + testes manuais/exploratórios da funcionalidade | Defeitos registados, relatório | Critérios de saída de QA (estratégia, §6) |
| 5. Aceitação em UAT | Smoke, checklist de release, validação com o negócio | Checklist preenchido | Decisão go/no-go registada no Jenkins |
| 6. Depois da release | Rever defeitos escapados, atualizar regressão, retrospetiva | Ações de melhoria | — |

## Definition of Ready (uma história pode entrar no sprint)

- [ ] Objetivo de negócio claro e valor conhecido
- [ ] Critérios de aceitação escritos, testáveis e com exemplos (incluindo casos-limite)
- [ ] Risco avaliado (probabilidade × impacto) e dependências identificadas
- [ ] Dados e ambiente de teste disponíveis ou planeados

## Definition of Done (uma história está pronta)

- [ ] Código revisto (pull request aprovado) e no `main`
- [ ] Testes de componente e cenários BDD dos critérios de aceitação automatizados e verdes no pipeline
- [ ] Cobertura de código não desceu (relatório do pipeline)
- [ ] Sem defeitos abertos de severidade crítica ou alta
- [ ] Matriz de rastreabilidade regenerada; documentação atualizada
- [ ] Validado em UAT e aprovado no go/no-go

## Papéis

| Papel | Responsabilidade na qualidade |
| --- | --- |
| Business Analyst / PO | Regras de negócio, critérios de aceitação, prioridade dos defeitos, aceitação em UAT |
| Developer | Testes unitários, correções, análise técnica dos defeitos |
| QA | Estratégia, risco, automação de aceitação, execução, defeitos, reporting, go/no-go técnico |
| Team lead / PM | Decisões de âmbito e de risco aceite, planeamento das releases |

## Cerimónias com participação do QA

Refinamento (three amigos) · planeamento · daily (bloqueios, defeitos críticos) · revisão do sprint (demonstração a partir do UAT)
· retrospetiva (ações de melhoria do processo de testes).
