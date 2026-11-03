# Base de dados no QA Lab

Cada ambiente tem o seu PostgreSQL 15 (`qa-lab-qa-db`, `qa-lab-uat-db`). Esquema em `db/schema.sql`.

## Formas de aceder

| Onde | Como |
| --- | --- |
| Terminal do ambiente | `psql "$DATABASE_URL"` |
| Adminer (`localhost:8081`) | Sistema PostgreSQL · servidor `qa-lab-qa-db` ou `qa-lab-uat-db` · `qa` / `qa` · base `qa_lab` |
| VS Code ou DBeaver no teu PC | `localhost:5433` (QA) ou `localhost:5434` (UAT) · `qa` / `qa` · `qa_lab` |
| Consola SQL da página | Só leitura (a aplicação recusa INSERT, UPDATE e DELETE) |

## Modelo de dados

| Tabela | Chave | Relações e regras |
| --- | --- | --- |
| `orders` | `order_id` | `side` só BUY/SELL (CHECK); `price` NULL = ordem de mercado |
| `trades` | `trade_id` | `buy_order_id` e `sell_order_id` → `orders` (FOREIGN KEY); `qty > 0` (CHECK) |
| `settlement_instructions` | `instruction_id` | `trade_id` → `trades`, **UNIQUE** (no máximo 1 instrução por negócio); `status` só PENDING/ON_HOLD/SETTLED |
| `system_state` | `state_key` | Data de negócio do sistema |

## Consultas de QA (`db/consultas_qa.sql`)

11 consultas: 5 de análise e 5 verificações de integridade, que devem devolver **0 linhas**.
Validadas em PostgreSQL com 300 ordens geradas por `scripts/gerar_ordens.py`:

| Verificação | Dados corretos | Modo desafio |
| --- | --- | --- |
| 4 · Negócios sem instrução de liquidação | 0 | 0 |
| 5 · Quantidade executada ≠ ordem (DEF-003) | 0 | **13 ordens** |
| 6 · Montante ≠ quantidade × preço | 0 | 0 |
| 7 · Preço ≠ preço da ordem do livro (DEF-002) | 0 | **117 negócios** |
| 8 · Liquidadas antes da data prevista | 0 | 0 |

Correr tudo: `psql "$DATABASE_URL" -f db/consultas_qa.sql`

## Exercícios

1. Quantas ordens há por estado? E por símbolo e lado? *(GROUP BY com duas colunas)*
2. Qual a diferença entre `INNER JOIN` e `LEFT JOIN` na verificação 4? Porque é que tem de ser LEFT? *(o INNER esconderia os negócios sem instrução)*
3. Porque é que a verificação 5 repete a expressão no `HAVING` em vez de usar o alias `executado`? *(ver DEF-010)*
4. Tenta `INSERT INTO trades ...` com um `buy_order_id` que não existe. Que erro dá e porquê? *(chave estrangeira)*
5. Tenta criar uma segunda instrução para o mesmo negócio. *(restrição UNIQUE: proteção contra liquidar duas vezes)*
6. Dentro de `BEGIN; DELETE FROM settlement_instructions; SELECT count(*) ...; ROLLBACK;`, o que acontece aos dados? *(transações)*
7. Escreve uma consulta com o VWAP por símbolo no último dia de negociação. *(base: consulta 3)*
8. Que índice ajuda o fecho do dia a encontrar as instruções devidas? *(`idx_si_status_isd`; experimenta `EXPLAIN` na consulta do EOD)*
9. Faz um backup (`scripts/backup_db.sh`) e restaura-o numa base nova:
   `psql "$DATABASE_URL" -c "CREATE DATABASE teste"` e depois `gunzip -c <ficheiro> | psql "${DATABASE_URL%/*}/teste"`.
10. Diferença entre `DELETE`, `TRUNCATE` e `DROP`: experimenta numa cópia restaurada, nunca em UAT.
