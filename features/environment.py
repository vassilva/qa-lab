"""
Configuração dos testes BDD (behave).

Os cenários correm contra um ambiente em execução, através da API REST:
    BASE_URL (por omissão http://localhost:8000)

Proteção: os cenários reiniciam o ambiente antes de cada teste, por isso o framework
RECUSA correr num ambiente que não seja QA ou LOCAL (nunca em UAT).
"""

import os

import requests

ALLOWED_ENVIRONMENTS = {"QA", "LOCAL"}


class Api:
    """Pequeno cliente da API do QA Lab, partilhado pelos passos."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def get(self, path, **kwargs):
        return self.session.get(self.base_url + path, timeout=10, **kwargs)

    def post(self, path, json=None):
        return self.session.post(self.base_url + path, json=json, timeout=10)

    def delete(self, path):
        return self.session.delete(self.base_url + path, timeout=10)

    def query(self, sql):
        r = self.post("/api/query", {"sql": sql})
        assert r.status_code == 200, f"Query falhou ({r.status_code}): {r.text}"
        return r.json()["rows"]


def before_all(context):
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    context.api = Api(base_url)
    try:
        health = context.api.get("/health").json()
    except requests.RequestException as exc:
        raise RuntimeError(f"O ambiente {base_url} não responde: {exc}") from exc

    environment = str(health.get("environment", "")).upper()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            f"Os cenários BDD reiniciam os dados e só podem correr em QA ou LOCAL. "
            f"O ambiente {base_url} é {environment}: execução cancelada para o proteger."
        )
    print(f"BDD contra {base_url} · ambiente {environment} · versão {health.get('version')} "
          f"· base de dados {health.get('database')}")


def before_scenario(context, scenario):
    context.orders = {}          # alias usado no cenário (ex.: "V1") → ordem devolvida pela API
    context.last_response = None
    context.trade = None
