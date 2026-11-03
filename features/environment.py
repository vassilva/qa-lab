"""
BDD test setup (behave).

The scenarios run against a running environment, through the REST API:
    BASE_URL (default http://localhost:8000)

Protection: the scenarios reset the environment before each test, so the framework
REFUSES to run against any environment other than QA or LOCAL (never UAT).
"""

import os
import time

import requests

ALLOWED_ENVIRONMENTS = {"QA", "LOCAL"}


class Api:
    """Small QA Lab API client shared by the steps."""

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
        assert r.status_code == 200, f"Query failed ({r.status_code}): {r.text}"
        return r.json()["rows"]


def before_all(context):
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    context.api = Api(base_url)
    try:
        health = context.api.get("/health").json()
    except requests.RequestException as exc:
        raise RuntimeError(f"The environment {base_url} does not respond: {exc}") from exc

    environment = str(health.get("environment", "")).upper()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            f"The BDD scenarios reset the data and may only run in QA or LOCAL. "
            f"The environment {base_url} is {environment}: run cancelled to protect it."
        )
    print(f"BDD against {base_url} · environment {environment} · version {health.get('version')} "
          f"· database {health.get('database')}")
    context.cleanup_allowed = True     # only after confirming this is NOT UAT

    # Readiness (DEF-015): do not start until Settlement can receive trades (Kafka partition assigned)
    deadline = time.time() + 90
    while not context.api.get("/api/integration").json().get("settlement", {}).get("consumer_ready"):
        if time.time() > deadline:
            raise RuntimeError("The Settlement consumer is not ready after 90 s (no Kafka partition assigned)")
        time.sleep(1)
    print("Settlement consumer ready")


def before_scenario(context, scenario):
    context.orders = {}          # alias used in the scenario (e.g. "S1") → order returned by the API
    context.last_response = None
    context.trade = None


def after_all(context):
    """Leaves the environment as it was before the tests: no test data and today's business date."""
    if not getattr(context, "cleanup_allowed", False):
        return                              # protected environment (e.g. UAT): never clean up
    try:
        context.api.post("/api/reset")
    except Exception as exc:  # noqa: BLE001 - do not hide the test result because of the cleanup
        print(f"Warning: could not clean up the environment after the tests: {exc}")
