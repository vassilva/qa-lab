"""
Configuração partilhada dos testes pytest.

Os três sistemas (Trading, Settlement e simulador T2S) correm no mesmo processo, com bases de dados SQLite
temporárias e o barramento em memória (entrega síncrona). As chamadas HTTP entre serviços são encaminhadas
diretamente para o cliente de teste de cada aplicação. Testes standalone: nunca tocam nos ambientes reais.
"""

import os
import sys
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="qa-lab-tests-")
for var in ("DATABASE_URL", "QA_LAB_KAFKA", "QA_LAB_BUS_FILE", "QA_LAB_CHALLENGE"):
    os.environ.pop(var, None)
os.environ.update(QA_LAB_SQLITE=os.path.join(_TMP, "trading.db"), SETTLEMENT_SQLITE=os.path.join(_TMP, "settlement.db"),
                  QA_LAB_LOG_DIR=os.path.join(_TMP, "logs"), QA_LAB_FILES_DIR=os.path.join(_TMP, "files"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ClientAdapter:
    """Mesma interface do ServiceClient, mas sobre o cliente de teste do Flask (sem rede)."""

    def __init__(self, flask_app):
        self.client = flask_app.test_client()

    def request(self, method, path, json=None, timeout=None):
        r = self.client.open(path, method=method, json=json)
        return r.status_code, r.get_json()


@pytest.fixture(scope="session")
def services():
    from app import server, settlement_service, t2s_simulator
    for a in (server.app, settlement_service.app, t2s_simulator.app):
        a.config["TESTING"] = True
    server.settlement_api = ClientAdapter(settlement_service.app)
    server.t2s_api = settlement_service.settlement.t2s = ClientAdapter(t2s_simulator.app)
    return server, settlement_service, t2s_simulator


@pytest.fixture
def client(services):
    server = services[0]
    with server.app.test_client() as c:
        c.post("/api/reset")
        c.post("/api/business-date", json={"date": "2026-11-02"})   # segunda-feira
        yield c
