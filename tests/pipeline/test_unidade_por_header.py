"""O SSE/polling de job manda a unidade só no header `X-Unidade-Id` (util compartilhado do front)."""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.routes.dependencias import unidade_autorizada


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr("app.auth.autorizacao.verificar_jwt",
                        lambda _t: {"sub": "u@x", "unidade": "2507507"})
    app = FastAPI()

    @app.get("/eco")
    def eco(ente: str = __import__("fastapi").Depends(unidade_autorizada)) -> dict:
        return {"ente": ente}

    return TestClient(app, raise_server_exceptions=False)


HDR = {"Authorization": "Bearer t", "X-Unidade-Id": "2507507"}


def test_unidade_apenas_no_header(cliente):
    r = cliente.get("/eco", headers=HDR)
    assert r.status_code == 200 and r.json()["ente"] == "2507507"


def test_query_e_header_divergentes(cliente):
    assert cliente.get("/eco?id_ente=1111111", headers=HDR).status_code == 400


def test_sem_query_e_sem_header(cliente):
    assert cliente.get("/eco", headers={"Authorization": "Bearer t"}).status_code == 400
