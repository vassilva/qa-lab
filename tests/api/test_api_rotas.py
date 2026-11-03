"""Rotas da API e das páginas que não eram exercidas pelos fluxos de negócio (melhoria de cobertura, ver 3.1)."""

import pytest


def _order(client, side, qty, price, symbol="EDP"):
    return client.post("/api/orders", json={"symbol": symbol, "side": side, "qty": qty, "price": price})


@pytest.mark.parametrize("path", ["/", "/checklist", "/docs/", "/docs/qa/estrategia-de-testes.md", "/api/checklist",
                                  "/docs-raw/qa/matriz-de-risco.md", "/api/symbols"])
def test_paginas_e_recursos_respondem(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs/qa/nao-existe.md", "/docs/qa/estrategia-de-testes.txt",
                                  "/docs-raw/../app/server.py", "/api/orders/O99999"])
def test_recursos_inexistentes_devolvem_404(client, path):
    assert client.get(path).status_code == 404


def test_cancelar_ordem_no_livro(client):
    order_id = _order(client, "BUY", 100, 4.40).get_json()["order"]["order_id"]
    r = client.delete(f"/api/orders/{order_id}")
    assert r.status_code == 200 and r.get_json()["order"]["status"] == "CANCELLED"
    assert client.get("/api/book/EDP").get_json()["bids"] == []
    assert client.delete(f"/api/orders/{order_id}").status_code == 409


def test_filtros_de_ordens_e_negocios(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    _order(client, "BUY", 10_001, 4.50)
    assert len(client.get("/api/orders?status=FILLED").get_json()) == 2
    assert len(client.get("/api/orders?status=REJECTED").get_json()) == 1
    assert len(client.get("/api/trades?symbol=EDP").get_json()) == 1
    assert client.get("/api/trades?symbol=GALP").get_json() == []


def test_filtro_de_instrucoes_por_estado(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    assert len(client.get("/api/settlement/instructions?status=PENDING").get_json()) == 1
    assert client.get("/api/settlement/instructions?status=SETTLED").get_json() == []


@pytest.mark.parametrize("body", [{"date": "06-11-2026"}, {"date": ""}, {}])
def test_data_de_negocio_com_formato_invalido(client, body):
    assert client.post("/api/business-date", json=body).status_code == 400


def test_acao_de_liquidacao_invalida(client):
    assert client.post("/api/settlement/instructions/S00001/apagar").status_code == 400


def test_release_de_instrucao_que_nao_esta_retida(client):
    _order(client, "SELL", 100, 4.50)
    _order(client, "BUY", 100, 4.50)
    assert client.post("/api/settlement/instructions/S00001/release").status_code == 409


def test_consola_sql_com_erro_de_sintaxe(client):
    r = client.post("/api/query", json={"sql": "SELECT coluna_que_nao_existe FROM orders"})
    assert r.status_code == 400 and "error" in r.get_json()


def test_health_indica_ambiente_e_versao(client):
    body = client.get("/health").get_json()
    assert {"environment", "version", "database", "challenge_mode"} <= body.keys()


def test_indice_da_documentacao(client):
    items = client.get("/api/docs").get_json()
    paths = {i["path"] for i in items}
    assert {"qa/estrategia-de-testes.md", "defeitos/README.md", "tecnico/git.md"} <= paths
    assert all(i["title"] for i in items)
