"""
Barramento de mensagens entre sistemas (Trading → Settlement), inspirado na arquitetura orientada a eventos
que a Euronext Securities refere nas suas vagas (Kafka).

Três implementações com a mesma interface, escolhidas pela configuração:
- KafkaBus   QA_LAB_KAFKA=host:porta   ambientes QA e UAT (Apache Kafka)
- FileBus    QA_LAB_BUS_FILE=caminho   desenvolvimento local: serviços em processos diferentes, fila num ficheiro SQLite
- MemoryBus  (por omissão)             testes pytest: entrega síncrona, no mesmo processo

Semântica (igual ao Kafka): entrega "pelo menos uma vez" (at-least-once). O consumidor confirma (commit) a mensagem
só depois de a processar; se o processamento falhar com RetryableError, a mesma mensagem é entregue outra vez.
Por isso o consumidor tem de ser idempotente: receber a mesma mensagem duas vezes não pode criar dois resultados.
"""

import json
import os
import sqlite3
import threading
import time

from app.logs import get_logger

TOPIC_TRADES = "trades.executed"
TOPIC_TRADES_DLQ = "trades.executed.dlq"

log = get_logger("BUS")


class RetryableError(Exception):
    """Falha temporária (ex.: base de dados em baixo): a mensagem não é confirmada e será entregue outra vez."""


class MemoryBus:
    name = "memory"

    def __init__(self):
        self.messages = []
        self._handlers = {}
        self.paused = set()

    def publish(self, topic, key, value):
        self.messages.append((topic, key, value))
        for handler in self._handlers.get(topic, []):
            if topic not in self.paused:
                handler(value)

    def start_consumer(self, topic, group, handler):
        self._handlers.setdefault(topic, []).append(handler)

    def ping(self):
        return True


class FileBus:
    """Fila persistente num ficheiro SQLite partilhado por vários processos (só para desenvolvimento local)."""
    name = "file"

    def __init__(self, path):
        self.path = path
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT, key TEXT, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS offsets (grp TEXT, topic TEXT, last_id INTEGER, PRIMARY KEY (grp, topic))")

    def _conn(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level=None)

    def publish(self, topic, key, value):
        with self._conn() as c:
            c.execute("INSERT INTO messages (topic, key, value) VALUES (?, ?, ?)", (topic, key, json.dumps(value)))

    def start_consumer(self, topic, group, handler):
        def loop():
            while True:
                try:
                    with self._conn() as c:
                        row = c.execute("SELECT last_id FROM offsets WHERE grp=? AND topic=?", (group, topic)).fetchone()
                        last = row[0] if row else 0
                        msgs = c.execute("SELECT id, value FROM messages WHERE topic=? AND id>? ORDER BY id LIMIT 50",
                                         (topic, last)).fetchall()
                    for msg_id, value in msgs:
                        handler(json.loads(value))
                        with self._conn() as c:
                            c.execute("INSERT INTO offsets (grp, topic, last_id) VALUES (?, ?, ?) "
                                      "ON CONFLICT (grp, topic) DO UPDATE SET last_id=excluded.last_id", (group, topic, msg_id))
                except RetryableError as exc:
                    log.warning("Processamento adiado (%s); a mensagem será entregue outra vez", exc)
                except Exception:  # noqa: BLE001
                    log.exception("Erro no consumidor %s/%s", group, topic)
                time.sleep(0.2)
        threading.Thread(target=loop, daemon=True, name=f"consumer-{topic}").start()

    def ping(self):
        return os.path.exists(self.path)


class KafkaBus:
    name = "kafka"

    def __init__(self, bootstrap):
        self.bootstrap = bootstrap
        self._producer = None
        self._lock = threading.Lock()

    def _get_producer(self):
        from kafka import KafkaProducer  # instalado no contentor (kafka-python)
        with self._lock:
            if self._producer is None:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap, acks="all", retries=3,
                    key_serializer=lambda k: k.encode("utf-8"),
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"))
            return self._producer

    def publish(self, topic, key, value):
        # .get() espera pela confirmação do broker: só depois disto o evento conta como publicado
        self._get_producer().send(topic, key=key, value=value).get(timeout=10)

    def start_consumer(self, topic, group, handler):
        def loop():
            from kafka import KafkaConsumer, TopicPartition
            while True:
                try:
                    consumer = KafkaConsumer(
                        topic, bootstrap_servers=self.bootstrap, group_id=group, enable_auto_commit=False,
                        auto_offset_reset="earliest", value_deserializer=lambda v: v)
                    log.info("Consumidor %s ligado ao tópico %s (%s)", group, topic, self.bootstrap)
                    for msg in consumer:
                        try:
                            handler(json.loads(msg.value.decode("utf-8")))
                        except RetryableError as exc:
                            log.warning("Processamento adiado (%s); a mensagem offset %s será entregue outra vez",
                                        exc, msg.offset)
                            consumer.seek(TopicPartition(msg.topic, msg.partition), msg.offset)
                            time.sleep(1)
                            continue
                        except (ValueError, UnicodeDecodeError):
                            handler({"_raw": msg.value.decode("utf-8", "replace")})   # vai para a DLQ
                        consumer.commit()
                except Exception as exc:  # noqa: BLE001 - Kafka indisponível: tentar de novo
                    log.warning("Kafka indisponível para o consumidor %s (%s); nova tentativa em 3 s", group, exc)
                    time.sleep(3)
        threading.Thread(target=loop, daemon=True, name=f"consumer-{topic}").start()

    def ping(self):
        try:
            self._get_producer().partitions_for(TOPIC_TRADES)
            return True
        except Exception:  # noqa: BLE001
            with self._lock:
                self._producer = None
            return False


_bus = None


def get_bus():
    global _bus
    if _bus is None:
        if os.environ.get("QA_LAB_KAFKA"):
            _bus = KafkaBus(os.environ["QA_LAB_KAFKA"])
        elif os.environ.get("QA_LAB_BUS_FILE"):
            _bus = FileBus(os.environ["QA_LAB_BUS_FILE"])
        else:
            _bus = MemoryBus()
    return _bus
