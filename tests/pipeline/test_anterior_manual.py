"""Mapa manual do exercício anterior: corpo do POST, reaplicação e MSC explícita.

O manual é por unidade (`anterior_por_recorte`); o consolidado não tem mapa próprio
(`pipeline-consolidado-anterior-soma-unidades`).
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tests.pipeline.conftest import LockFake

ENTE = "2611606"
EXERCICIO = 2025
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}
OUTRO_ENTE = "2507507"
L17 = "628456869.17"
MANUAL_UG1 = {"ug:1": {"origem": "manual", "valores": {"L17": L17}}}


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


def _cliente(repo, fila, unidade=ENTE):
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo
    if unidade:                                  # `unidade=None` exercita a autorização real

        def _autorizada(request: Request) -> str:
            request.state.poderes = ("consolidado",)
            return unidade

        app.dependency_overrides[unidade_autorizada] = _autorizada
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
    """Scenario: processamento seguinte reaplica o mapa salvo (por unidade)."""
    from app.services.pipeline.cache import parametros_efetivos

    registro = _Registro({"anterior_por_recorte": MANUAL_UG1})
    assert parametros_efetivos({}, registro)["anterior_por_recorte"] == MANUAL_UG1


def test_msc_explicita_nao_reaplica():
    """Scenario: MSC explícita remove o mapa (por unidade, via `padrao`)."""
    from app.services.pipeline.cache import parametros_efetivos

    registro = _Registro({"anterior_por_recorte": MANUAL_UG1})
    efetivo = parametros_efetivos({"anterior_por_recorte": {"ug:1": {"origem": "padrao"}}},
                                  registro)
    assert "anterior_por_recorte" not in efetivo


def test_erro_de_job_conserva_a_procedencia():
    """Scenario: job que falha conserva o mapa."""
    from app.services.pipeline.job import _gravar_erro

    class Repo:
        def __init__(self):
            self.linha = _Registro({"anterior_por_recorte": MANUAL_UG1})
            self.linha.id_ente = ENTE
            self.linha.an_referencia = EXERCICIO
            self.linha.anexo = "BF"

        def obter(self, ente, exercicio, anexo):
            return self.linha

        def gravar(self, registro):
            self.linha = registro

    repo = Repo()
    _gravar_erro(repo, ENTE, EXERCICIO, "BF", "falhou", "0.1.0", "v")
    assert repo.linha.procedencia["anterior_por_recorte"] == MANUAL_UG1
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
        json={"anterior_por_recorte": MANUAL_UG1},
    )
    assert resposta.status_code == 202
    assert fila.chamadas[0]["anterior_por_recorte"] == MANUAL_UG1


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
    """Scenario: linha informada fora do IPC 06 (por unidade)."""
    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _t: {"sub": "u@x", "unidade": ENTE},
    )
    repo = _Repo(_Registro({"anterior_por_recorte": MANUAL_UG1}))
    fila = _Fila()
    resposta = _cliente(repo, fila).post(
        f"/dca/BF/reprocessar?anReferencia={EXERCICIO}",
        headers=HDR,
        json={"anterior_por_recorte": {"ug:1": {"origem": "manual",
                                                "valores": {"L99": "1.00"}}}},
    )
    assert resposta.status_code == 422
    assert "L99" in resposta.json()["detail"]
    assert repo.registro.procedencia["anterior_por_recorte"] == MANUAL_UG1
    assert fila.chamadas == []


def test_percurso_completo_reaplica_o_mapa(monkeypatch):
    """Scenario: percurso completo reaplica o mapa."""
    from app.services.pipeline import apuracao
    from app.services.pipeline.cache import parametros_efetivos
    from tests.recorte.test_anterior_por_recorte import _fonte_bf

    fonte = _fonte_bf()
    monkeypatch.setattr(apuracao, "fonte", lambda *_a, **_k: fonte)
    registro = _Registro({"anterior_por_recorte": {
        "ug:3": {"origem": "manual", "valores": {"L27": "5.00"}}}})
    # É o que o worker monta por anexo no percurso: pedido sem escolha + a procedência gravada.
    apurar = apuracao.apurador("BF", parametros=parametros_efetivos({}, registro))
    resultado = apurar(int(ENTE), EXERCICIO)

    ug3 = resultado.recortes["ug:3"].resultado
    assert ug3.procedencia.escolha_anterior == {"origem": "manual", "valores": {"L27": "5.00"}}
    assert ug3.procedencia.valores_anteriores == {"L27": "5.00"}


def test_post_do_mapa_para_ente_alheio_responde_403(monkeypatch):
    """Scenario: ente não autorizado."""
    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _t: {"sub": "u@x", "unidade": ENTE},
    )
    repo = _Repo(_Registro({"anterior_por_recorte": MANUAL_UG1}))
    fila = _Fila()
    resposta = _cliente(repo, fila, unidade=None).post(
        f"/dca/BF/reprocessar?anReferencia={EXERCICIO}",
        headers={"Authorization": "Bearer t", "X-Unidade-Id": OUTRO_ENTE},
        json={"anterior_por_recorte": {"ug:1": {"origem": "manual", "valores": {"L17": "1.00"}}}},
    )
    assert resposta.status_code == 403
    assert repo.gravados == []
    assert repo.registro.procedencia["anterior_por_recorte"] == MANUAL_UG1
    assert fila.chamadas == []
