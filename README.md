# QA Lab · Mini bolsa de valores

Laboratório de Quality Assurance que simula, de forma simplificada, a cadeia de uma bolsa:
**ordem → negociação → mensagem (Kafka) → liquidação T+2 → sistema externo (T2S)**. A arquitetura é **inspirada** na arquitetura pública
da Euronext (não é uma réplica dos seus sistemas).

Cada requisito da vaga de QA é uma feature, e o progresso está na página **/checklist**
(✓ verde = feito, ✕ vermelho = por fazer).

## Arquitetura

Três serviços separados, cada um com a sua base de dados, ligados por Kafka e por ficheiros
(detalhe em `docs/tecnico/arquitetura.md`):

```
Trading (OEG → ME → Market Data) ──Kafka: trades.executed──► Settlement T+2 ──ficheiros SI/CONF──► simulador T2S
        base qa_lab                  (DLQ: trades.executed.dlq)      base settlement
```

| Componente | Ficheiro | O que faz |
| --- | --- | --- |
| Order Entry Gateway (OEG) | `app/gateway.py` | Recebe e valida as ordens: quantidade, tick size, bandas de preço, símbolo |
| Matching Engine (ME) | `app/matching_engine.py` | Cruza ordens por prioridade preço-tempo, execuções parciais, ordens de mercado |
| Trading (API, Market Data, outbox) | `app/server.py` | API, livro de ordens, negócios; publica TradeExecuted pelo outbox |
| Barramento | `app/bus.py` | Kafka nos ambientes; ficheiro ou memória em testes locais |
| Contrato do evento | `contracts/trade-executed.v1.schema.json` | JSON Schema do TradeExecuted v1 |
| Settlement | `app/settlement_service.py`, `app/settlement.py` | Consome os eventos, instruções T+2, TARGET2, hold/release, fecho do dia, reciclagem |
| Simulador T2S | `app/t2s_simulator.py` | Confirma ou rejeita instruções por ficheiro; modos de falha |
| Contratos de API | `contracts/*.openapi.yaml` | OpenAPI 3 dos três serviços |
| Bases de dados | `db/schema.sql`, `db/schema_settlement.sql` | `qa_lab` (ordens, negócios, outbox) e `settlement` (instruções, eventos rejeitados) |

## Ambientes e ferramentas

| | QA | UAT |
| --- | --- | --- |
| Para quê | Testes automáticos completos a cada versão | Aceitação da release e decisão go/no-go |
| Mini bolsa | http://localhost:8000 | http://localhost:9000 |
| Terminal Linux | http://localhost:7681 | http://localhost:7682 |
| PostgreSQL (VS Code, cliente SQL) | `localhost:5433` | `localhost:5434` |
| Settlement (API) | http://localhost:8100 | http://localhost:9100 |
| Simulador T2S (API) | http://localhost:8200 | http://localhost:9200 |
| Contentores | `qa-lab-qa-{app,settlement,t2s,kafka,db}` | `qa-lab-uat-{app,settlement,t2s,kafka,db}` |

Partilhados:
- **Jenkins** http://localhost:8090 (utilizador `admin`, password `admin`)
- **Adminer** http://localhost:8081 (sistema PostgreSQL · servidor `qa-lab-qa-db` ou `qa-lab-uat-db` · utilizador `qa` · password `qa` · base `qa_lab` ou `settlement`)

Bases de dados: utilizador `qa`, password `qa`, bases `qa_lab` (Trading) e `settlement`.

## Pipeline (Jenkinsfile)

```
Preparar → Build da imagem → Testes de componente e API
  → QA · Deploy → QA · Smoke → QA · Regressão BDD
  → UAT · Deploy → UAT · Smoke → UAT · Resumo de testes → UAT · Go/No-go
```

A imagem é construída **uma vez** (`qa-lab:<versão>-<commit>`) e a mesma imagem é promovida de QA para UAT.
O Jenkins verifica o repositório a cada 2 minutos: cada `git commit` dispara o pipeline. Há também uma regressão
noturna em QA (dias úteis, ~02:00) que não passa para UAT. Parâmetros: `REGRESSAO` (completa/critica) e `MODO_DESAFIO`.

No Docker Desktop há três grupos: **`qa`**, **`uat`** e **`qa-lab-tools`** (Jenkins + Adminer).

## Testes

| Nível | Onde | Como correr |
| --- | --- | --- |
| Componentes e API (standalone) | `tests/` (pytest) | `bash scripts/run_tests.sh unit` |
| Aceitação BDD (Gherkin em português) | `features/` (behave) | `bash scripts/run_tests.sh bdd` (só em QA) |
| Só os críticos | | `BDD_TAGS=@critico bash scripts/run_tests.sh bdd` |
| Um critério de aceitação | | `BDD_TAGS=@AC-L03 bash scripts/run_tests.sh bdd` |
| Smoke pós-deploy | `scripts/smoke.sh` | `bash scripts/smoke.sh` |
| Integridade de dados | `db/consultas_qa.sql` | `psql "$DATABASE_URL" -f db/consultas_qa.sql` |
| Relatório de testes | `scripts/test_summary.py` | `python3 scripts/test_summary.py reports` → `localhost:8000/reports/` |
| Rastreabilidade | `scripts/rastreabilidade.py` | `python3 scripts/rastreabilidade.py` |

