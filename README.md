# QA Lab · Mini bolsa de valores

Laboratório de Quality Assurance que simula um sistema de negociação de uma bolsa
(ordens, livro de ordens, execuções), construído para demonstrar, feature a feature,
os requisitos de uma função de **QA Engineer em mercados financeiros**.

O progresso está na página **[/checklist](http://localhost:8000/checklist)**:
cada requisito da vaga é uma feature, com ✓ verde quando está feito e ✕ vermelho quando falta.

## Arranque rápido

Pré-requisitos: Docker Desktop (ou Docker Engine com Compose) e Git.

```bash
git clone <url-do-teu-repositório> qa-lab
cd qa-lab
docker compose up -d --build
```

Ao fim de cerca de 30 segundos:

| Endereço | O que é |
| --- | --- |
| http://localhost:8000 | Mini bolsa: enviar e cancelar ordens, livro de ordens, negócios, consola SQL |
| http://localhost:8000/checklist | Checklist da vaga (✓ / ✕) |
| http://localhost:7681 | Terminal Linux dentro do contentor, no browser |
| http://localhost:8081 | Adminer (base de dados no browser): sistema PostgreSQL, servidor `postgres`, utilizador `qa`, password `qa`, base `qa_lab` |
| `localhost:5433` | PostgreSQL para o VS Code ou o teu cliente SQL (utilizador `qa`, password `qa`) |

Comandos úteis:

```bash
docker compose ps                     # estado dos contentores
docker compose logs -f app            # mensagens de arranque
docker exec -it qa-lab-app bash       # entrar no contentor Linux (como um ssh)
docker compose down                   # parar (os dados ficam guardados)
docker compose down -v                # parar e apagar a base de dados
QA_LAB_CHALLENGE=1 docker compose up -d   # modo desafio: ativa defeitos escondidos
```

> O PostgreSQL do laboratório usa a porta **5433** no teu computador, para não chocar
> com um PostgreSQL que já tenhas instalado na 5432.

## Arquitetura

```
Browser ──► :8000 mini bolsa (Flask) ──► PostgreSQL (orders, trades)
        ──► :7681 terminal Linux (ttyd)        │
        ──► :8081 Adminer ─────────────────────┘
Contentor qa-lab-app (Debian Linux): aplicação, logs em /var/log/qa-lab, scripts e testes
Jenkins (o teu) ──► corre os testes a partir do repositório Git
```

## Estrutura

```
app/            aplicação: motor de negociação, base de dados, servidor web
app/static/     páginas web (mini bolsa e checklist)
db/schema.sql   esquema PostgreSQL
docker/         arranque do contentor
features/       cenários BDD (Gherkin)
checklist.json  estado das features da vaga
```

## Regras de negócio da mini bolsa

- Símbolos: EDP (4.50), GALP (15.20), BCP (0.65), NOS (3.80) — preços de referência em EUR.
- Ordens **limitadas** (com preço) ou **de mercado** (sem preço).
- Quantidade entre 1 e 10 000; preço múltiplo de 0.01 (tick size); preço dentro de ±10% da referência.
- Cruzamento por **prioridade preço-tempo**; o negócio é feito ao preço da ordem que já estava no livro.
- Execução parcial: o restante fica no livro. Ordens de mercado sem contraparte são canceladas.

## API

| Método | Caminho | Descrição |
| --- | --- | --- |
| GET | `/health` | Estado do serviço e da base de dados |
| GET | `/api/symbols` | Símbolos e preços de referência |
| POST | `/api/orders` | Nova ordem: `{"symbol":"EDP","side":"BUY","qty":100,"price":4.50}` (sem `price` = mercado) |
| DELETE | `/api/orders/<id>` | Cancelar ordem |
| GET | `/api/orders?status=FILLED` | Listar ordens |
| GET | `/api/book/<symbol>` | Livro de ordens |
| GET | `/api/trades` | Negócios |
| POST | `/api/query` | Query SQL de leitura: `{"sql":"SELECT ..."}` |
| POST | `/api/reset` | Apagar ordens e negócios |
