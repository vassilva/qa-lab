# Template de pull request

```markdown
## O quê e porquê
<!-- Uma ou duas frases. Ligar à história ou ao defeito: DEF-NNN / AC-XNN -->

## Como foi testado
- [ ] Testes de componente acrescentados/atualizados (`tests/`)
- [ ] Cenário BDD que cobre o critério de aceitação (`features/`), com etiqueta de prioridade e `@AC-…`
- [ ] Para um defeito: o teste novo falha sem a correção e passa com ela
- [ ] Pipeline verde (QA · Regressão BDD)

## Impacto e risco
<!-- Componentes tocados, riscos da matriz afetados, migração de dados, alterações de configuração -->

## Checklist do revisor (QA)
- [ ] Os critérios de aceitação estão cobertos
- [ ] Casos-limite considerados
- [ ] Logs úteis para diagnóstico (com a etiqueta do componente)
- [ ] Documentação e matriz de rastreabilidade atualizadas
```
