"""Percurso completo respeita a origem da coluna anterior do BP (`pipeline-percurso-origem-bp`).

Rota, worker e leitura individual têm de gravar e conferir a mesma identidade de pedido.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tests.pipeline.conftest import RegistroFake

ENTE = "2505204"
EXERCICIO = 2025
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}
MSC, PUBLICADO = "msce_exercicio_anterior", "publicado_siconfi"
PROCESSADO = "processado_exercicio_anterior"
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
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    fila = FilaFake()
    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo
    def autorizada(request: Request) -> str:
        request.state.poderes = ("consolidado",)   # o que `unidade_autorizada` grava
        return ENTE

    app.dependency_overrides[unidade_autorizada] = autorizada
    app.state.portas = {"fila_async": lambda: fila, "lock": lock, "jobs": jobs,
                        "repo_vigencias": None, "base_url": "", "notificador": notificador}
    return TestClient(app, raise_server_exceptions=False), fila


@pytest.fixture(autouse=True)
def _serializador(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.job.para_dados", lambda r: {
        "matriz": r.matriz, "procedencia": r.procedencia, "diagnostico": r.diagnostico})


class Resultado:
    def __init__(self, anexo: str, origem: str):
        from app.services.pipeline import apuracao

        self.matriz = {"L1": {"C1": 1}}
        self.procedencia = {"origem_exercicio_anterior": origem,
                            "versao_regras": apuracao.versao_regras(EXERCICIO, anexo, None)}
        self.diagnostico = {"nao_apuradas": [], "residuos": [], "duracao_ms": 1,
                            "sem_dados": False}


def _gravar_em_cache(repo, anexo: str, origem: str | None):
    """Registro válido na identidade que o percurso confere para o anexo."""
    from app.core.config import config
    from app.services.pipeline import apuracao
    from app.services.pipeline.cache import versao_do_pedido
    from app.services.pipeline.completo import pedido_do_percurso

    versao = versao_do_pedido(apuracao.versao_regras(EXERCICIO, anexo, None), anexo,
                              pedido_do_percurso(None, config().fonte_padrao, anexo, origem))
    repo.gravar(RegistroFake(ENTE, EXERCICIO, anexo, status="ok", resultado={"x": 1},
                             versao_api=apuracao.VERSAO_API, versao_regras=versao))


def test_percurso_envia_a_origem_pedida_ao_job(api):
    """Scenario: percurso grava o BP pela origem pedida"""
    cliente, fila = api
    resposta = cliente.post(f"{URL}&origem_exercicio_anterior={MSC}", headers=HDR)

    assert resposta.status_code == 202, resposta.text
    assert fila.percursos[0]["origem_bp"] == MSC


def test_percurso_sem_origem_mantem_o_padrao(api):
    """Scenario: percurso sem origem mantém o padrão"""
    cliente, fila = api
    assert cliente.post(URL, headers=HDR).status_code == 202
    assert fila.percursos[0]["origem_bp"] == PUBLICADO


@pytest.mark.parametrize("origem", ["manual", "qualquer"])
def test_percurso_recusa_origem_invalida(api, origem):
    """Scenario: origem inválida no percurso"""
    cliente, fila = api
    resposta = cliente.post(f"{URL}&origem_exercicio_anterior={origem}", headers=HDR)

    assert resposta.status_code == 422
    assert fila.percursos == []


def test_bp_em_cache_pela_outra_origem_entra_a_apurar(api, repo):
    """Scenario: cache do BP em outra origem entra a apurar"""
    cliente, _ = api
    for anexo in ("BO", "BF"):
        _gravar_em_cache(repo, anexo, None)
    _gravar_em_cache(repo, "BP", PUBLICADO)

    resposta = cliente.post(f"{URL}&origem_exercicio_anterior={MSC}", headers=HDR)

    estados = {n["anexo"]: n["estado"] for n in resposta.json()["anexos"]}
    assert estados["BP"] == "a_apurar"
    assert estados["BO"] == estados["BF"] == "em_cache"

    mesma = cliente.post(f"{URL}&origem_exercicio_anterior={PUBLICADO}", headers=HDR)
    assert {n["anexo"]: n["estado"] for n in mesma.json()["anexos"]}["BP"] == "em_cache"


@pytest.mark.parametrize("origem", [MSC, PUBLICADO, PROCESSADO])
def test_bo_e_bf_nao_dependem_da_origem_do_bp(origem):
    """Requisito: BO e BF — identidade e resultado inalterados.

    Regressão (Cuitegi 2025-10-14): `processado` do BP vazava para o BF, que falhava com
    "processe 2024 antes" sem o usuário ter escolhido nada no BF.
    """
    from app.services.pipeline.completo import pedido_do_percurso

    for anexo in ("BO", "BF", ""):
        assert pedido_do_percurso(None, "siconfi", anexo, origem) == pedido_do_percurso(
            None, "siconfi", anexo)
    assert pedido_do_percurso(None, "siconfi", "BP", origem)["origem_anterior"] == origem
    assert pedido_do_percurso(None, "siconfi", "BP")["origem_anterior"] == PUBLICADO


def test_percurso_processado_sem_n1_do_bp_recusa_com_409(api):
    """Scenario: processado explícito sem N−1 — no percurso, `409` antes de enfileirar"""
    cliente, fila = api
    resposta = cliente.post(f"{URL}&origem_exercicio_anterior={PROCESSADO}", headers=HDR)

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == f"processe {EXERCICIO - 1} antes"
    assert fila.percursos == []


def test_percurso_processado_com_n1_do_bp_enfileira(api, repo):
    """Scenario: processado no percurso com o BP de N−1 `ok` enfileira"""
    cliente, fila = api
    repo.gravar(RegistroFake(ENTE, EXERCICIO - 1, "BP", status="ok", resultado={"x": 1}))
    resposta = cliente.post(f"{URL}&origem_exercicio_anterior={PROCESSADO}", headers=HDR)

    assert resposta.status_code == 202, resposta.text
    assert fila.percursos[0]["origem_bp"] == PROCESSADO


def test_worker_apura_e_grava_o_bp_na_identidade_que_a_leitura_confere(
        api, repo, lock, jobs, monkeypatch):
    """Scenario: percurso grava o BP pela origem pedida"""
    import worker
    from app.services.pipeline import apuracao

    pedidos: dict[str, dict] = {}

    def apurador(anexo, **kw):
        pedidos[anexo] = kw["parametros"]
        return lambda ente, exercicio: Resultado(anexo, kw["parametros"].get("anterior", "-"))

    class Db:
        def close(self):
            pass

    monkeypatch.setattr("app.core.database.sessao", Db)
    monkeypatch.setattr("app.infra.cache.repositorio.RepositorioCache", lambda _db: repo)
    monkeypatch.setattr("app.infra.cache.vigencias_repo.RepositorioVigencias", lambda _db: None)
    monkeypatch.setattr(apuracao, "apurador", apurador)
    monkeypatch.setattr("app.auth.autorizacao.verificar_jwt",
                        lambda _t: {"sub": "u@x", "unidade": ENTE})

    asyncio.run(worker.apurar_completo({"lock": lock, "jobs": jobs}, job_id="j1", ente=ENTE,
                                       exercicio=EXERCICIO, forcar=True, origem_bp=MSC))

    assert pedidos["BP"]["anterior"] == MSC
    assert "anterior" not in pedidos["BO"] and "origem_anterior" not in pedidos["BF"]
    assert repo.obter(ENTE, EXERCICIO, "BP").procedencia["origem_exercicio_anterior"] == MSC

    cliente, fila = api
    # `use_siconfi=true`: a fonte padrão do percurso (`DATA_SOURCE`) é o SICONFI, e a leitura
    # precisa pedir a mesma para conferir a mesma identidade.
    lida = cliente.get(f"/dca/BP?anReferencia={EXERCICIO}&id_ente={ENTE}&use_siconfi=true"
                       f"&origem_exercicio_anterior={MSC}", headers=HDR)
    assert lida.status_code == 200, lida.text
    assert lida.json()["motivos_desatualizado"] == [], lida.json()["motivos_desatualizado"]
    assert fila.enfileirados == []
