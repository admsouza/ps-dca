"""Percurso completo: fonte do pedido (`pipeline-percurso-origem-bp`, histórico).

A origem própria do BP no percurso foi removida (`pipeline-consolidado-anterior-soma-unidades`):
o consolidado não tem origem própria, e o percurso reaplica só as escolhas por unidade
(`tests/pipeline/test_rota_anterior_por_recorte.py`). Este arquivo guarda a regressão de fonte,
que é independente disso.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

ENTE = "2505204"
EXERCICIO = 2025
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}
URL = f"/batch-jobs?anReferencia={EXERCICIO}&id_ente={ENTE}"


class FilaFake:
    pendente = None

    def __init__(self):
        self.percursos: list[dict] = []
        self.enfileirados: list = []

    def enfileirar(self, *args, **kwargs):
        self.enfileirados.append((args, kwargs))

    def enfileirar_percurso(self, *args, **kwargs):
        self.percursos.append(kwargs)


@pytest.fixture
def api(repo, lock, jobs, notificador):
    from app.core.config import config
    from app.routes import anexos as rotas
    from app.routes.dependencias import (
        FontePedido,
        fonte_do_pedido,
        repositorio,
        unidade_autorizada,
    )

    fila = FilaFake()
    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo

    def autorizada(request: Request) -> str:
        request.state.poderes = ("consolidado",)   # o que `unidade_autorizada` grava
        return ENTE

    app.dependency_overrides[unidade_autorizada] = autorizada
    # A fonte padrão, como antes da fonte no percurso; `_com_fonte` troca.
    app.dependency_overrides[fonte_do_pedido] = lambda: FontePedido(config().fonte_padrao)
    app.state.portas = {"fila_async": lambda: fila, "lock": lock, "jobs": jobs,
                        "repo_vigencias": None, "base_url": "", "notificador": notificador}
    return TestClient(app, raise_server_exceptions=False), fila


def _com_fonte(api, nome: str, token: str | None = None):
    """O app do fixture com `fonte_do_pedido` fixo (o hub não existe no teste)."""
    from app.routes.dependencias import FontePedido, fonte_do_pedido

    cliente, fila = api
    cliente.app.dependency_overrides[fonte_do_pedido] = lambda: FontePedido(nome, token)
    return cliente, fila


def test_percurso_recusa_origem_consolidada_legada(api):
    """Scenario: percurso recusa origem consolidada"""
    cliente, fila = api

    resposta = cliente.post(f"{URL}&origem_exercicio_anterior=msce_exercicio_anterior", headers=HDR)

    assert resposta.status_code == 422
    assert fila.percursos == []


def test_percurso_apura_pela_fonte_pedida(api, monkeypatch):
    """Scenario: percurso usa a fonte escolhida no front (SIAFIC → publicsoft), não a padrão

    Regressão (Cuitegi 2025-10-14): o percurso apurava sempre pela fonte padrão (SICONFI), com
    recortes por PO, e a leitura pela SIAFIC via o resultado como desatualizado.
    """
    guardados = []
    monkeypatch.setattr("app.infra.fila.credencial.guardar",
                        lambda cofre, *, job_id, token: guardados.append((job_id, token)))
    cliente, fila = _com_fonte(api, "publicsoft", "tk")
    cliente.app.state.portas["cofre"] = object()

    resposta = cliente.post(URL, headers=HDR)

    assert resposta.status_code == 202, resposta.text
    assert fila.percursos[0]["fonte"] == "publicsoft"
    assert guardados == [(resposta.json()["batch_job_id"], "tk")]
    assert "tk" not in str(fila.percursos[0])
