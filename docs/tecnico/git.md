# Git no QA Lab

## Fluxo de trabalho

| Ramo | Para quê | Exemplo |
| --- | --- | --- |
| `main` | Sempre estável; cada commit dispara o pipeline no Jenkins | |
| `feature/<descricao>` | Funcionalidade nova ou documentação | `feature/epico-2-defeitos-e-relatorios` |
| `fix/DEF-NNN-<descricao>` | Correção de um defeito, com o ID no nome | `fix/DEF-006-bdd-repoe-ambiente` |

Os ramos entram no `main` com **merge sem fast-forward** (`git merge --no-ff`), para o histórico mostrar
que trabalho veio de cada ramo. Num repositório no GitHub isto é um **pull request** com revisão
(ver `docs/processo/template-pull-request.md`).

**Mensagens de commit:** primeira linha curta no imperativo ("Corrige…", "Acrescenta…"), com o ID do defeito
quando existe; corpo com o porquê.

## Ver o histórico deste projeto

```bash
git log --oneline --graph --all     # ramos e merges
git log --grep=DEF-006              # tudo o que tocou num defeito
git show --stat HEAD~1              # ficheiros alterados num commit
git blame features/environment.py   # quem alterou cada linha e em que commit
```

## Exercícios (no VS Code, terminal na pasta do projeto)

| # | Tarefa | Comandos |
| --- | --- | --- |
| 1 | Configurar o teu nome e email (uma vez) | `git config --global user.name "…"` · `git config --global user.email "…"` |
| 2 | Ver o estado e o histórico | `git status` · `git log --oneline --graph` |
| 3 | Criar um ramo para um cenário novo | `git switch -c feature/cenario-ordem-gal` |
| 4 | Acrescentar um cenário BDD, ver a diferença e fazer commit | `git diff` · `git add features/` · `git commit -m "Acrescenta cenário …"` |
| 5 | Voltar ao `main` e juntar o ramo | `git switch main` · `git merge --no-ff feature/cenario-ordem-gal` |
| 6 | Ver o Jenkins disparar sozinho (até 2 minutos) | `localhost:8090` → "Started by an SCM change" |
| 7 | Provocar um conflito: alterar a mesma linha em dois ramos e juntar | Resolver no VS Code, `git add`, `git commit` |
| 8 | Desfazer um commit já partilhado, sem reescrever o histórico | `git revert <commit>` |
| 9 | Guardar trabalho a meio para mudar de tarefa | `git stash` · `git stash pop` |
| 10 | Marcar a versão aprovada em UAT | `git tag -a v0.4.0 -m "Aprovada em UAT"` · `git tag` |

**merge vs. rebase:** o `merge` preserva o histórico tal como aconteceu (com um commit de junção); o `rebase` reescreve
os commits do ramo em cima do `main`, ficando linear. Regra: não fazer rebase de commits já partilhados.

## Publicar no GitHub (opcional)

1. Criar um repositório vazio no GitHub (por exemplo, `qa-lab`).
2. `git remote add origin https://github.com/<utilizador>/qa-lab.git`
3. `git push -u origin main --tags` (e os ramos que quiseres mostrar).

O Jenkins do laboratório continua a ler o repositório local; ligá-lo ao GitHub é um passo seguinte opcional.