| Integração entre serviços e contratos | `tests/integration/` (pytest) | incluído em `unit` |

Hoje: **86** testes pytest (cobertura de código 86%) e **33** cenários BDD (21 critérios de aceitação, 100% automatizados).

Os cenários BDD reiniciam os dados, por isso **recusam correr em UAT**.
No Jenkins, **Build with Parameters** permite escolher regressão `completa` ou `critica`.

Toda a documentação está em `docs/` e no índice **`localhost:8000/docs/`**: qualidade (estratégia, risco, casos manuais,
relatórios, rastreabilidade, automação, IA), defeitos, guias técnicos (Linux, SQL, Git, Jenkins), processo e onboarding.

## Arranque (Windows, PowerShell no VS Code)

Pré-requisitos: Docker Desktop a correr e Git.

```powershell
docker network create qa-lab-net        # só da primeira vez
docker compose up -d --build            # Jenkins + Adminer (da primeira vez demora alguns minutos)
```

O Docker Desktop precisa de **~6 GB de memória** (Settings → Resources): cada ambiente tem agora Kafka e três serviços.

**Atualizar o laboratório para uma versão nova** (evita o DEF-008):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\atualizar_ferramentas.ps1 -SoPausar   # 1. Jenkins em pausa
# 2. substituir os ficheiros do projeto e fazer o commit
powershell -ExecutionPolicy Bypass -File scripts\atualizar_ferramentas.ps1             # 3. reconstrói e reinicia o Jenkins
```

Depois abre http://localhost:8090, entra com `admin` / `admin`, abre **qa-lab-pipeline** e carrega em
**Build Now**. O pipeline constrói a imagem e cria os ambientes QA e UAT. No fim, espera pela tua
aprovação (go/no-go).

Comandos úteis:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"   # o que está a correr
docker exec -it qa-lab-qa-app bash                                # entrar no servidor de QA (como um ssh)
docker logs qa-lab-uat-app                                        # mensagens de arranque do UAT
docker exec qa-lab-qa-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic trades.executed --from-beginning --timeout-ms 5000   # mensagens no Kafka
docker compose -p qa down                                         # parar o QA (dados mantidos)
docker compose down                                               # parar Jenkins e Adminer
```

Dentro do servidor Linux (terminal no browser ou `docker exec`):

```bash
tail -f /var/log/qa-lab/qa-lab.log            # log do Trading, com etiquetas [OEG] [ME] [API]
tail -f /var/log/qa-lab/settlement.log        # log do Settlement (consumidor, EOD)
grep -h T00001 /var/log/qa-lab/*.log          # um negócio seguido pelos três serviços
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
- Estados: `PENDING` → `SETTLED`; `ON_HOLD` (hold) não liquida até ser libertada (release);
  `FAILED` quando o T2S rejeita ou não responde: é reciclada no fecho seguinte.
- No fecho do dia o Settlement envia um ficheiro `SI_*.csv` ao T2S e lê a confirmação `CONF_*.csv`.
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
| GET | `/api/integration` | Estado do barramento, outbox, Settlement e T2S |
| GET | `/api/reconciliation` | Diferenças entre negócios (Trading) e instruções (Settlement) |
| POST | `/api/t2s/mode` | Modo do simulador T2S: `{"mode":"rejeitar_simbolo","symbol":"GALP"}` (só QA) |
| POST | `/api/reset` | Apagar os dados do ambiente (Trading, Settlement e T2S) |

Contratos completos: `contracts/trading.openapi.yaml`, `settlement.openapi.yaml`, `t2s-simulator.openapi.yaml`.

## Estrutura

```
app/                 componentes da aplicação e páginas web (app/static)
contracts/           JSON Schema do evento e OpenAPI dos três serviços
db/                  esquemas das bases (qa_lab, settlement) e consultas de QA
docker/              arranque do contentor
envs/                configuração dos ambientes QA e UAT
features/            cenários BDD (Gherkin) e passos automatizados (features/steps)
docs/                qa/ defeitos/ tecnico/ processo/ onboarding/ (índice em /docs/)
jenkins/             Jenkins do laboratório (configuração como código)
scripts/             deploy, smoke, testes, relatório, rastreabilidade, logs, EOD, backup, gerador de ordens
tests/               testes pytest (unitários e de API)
Jenkinsfile          pipeline CI/CD
docker-compose.yml   Jenkins + Adminer
docker-compose.env.yml  definição de um ambiente (usada para QA e UAT)
checklist.json       estado das features da vaga
```
