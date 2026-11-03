# Retrospetiva e melhoria contínua · QA Lab

Retrospetiva da construção do laboratório (2 a 3 de novembro de 2026), com factos reais do projeto.

## O que correu bem

- O gate de qualidade funciona: com defeitos ativos, a regressão falha e nada chega a UAT.
- A mesma imagem promovida de QA para UAT eliminou a pergunta "o que testámos é o que foi instalado?".
- Validar o SQL no mesmo motor da produção apanhou um erro antes de chegar a um ambiente (DEF-010).
- A leitura cuidadosa de logs (horas do build vs. horas da atualização) evitou "corrigir" código que não tinha defeito (DEF-008).

## O que correu menos bem

| Facto | Causa | Lição |
| --- | --- | --- |
| Build da imagem falhou na primeira vez (DEF-009) | Dependência assumida sem verificar | Verificar a disponibilidade dos pacotes na distribuição alvo |
| Pipeline correu no Jenkins antigo (DEF-008) | Atualização da infraestrutura em paralelo com o disparo automático | Atualizar ferramentas antes de disponibilizar commits |
| Testes deixavam o QA sujo (DEF-006) | Só havia preparação, não havia limpeza | Cada suite deixa o ambiente como o encontrou |
| Mensagem de falha enganadora (DEF-007) | Texto genérico que afirmava algo nem sempre verdadeiro | As mensagens não podem afirmar o que não sabem |
| Nomes dos grupos no Docker confundiam (`qa-lab` parecia um ambiente) | Nome por omissão da pasta | Dar nomes explícitos aos grupos: `qa`, `uat`, `qa-lab-tools` |
| Cliente e servidor PostgreSQL de versões diferentes (DEF-011) | Imagens escolhidas em separado | Verificar a compatibilidade das ferramentas de operação (backups) |
| Ia usar-se uma ligação ao Jira corporativo para dados de teste | A ferramenta tinha acesso | Dados de teste nunca em sistemas corporativos; Jira pessoal (F1) |

## Ações de melhoria

| # | Ação | Responsável | Estado |
| --- | --- | --- | --- |
| A1 | Limpeza no fim dos testes BDD, com proteção do UAT | QA | ✓ Feito (DEF-006) |
| A2 | Estágios do Jenkins agrupados por ambiente (QA · / UAT ·) | QA | ✓ Feito |
| A3 | Grupos `qa`, `uat`, `qa-lab-tools`, com migração automática no deploy | QA | ✓ Feito |
| A4 | Medir a cobertura de código no pipeline e subir de 85% para 93% | QA | ✓ Feito |
| A5 | Relatório HTML com critérios, riscos e defeitos para o go/no-go | QA | ✓ Feito |
| A6 | Verificações SQL de integridade como estágio do pipeline | QA | Planeado (plano de automação #1) |
| A7 | Testes de interface com Playwright para 3 casos manuais | QA | Planeado (plano de automação #3) |
| A8 | Registar os defeitos num Jira pessoal de testes | QA | Planeado (F1) |

## Métricas a acompanhar entre releases

Defeitos encontrados em QA vs. em UAT (fuga de defeitos) · tempo do commit até QA validado · cobertura de critérios de
aceitação e de código · cenários instáveis (devem ser 0) · tempo médio de correção por severidade.
