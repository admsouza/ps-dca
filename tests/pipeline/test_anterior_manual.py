"""Mapa manual do exercício anterior: corpo do POST, reaplicação e MSC explícita."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.pipeline.conftest import LockFake

ENTE = "2611606"
EXERCICIO = 2025
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}
L17 = "628456869.17"


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


def test_mapa_manual_fica_na_procedencia():
    """Scenario: coluna anterior preenchida manualmente."""
    from app.services.bf.quadro_principal import Anterior, apurar
    from tests.bf.conftest import fonte_com

    resultado = apurar(
        int(ENTE), EXERCICIO,
        fonte_com(a2025={}, e2025={}, a2024={}),
        anterior=Anterior.MANUAL,
        valores_anteriores={"L17": L17},
    )
    assert resultado.procedencia.valores_anteriores == {"L17": L17}
    assert resultado.procedencia.origem_exercicio_anterior == "manual"


def test_pedido_sem_origem_reaplica_o_mapa():
    """Scenario: processamento seguinte reaplica o mapa salvo."""
    from app.services.pipeline.cache import parametros_efetivos

    registro = _Registro({
        "origem_exercicio_anterior": "manual",
        "valores_anteriores": {"L17": L17},
    })
    assert parametros_efetivos({}, registro)["valores_anteriores"] == {"L17": L17}


def test_msc_explicita_nao_reaplica():
    """Scenario: MSC explícita remove o mapa."""
    from app.services.pipeline.cache import parametros_efetivos

    registro = _Registro({
        "origem_exercicio_anterior": "manual",
        "valores_anteriores": {"L17": L17},
    })
    assert parametros_efetivos(
        {"origem_anterior": "msce_exercicio_anterior"}, registro,
    ) == {}


def test_erro_de_job_conserva_a_procedencia():
    """Scenario: job que falha conserva o mapa."""
    from app.services.pipeline.job import _gravar_erro

    class Repo:
        def __init__(self):
            self.linha = _Registro({"valores_anteriores": {"L17": L17},
                                    "origem_exercicio_anterior": "manual"})
            self.linha.id_ente = ENTE
            self.linha.an_referencia = EXERCICIO
            self.linha.anexo = "BF"

        def obter(self, ente, exercicio, anexo):
            return self.linha

        def gravar(self, registro):
            self.linha = registro

    repo = Repo()
    _gravar_erro(repo, ENTE, EXERCICIO, "BF", "falhou", "0.1.0", "v")
    assert repo.linha.procedencia["valores_anteriores"] == {"L17": L17}
    assert repo.linha.resultado is None


def test_post_grava_o_mapa_no_corpo(monkeypatch):
    """Scenario: mapa no corpo é gravado."""
    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _t: {"sub": "u@x", "unidade": ENTE},
    )
    fila = _Fila()
    resposta = _cliente(_Repo(), fila).post(
        f"/dca/BF/reprocessar?anReferencia={EXERCICIO}",
        headers=HDR,
        json={"origem_exercicio_anterior": "manual", "valores_anteriores": {"L17": L17}},
    )
    assert resposta.status_code == 202
    assert fila.chamadas[0]["valores_anteriores"] == {"L17": L17}


def test_get_com_valores_na_query_responde_400(monkeypatch):
    """Scenario: mapa na query é recusado."""
    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _t: {"sub": "u@x", "unidade": ENTE},
    )
    fila = _Fila()
    resposta = _cliente(_Repo(), fila).get(
        f"/dca/BF?anReferencia={EXERCICIO}&valores_anteriores=%7B%22L17%22%3A%22{L17}%22%7D",
        headers=HDR,
    )
    assert resposta.status_code == 400
    assert fila.chamadas == []


def test_codigo_fora_do_ipc_responde_422(monkeypatch):
    """Scenario: linha informada fora do IPC 06."""
    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _t: {"sub": "u@x", "unidade": ENTE},
    )
    repo = _Repo(_Registro({
        "origem_exercicio_anterior": "manual",
        "valores_anteriores": {"L17": L17},
    }))
    fila = _Fila()
    resposta = _cliente(repo, fila).post(
        f"/dca/BF/reprocessar?anReferencia={EXERCICIO}",
        headers=HDR,
        json={"origem_exercicio_anterior": "manual", "valores_anteriores": {"L99": "1.00"}},
    )
    assert resposta.status_code == 422
    assert "L99" in resposta.json()["detail"]
    assert repo.registro.procedencia["valores_anteriores"] == {"L17": L17}
    assert fila.chamadas == []
