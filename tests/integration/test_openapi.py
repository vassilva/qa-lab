"""Teste de contrato das APIs: todas as rotas da API estão documentadas no OpenAPI, e o OpenAPI não tem rotas fantasma."""

import os
import re

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES = {"/", "/checklist", "/docs/", "/docs/<path:name>", "/docs-raw/<path:name>", "/reports/", "/reports/<path:name>",
         "/static/<path:filename>"}


def _routes(flask_app):
    out = set()
    for rule in flask_app.url_map.iter_rules():
        if rule.rule in PAGES:
            continue
        path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule)
        out |= {(m.lower(), path) for m in rule.methods - {"HEAD", "OPTIONS"}}
    return out


def _spec(name):
    with open(os.path.join(ROOT, "contracts", name), encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    return {(m, p) for p, ops in spec["paths"].items() for m in ops}


@pytest.mark.parametrize("module, spec_file", [("server", "trading.openapi.yaml"),
                                               ("settlement_service", "settlement.openapi.yaml"),
                                               ("t2s_simulator", "t2s-simulator.openapi.yaml")])
def test_openapi_cobre_todas_as_rotas(services, module, spec_file):
    from importlib import import_module
    routes, spec = _routes(import_module(f"app.{module}").app), _spec(spec_file)
    assert routes - spec == set(), f"Rotas sem documentação OpenAPI: {sorted(routes - spec)}"
    assert spec - routes == set(), f"Rotas documentadas que não existem: {sorted(spec - routes)}"
