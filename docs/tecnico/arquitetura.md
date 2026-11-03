# Arquitetura de integração · QA Lab

O laboratório é **inspirado** na arquitetura pública da Euronext. Não é uma réplica dos seus sistemas.
Reproduz o tipo de sistemas e de integrações que um QA de pós-negociação testa:
negociação → mensagens → liquidação → sistema externo, com contratos, falhas e reconciliação.

## Visão geral (um ambiente: QA ou UAT)

```
                      ┌──────────────────────── TRADING (serviço "app") ─────────────────────────┐
  participante ─────► │ Order Entry Gateway → Matching Engine → Market Data    base: qa_lab       │
  (página / API)      │        negócio + evento gravados na MESMA transação (outbox)             │
                      └───────────────┬────────────────────────────────────────────────────────────┘
                                      │ publica TradeExecuted v1 (contracts/trade-executed.v1.schema.json)
                                      ▼
                           ┌─────── Apache Kafka ───────┐
                           │ trades.executed            │
                           │ trades.executed.dlq (erros)│
                           └─────────────┬──────────────┘
                                         │ consome (grupo settlement-service), valida o contrato, idempotente
                                         ▼
                      ┌──────────────────────── SETTLEMENT ─────────────────────────────┐
                      │ instruções T+2 · hold/release · fecho do dia    base: settlement │
                      └───────────────┬───────────────────────────────▲──────────────────┘
                     ficheiro SI_*.csv│                               │ficheiro CONF_*.csv
                                      ▼                               │
                      ┌────────── simulador T2S (sistema externo) ──────────┐
                      │ normal · rejeitar_simbolo · rejeitar_tudo · lento · indisponivel │
                      └──────────────────────────────────────────────────────┘
```

| Serviço | Contentor (QA) | Porta QA / UAT | Base de dados | Log |
| --- | --- | --- | --- | --- |
| Trading | `qa-lab-qa-app` | 8000 / 9000 (+ terminal 7681 / 7682) | `qa_lab` | `qa-lab.log` |
| Settlement | `qa-lab-qa-settlement` | 8100 / 9100 | `settlement` | `settlement.log` |
| Simulador T2S | `qa-lab-qa-t2s` | 8200 / 9200 | — | `t2s-sim.log` |
| Kafka | `qa-lab-qa-kafka` | interna (`kafka:9092`) | — | `docker logs` |
| PostgreSQL | `qa-lab-qa-db` | 5433 / 5434 | `qa_lab` e `settlement` | — |

Os logs dos três serviços estão no mesmo volume, `/var/log/qa-lab/`, e o terminal do Trading vê-os todos:
é possível seguir um negócio de ponta a ponta com `grep T00001 /var/log/qa-lab/*.log`.

## Ligação ao que a Euronext publica

| No laboratório | Referência pública |
| --- | --- |
| Order Entry Gateway, Matching Engine, Market Data | Componentes da plataforma Optiq (OEG, ME, MDG) na documentação técnica para membros |
| Kafka para integração orientada a eventos | Vagas de backend da equipa de Settlement da Euronext Securities (Porto): "Kafka (strong plus)" |
| APIs descritas em OpenAPI (`contracts/*.openapi.yaml`) | As mesmas vagas: "RESTful APIs aligned with OpenAPI standards" |
| Settlement T+2 com calendário TARGET2 e T2S | Euronext Securities Porto: liquidação em T2S, ciclos noturno e diurno, reciclagem |
| Testes de regressão e reconciliação entre sistemas | Projeto Convergence (migração dos sistemas de liquidação do mainframe para Java): provar que o sistema novo dá os mesmos resultados |

## Padrões de integração e como se testam

| Padrão | Porque existe | Como se testa |
| --- | --- | --- |
| **Contrato de mensagem** (JSON Schema) | Produtor e consumidor evoluem em equipas diferentes | `tests/integration/test_integracao.py` (6 variações inválidas), AC-I01 |
| **Transactional outbox** | Se o Kafka falhar, nenhum negócio fica sem evento | Consumidor em pausa → evento pendente → entregue depois (AC-I04) |
| **Entrega pelo menos uma vez + idempotência** | O Kafka pode entregar a mesma mensagem duas vezes | Reenvio do mesmo evento → 1 instrução (AC-I02) |
| **Dead letter queue** | Uma mensagem má não pode bloquear as boas | Mensagem fora do contrato → `rejected_events` e `trades.executed.dlq` (AC-I03) |
| **Interface por ficheiro** | Comum em banca e com sistemas externos (T2S, custódia) | Ficheiros `SI_*.csv` / `CONF_*.csv` em `/var/lib/qa-lab/files` |
| **Reciclagem** | Uma instrução falhada volta a tentar no ciclo seguinte | T2S rejeita → FAILED → liquida no fecho seguinte (AC-I05, AC-I06) |
| **Reconciliação entre sistemas** | Cada sistema tem a sua base de dados: as diferenças só se veem comparando | `GET /api/reconciliation` e o passo BDD de reconciliação |
| **Geração do ambiente** | Eventos "em trânsito" de um teste anterior não podem poluir o seguinte | Evento de geração antiga é ignorado (teste pytest) |

## Ver as mensagens no Kafka

```bash
# no teu PC (PowerShell): mensagens do tópico, desde o início
docker exec qa-lab-qa-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic trades.executed --from-beginning --timeout-ms 5000
# fila de erros
docker exec qa-lab-qa-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic trades.executed.dlq --from-beginning --timeout-ms 5000
# atraso do consumidor (lag): quantas mensagens o Settlement ainda não processou
docker exec qa-lab-qa-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group settlement-service
```

## Desenvolvimento local e testes

| Onde | Barramento | Para quê |
| --- | --- | --- |
| Ambientes QA e UAT (Docker) | Kafka (`QA_LAB_KAFKA`) | O real |
| Processos locais | Fila num ficheiro SQLite (`QA_LAB_BUS_FILE`) | Correr os três serviços separados sem Kafka |
| pytest | Em memória | Testes rápidos e determinísticos, no mesmo processo |

As três implementações seguem a mesma semântica do Kafka (confirmação só depois de processar, reentrega em falhas).
O conector Kafka (`KafkaBus`) é validado no pipeline, no ambiente QA.
