"""Mapa G8 do exercício atual: corpo do POST, reaplicação e limpeza."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.pipeline.conftest import LockFake

ENTE = "2611606"
EXERCICIO = 2025
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}
L22 = "1234567.89"


class _Registro:
    def __init__(self, procedencia=None):
        self.procedencia = procedencia
        self.status = "ok"
        self.resultado = {"linhas": []}
        self.versao_api = "0.1.0"
        self.versao_regras = "outra"


class _Repo:
    def __init__(self, registro=None):
        self.registro = registro
        self.gravados = []

    def obter(self, ente, exercicio, anexo):
        return self.registro

    def gravar(self, registro):
        self.gravados.append(registro)
        self.registro = registro


class _Fila:
    pendente = None

    def __init__(self):
        self.chamadas = []

    def enfileirar(self, ente, exercicio, anexo, job_id, **kwargs):
        self.chamadas.append({"ente": ente, "exercicio": exercicio, "anexo": anexo,
                              "job_id": job_id, **kwargs})


def _cliente(repo, fila):
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo
    app.dependency_overrides[unidade_autorizada] = lambda: ENTE
    app.state.portas = {
        "fila_async": lambda: fila,
        "lock": LockFake(),
        "jobs": None,
        "repo_vigencias": None,
        "base_url": "",
    }
    return TestClient(app, raise_server_exceptions=False)


def test_post_grava_o_mapa_g8_no_corpo(monkeypatch):
    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _t: {"sub": "u@x", "unidade": ENTE},
    )
    fila = _Fila()
    resposta = _cliente(_Repo(), fila).post(
        f"/dca/BF/reprocessar?anReferencia={EXERCICIO}",
        headers=HDR,
        json={"valores_sem_mapeamento": {"L22": L22}},
    )
    assert resposta.status_code == 202
    assert fila.chamadas[0]["valores_sem_mapeamento"] == {"L22": L22}


def test_query_com_mapa_g8_responde_400(monkeypatch):
    """Scenario: mapa G8 na query é recusado."""
    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _t: {"sub": "u@x", "unidade": ENTE},
    )
    fila = _Fila()
    resposta = _cliente(_Repo(), fila).get(
        f"/dca/BF?anReferencia={EXERCICIO}&valores_sem_mapeamento=%7B%22L22%22%3A%22{L22}%22%7D",
        headers=HDR,
    )
    assert resposta.status_code == 400
    assert fila.chamadas == []


def test_codigo_fora_de_g8_no_corpo_responde_422(monkeypatch):
    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _t: {"sub": "u@x", "unidade": ENTE},
    )
    repo = _Repo(_Registro({"valores_sem_mapeamento": {"L22": L22}}))
    fila = _Fila()
    resposta = _cliente(repo, fila).post(
        f"/dca/BF/reprocessar?anReferencia={EXERCICIO}",
        headers=HDR,
        json={"valores_sem_mapeamento": {"L17": "1.00"}},
    )
    assert resposta.status_code == 422
    assert "L17" in resposta.json()["detail"]
    assert repo.registro.procedencia["valores_sem_mapeamento"] == {"L22": L22}
    assert fila.chamadas == []


def test_pedido_sem_o_mapa_reaplica_o_salvo():
    """Scenario: GET seguinte reaplica o mapa G8."""
    from app.services.pipeline.cache import parametros_efetivos

    registro = _Registro({"valores_sem_mapeamento": {"L22": L22}})
    assert parametros_efetivos({}, registro)["valores_sem_mapeamento"] == {"L22": L22}


def test_mapa_vazio_limpa_o_override():
    from app.services.pipeline.cache import parametros_efetivos

    registro = _Registro({"valores_sem_mapeamento": {"L22": L22}})
    efetivo = parametros_efetivos({"valores_sem_mapeamento": {}}, registro)
    assert "valores_sem_mapeamento" not in efetivo


def test_independente_de_origem_exercicio_anterior():
    """Requisito: o G8 reaplica independente do mapa manual legado do consolidado, que não existe
    mais (`pipeline-consolidado-anterior-soma-unidades`)."""
    from app.services.pipeline.cache import parametros_efetivos

    registro = _Registro({"origem_exercicio_anterior": "manual",
                          "valores_anteriores": {"L17": "1.00"},
                          "valores_sem_mapeamento": {"L22": L22}})
    efetivo = parametros_efetivos({}, registro)
    assert "valores_anteriores" not in efetivo
    assert efetivo["valores_sem_mapeamento"] == {"L22": L22}
