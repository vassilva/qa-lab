# Guia da automação de testes · QA Lab

Como está organizada a automação, e como acrescentar um teste novo em 10 minutos.

## Frameworks e camadas

| Camada | Framework | Pasta | Corre contra |
| --- | --- | --- | --- |
| Componente (standalone) | pytest (fixtures, `parametrize`) | `tests/unit/` | Código em memória, sem rede nem base de dados |
| API + base de dados | pytest + cliente de teste do Flask | `tests/api/` | Aplicação em processo, SQLite temporário |
| Aceitação (BDD) | behave, Gherkin em português | `features/` + `features/steps/` | Ambiente QA real (API REST + PostgreSQL), via `requests` |
| Smoke | Bash + `curl` + `jq` | `scripts/smoke.sh` | QA e UAT depois de cada deploy |
| Integridade de dados | SQL | `db/consultas_qa.sql` | PostgreSQL do ambiente |

Princípios: pirâmide de testes (muitos testes rápidos de componente, menos testes de ponta a ponta);
cada cenário independente (prepara os próprios dados); testes determinísticos (datas fixas, semente fixa no gerador);
nunca correr testes destrutivos em UAT (proteção no `features/environment.py`).

## Estrutura BDD

```
features/
  01_validacao_ordens.feature     Funcionalidade + critérios de aceitação (AC-V..) + cenários
  02_execucao_ordens.feature      AC-N..
  03_liquidacao.feature           AC-L..
  environment.py                  hooks: verifica o ambiente, proteção do UAT, limpeza no fim
  steps/mercado_steps.py          passos de ordens, negócios, livro
  steps/liquidacao_steps.py       passos de liquidação, EOD, reconciliação SQL
```

Etiquetas: prioridade (`@critico`, `@alto`, `@medio`), rastreabilidade (`@AC-xxx`), área (`@gateway`, `@matching`,
`@settlement`), tipo (`@smoke`, `@fronteira`, `@regressao`).

## Acrescentar um cenário (passo a passo)

1. Escolher o critério de aceitação (ou criar um novo na secção "Critérios de aceitação" do `.feature`).
2. Escrever o cenário em linguagem de negócio, reutilizando passos que já existem:
   ```gherkin
   @AC-N01 @critico
   Cenário: Venda que cruza executa ao preço da compra que estava no livro
     Dado um mercado limpo com a data de negócio "2026-11-02"
     E que existe uma ordem "C1" de compra de 100 "GALP" a 15.20 EUR
     Quando é submetida uma ordem "V1" de venda de 100 "GALP" a 15.10 EUR
     Então existe 1 negócio de 100 ações a 15.20 EUR
   ```
3. Correr só esse cenário no terminal de QA: `BDD_TAGS=@AC-N01 bash scripts/run_tests.sh bdd`.
4. Se faltar um passo, behave mostra o esqueleto a implementar; acrescentá-lo em `features/steps/`.
5. Regenerar a rastreabilidade: `python3 scripts/rastreabilidade.py`. Fazer commit e o Jenkins faz o resto.

## Scripts Python de apoio

| Script | Faz |
| --- | --- |
| `scripts/test_summary.py` | Relatório de testes (Markdown + HTML): progresso, cobertura, critérios, riscos, defeitos, recomendação GO/NO-GO |
| `scripts/rastreabilidade.py` | Gera a matriz de rastreabilidade a partir dos ficheiros do projeto |
| `scripts/qa_artifacts.py` | Biblioteca partilhada: lê features, riscos, casos manuais, defeitos e relatórios JUnit |
| `scripts/gerar_ordens.py` | Gera ordens reproduzíveis (`--seed`) para exploração e volume, com tempos de resposta |

## Testes instáveis (flaky): regras da casa

Nenhum `sleep` fixo nos testes (o deploy espera pelo healthcheck); dados criados pelo próprio cenário; nenhuma dependência
da data de hoje; falha intermitente = defeito no teste, investigado como qualquer outro, nunca "correr outra vez até passar".
