# Guia de onboarding · novo elemento de QA

Plano de 5 dias para alguém sem experiência no domínio ficar autónomo no QA Lab.
Cada dia tem um objetivo, leituras curtas e um exercício prático. Um elemento mais experiente acompanha (pair testing).

| Dia | Objetivo | Ler | Fazer |
| --- | --- | --- | --- |
| 1 | Perceber o negócio | `README.md` (regras de negócio), `docs/qa/estrategia-de-testes.md` | Na mini bolsa: executar TC-M01 e TC-M02 e explicar porque é que o negócio é a 4.50 |
| 2 | Ambientes e Linux | `docs/tecnico/linux-e-shell.md` | Exercícios 1 a 10 no terminal de QA; seguir uma ordem nos logs |
| 3 | Testes automáticos | `docs/qa/guia-de-automacao.md` | Correr `run_tests.sh unit` e `bdd`; acrescentar um cenário BDD num ramo Git |
| 4 | Defeitos | `docs/defeitos/README.md`, DEF-002 e DEF-003 | Pipeline com `MODO_DESAFIO`; reproduzir o DEF-004 sozinho e escrever o bug report |
| 5 | Release | `docs/qa/checklist-release.md`, `docs/tecnico/jenkins.md` | Acompanhar um pipeline completo, preencher o checklist e apresentar o go/no-go à equipa |

## Glossário rápido

| Termo | Significado |
| --- | --- |
| Livro de ordens | Lista de ordens de compra e venda à espera, ordenadas por preço e chegada |
| Prioridade preço-tempo | Executa primeiro o melhor preço; com o mesmo preço, quem chegou antes |
| Execução parcial | Só parte da quantidade é executada; o restante fica no livro |
| Ordem de mercado | Sem preço: executa contra o que houver; o que sobrar é cancelado |
| Tick size | Variação mínima de preço (aqui 0.01) |
| Bandas de preço | Limite de ±10% face ao preço de referência |
| T+2 | Liquidação dois dias úteis depois da negociação |
| TARGET2 / T2S | Sistema europeu de pagamentos / de liquidação de títulos; os seus feriados não são dias úteis |
| EOD | Fecho do dia: processos batch que liquidam e produzem relatórios |
| Hold / release | Reter e libertar uma instrução de liquidação |
| Smoke test | Verificação rápida do essencial depois de um deploy |
| Regressão | Voltar a testar o que já funcionava, depois de uma alteração |
| Go / no-go | Decisão de libertar (ou não) uma versão |

## Boas práticas que esperamos

1. Reproduzir antes de reportar; um defeito sem passos não é um defeito, é um palpite.
2. Perguntar cedo: uma dúvida no refinamento custa minutos, em UAT custa dias.
3. Nunca testar destrutivamente em UAT; nunca usar dados reais ou sistemas corporativos em testes.
4. Deixar os ambientes como os encontraste.
5. Escrever para quem decide: impacto primeiro, detalhe técnico depois.
