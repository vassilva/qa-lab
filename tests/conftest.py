"""Configuração partilhada dos testes pytest: base de dados e logs temporários (SQLite)."""

import os
import sys
import tempfile

import pytest

# Testes standalone: nunca tocam na base de dados do ambiente (mesmo dentro do contentor de QA/UAT)
_TMP = tempfile.mkdtemp(prefix="qa-lab-tests-")
os.environ.pop("DATABASE_URL", None)
os.environ["QA_LAB_SQLITE"] = os.path.join(_TMP, "test.db")
os.environ["QA_LAB_LOG_DIR"] = os.path.join(_TMP, "logs")
os.environ.pop("QA_LAB_CHALLENGE", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    from app import server
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        c.post("/api/reset")
        c.post("/api/business-date", json={"date": "2026-11-02"})   # segunda-feira
        yield c
