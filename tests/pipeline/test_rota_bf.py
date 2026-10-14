"""`GET /dca/BF` ponta a ponta, com as portas fakes que o resto do pipeline já usa.

Este é o teste que o front espera: a rota responde pelo mesmo contrato do BO, com o corpo que a
serialização comum produz.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

ENTE = "2611606"
EXERCICIO = 2025
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}


class RegistroFake:
    def __init__(self, dados: dict, versao_api: str, versao_regras: str):
        self.ente, self.exercicio, self.anexo = ENTE, EXERCICIO, "BF"
        self.status = "ok"
        self.resultado = dados
        self.versao_api = versao_api
        self.versao_regras = versao_regras
        self.job_id = None
        self.atualizado_em = None
        self.duracao_ms = 1
        self.erro = None


class RepoFake:
    def __init__(self, registro=None):
        self.registro = registro
        self.gravados: list[Any] = []

    def obter(self, ente, exercicio, anexo):
        return self.registro

    def gravar(self, registro):
        self.gravados.append(registro)


@pytest.fixture
def cliente(monkeypatch):
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    monkeypatch.setattr("app.auth.autorizacao.verificar_jwt",
                        lambda _t: {"sub": "u@x", "unidade": ENTE})

    class FilaFake:
        """Mesma forma da fila async que a rota espera: `enfileirar` e `pendente`."""

        pendente = None

        async def enfileirar(self, **_):
            return "job-1"

    def _autorizada(request: Request) -> str:
        request.state.poderes = ("consolidado",)   # BF também lê por recorte (fail closed)
        return ENTE

    def _montar(repo):
        app = FastAPI()
        app.include_router(rotas.router)
        app.dependency_overrides[repositorio] = lambda: repo
        app.dependency_overrides[unidade_autorizada] = _autorizada
        app.state.portas = {"fila_async": FilaFake, "lock": None, "jobs": None,
                            "repo_vigencias": None, "base_url": ""}
        return TestClient(app, raise_server_exceptions=False)

    return _montar


def test_rota_do_bf_serve_o_resultado_em_cache(cliente):
    """Scenario: a rota do BF responde"""
    from app.services.bf.quadro_principal import apurar
    from app.services.pipeline.apuracao import VERSAO_API, versao_regras
    from app.services.pipeline.cache import versao_do_pedido
    from app.services.pipeline.resultado import para_dados
    from tests.bf.conftest import fonte_com

    resultado = apurar(int(ENTE), EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={}))
    # Sem `use_siconfi` o pedido é PublicSoft (como RREO/RGF), e a fonte entra na identidade.
    versao = versao_do_pedido(versao_regras(EXERCICIO, "BF"), "BF", {"fonte": "publicsoft"})
    registro = RegistroFake(para_dados(resultado), VERSAO_API, versao)

    resposta = cliente(RepoFake(registro)).get(f"/dca/BF?anReferencia={EXERCICIO}", headers=HDR)

    assert resposta.status_code == 200
    corpo = resposta.json()
    linhas = corpo["resultado"]["linhas"] if "resultado" in corpo else corpo["linhas"]
    assert len(linhas) == 80, "66 do quadro principal e 14 do anexo"
    assert linhas[0]["codigo"] == "L1" and linhas[0]["grupo"] == "INGRESSOS"


def test_grafias_do_bf_apontam_o_mesmo_anexo(cliente):
    """Requisito: `bf`, `B-F` e `BF` são o mesmo anexo, sem fragmentar o cache."""
    from app.services.pipeline.registry import validar_anexo

    assert {validar_anexo(g) for g in ("bf", "BF", "B-F", "b_f")} == {"BF"}


def test_bf_deixa_de_aparecer_como_anexo_sem_servico():
    """Requisito: o resumo não reporta o BF como `sem_cache` por falta de serviço."""
    from app.services.pipeline.registry import implementado

    assert implementado("BF")


def test_valores_na_query_sao_recusados():
    """Scenario: mapa na query é recusado."""
    from fastapi import HTTPException

    from app.routes.anexos import _parametros_bf

    assert _parametros_bf("BF", None, None) == {}
    assert _parametros_bf("BF", "msce_exercicio_anterior", None) == {
        "origem_anterior": "msce_exercicio_anterior",
    }
    with pytest.raises(HTTPException) as erro:
        _parametros_bf("BF", "manual", '{"L2": "1.00"}')
    assert erro.value.status_code == 400
    with pytest.raises(HTTPException) as erro_bo:
        _parametros_bf("BO", None, '{"L2": "1.00"}')
    assert erro_bo.value.status_code == 400
