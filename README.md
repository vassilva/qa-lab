# QA Lab · Mini bolsa de valores

Laboratório de Quality Assurance que simula, de forma simplificada, a cadeia de uma bolsa:
**ordem → negociação → liquidação T+2**. A arquitetura é **inspirada** na arquitetura pública
da Euronext (não é uma réplica dos seus sistemas).

Cada requisito da vaga de QA é uma feature, e o progresso está na página **/checklist**
(✓ verde = feito, ✕ vermelho = por fazer).

## Arquitetura

| Componente | Ficheiro | O que faz |
| --- | --- | --- |
| Order Entry Gateway (OEG) | `app/gateway.py` | Recebe e valida as ordens: quantidade, tick size, bandas de preço, símbolo |
| Matching Engine (ME) | `app/matching_engine.py` | Cruza ordens por prioridade preço-tempo, execuções parciais, ordens de mercado |
| Market Data | `app/server.py` (API) | Livro de ordens e negócios em tempo real |
| Settlement T+2 | `app/settlement.py` | Instruções de liquidação, calendário TARGET2, hold/release, fecho do dia (EOD) |
| Base de dados | `db/schema.sql` | PostgreSQL: `orders`, `trades`, `settlement_instructions`, `system_state` |

## Ambientes e ferramentas

| | QA | UAT |
| --- | --- | --- |
| Para quê | Testes automáticos completos a cada versão | Aceitação da release e decisão go/no-go |
| Mini bolsa | http://localhost:8000 | http://localhost:9000 |
| Terminal Linux | http://localhost:7681 | http://localhost:7682 |
| PostgreSQL (VS Code, cliente SQL) | `localhost:5433` | `localhost:5434` |
| Contentores | `qa-lab-qa-app`, `qa-lab-qa-db` | `qa-lab-uat-app`, `qa-lab-uat-db` |

Partilhados:
- **Jenkins** http://localhost:8090 (utilizador `admin`, password `admin`)
- **Adminer** http://localhost:8081 (sistema PostgreSQL · servidor `qa-lab-qa-db` ou `qa-lab-uat-db` · utilizador `qa` · password `qa` · base `qa_lab`)

Base de dados: utilizador `qa`, password `qa`, base `qa_lab`.

## Pipeline (Jenkinsfile)

```
Preparar → Build da imagem → Testes unitários e de API → Deploy QA → Smoke QA
        → Regressão BDD (QA) → Deploy UAT → Smoke UAT → Aprovação go/no-go
```

A imagem é construída **uma vez** (`qa-lab:<versão>-<commit>`) e a mesma imagem é promovida de QA para UAT.
O Jenkins verifica o repositório a cada 2 minutos: cada `git commit` dispara o pipeline.

## Arranque (Windows, PowerShell no VS Code)

Pré-requisitos: Docker Desktop a correr e Git.

```powershell
docker network create qa-lab-net        # só da primeira vez
docker compose up -d --build            # Jenkins + Adminer (da primeira vez demora alguns minutos)
```

Depois abre http://localhost:8090, entra com `admin` / `admin`, abre **qa-lab-pipeline** e carrega em
**Build Now**. O pipeline constrói a imagem e cria os ambientes QA e UAT. No fim, espera pela tua
aprovação (go/no-go).

Comandos úteis:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"   # o que está a correr
docker exec -it qa-lab-qa-app bash                                # entrar no servidor de QA (como um ssh)
docker logs qa-lab-uat-app                                        # mensagens de arranque do UAT
docker compose -p qa-lab-qa down                                  # parar o QA (dados mantidos)
docker compose down                                               # parar Jenkins e Adminer
```

Dentro do servidor Linux (terminal no browser ou `docker exec`):

```bash
tail -f /var/log/qa-lab/qa-lab.log            # log da aplicação, com etiquetas [OEG] [ME] [SETTLEMENT] [API]
ls /var/log/qa-lab/eod/                       # relatórios CSV do fecho do dia
bash scripts/smoke.sh                         # smoke test
bash scripts/run_tests.sh unit                # testes unitários e de API
```

## Regras de negócio

**Negociação**
- Símbolos e preços de referência (EUR): BCP 0.65 · EDP 4.50 · GALP 15.20 · NOS 3.80.
- Ordens limitadas (com preço) ou de mercado (sem preço).
- Quantidade de 1 a 10 000; preço múltiplo de 0.01; preço dentro de ±10% da referência (limites incluídos).
- Prioridade preço-tempo; o negócio faz-se ao preço da ordem que já estava no livro.
- Execução parcial: o restante fica no livro. Ordem de mercado sem contraparte é cancelada.

**Liquidação**
- Cada negócio gera uma instrução de liquidação para T+2 dias úteis.
- Dias úteis: segunda a sexta, exceto os dias de fecho TARGET2 (1 jan, Sexta-feira Santa,
  Segunda-feira de Páscoa, 1 mai, 25 e 26 dez).
- Estados: `PENDING` → `SETTLED`; `ON_HOLD` (hold) não liquida até ser libertada (release).
- O fecho do dia (EOD) liquida as instruções devidas, escreve `eod/settlement_AAAAMMDD.csv`
  e avança a data de negócio para o próximo dia útil.

**Modo desafio:** com `QA_LAB_CHALLENGE=1` a aplicação passa a ter defeitos escondidos, para treinar
a análise e o reporte de defeitos.

## API

| Método | Caminho | Descrição |
| --- | --- | --- |
| GET | `/health` | Estado, ambiente, versão e base de dados |
| GET | `/api/symbols` | Símbolos e preços de referência |
| POST | `/api/orders` | Nova ordem: `{"symbol":"EDP","side":"BUY","qty":100,"price":4.50}` (sem `price` = mercado) |
| DELETE | `/api/orders/<id>` | Cancelar ordem |
| GET | `/api/orders?status=FILLED` | Listar ordens |
| GET | `/api/book/<símbolo>` | Livro de ordens |
| GET | `/api/trades` | Negócios |
| GET / POST | `/api/business-date` | Ver ou mudar a data de negócio: `{"date":"2026-11-06"}` (só dias úteis) |
| GET | `/api/settlement/instructions?status=PENDING` | Instruções de liquidação |
| POST | `/api/settlement/instructions/<id>/hold` · `/release` | Reter ou libertar uma instrução |
| POST | `/api/eod` | Fecho do dia |
| POST | `/api/query` | Query SQL só de leitura: `{"sql":"SELECT ..."}` |
| POST | `/api/reset` | Apagar os dados do ambiente |

## Estrutura

```
app/                 componentes da aplicação e páginas web (app/static)
db/schema.sql        esquema da base de dados
docker/              arranque do contentor
envs/                configuração dos ambientes QA e UAT
features/            cenários BDD (Gherkin)
jenkins/             Jenkins do laboratório (configuração como código)
scripts/             deploy, smoke test, testes, espera pelo serviço
tests/               testes pytest (unitários e de API)
Jenkinsfile          pipeline CI/CD
docker-compose.yml   Jenkins + Adminer
docker-compose.env.yml  definição de um ambiente (usada para QA e UAT)
checklist.json       estado das features da vaga
```
