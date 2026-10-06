"""Change `pipeline-fonte-por-pedido`: `use_siconfi` escolhe a fonte; `token_ps` vem do hub.

Mesmo desenho de `regras-rgf-api` (`resolve_publicsoft_auth`): `Query(False)`, token resolvido no
hub, cifrado no cofre por job, nunca no payload da fila.
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

ENTE = "2505204"
EXERCICIO = 2025
TOKEN = "token-ps-cuitegi"
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}


class FilaFake:
    """Fila async da rota. Guarda o payload, para afirmar o que vai — e o que não vai — nele."""

    enfileirados: list[dict] = []
    pendente = None

    def enfileirar(self, ente, exercicio, anexo, job_id, **parametros):
        FilaFake.enfileirados.append({"ente": ente, "anexo": anexo, "job_id": job_id,
                                      **parametros})


class CofreFake:
    def __init__(self):
        self.valores: dict[str, str] = {}

    def gravar(self, chave: str, valor: str, ttl: int) -> None:
        self.valores[chave] = valor

    def obter(self, chave: str) -> str | None:
        return self.valores.get(chave)


class LockLivre:
    def adquirir(self, *_a, **_k):
        return True

    def liberar(self, *_a, **_k):
        return None

    def dono(self, *_a, **_k):
        return None


class RepoFake:
    def __init__(self, registro=None):
        self.registro = registro

    def obter(self, ente, exercicio, anexo):
        return self.registro

    def gravar(self, registro):
        self.registro = registro


class Registro:
    def __init__(self, versao_api, versao_regras):
        self.status = "ok"
        self.resultado = {"linhas": [], "matriz": {}}
        self.versao_api = versao_api
        self.versao_regras = versao_regras
        self.procedencia = None
        self.erro_detalhe = None
        self.solicitado_por = None


@pytest.fixture(autouse=True)
def _chave_do_cofre(monkeypatch):
    from cryptography.fernet import Fernet

    from app.core.config import config

    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    config.cache_clear()
    FilaFake.enfileirados = []
    yield
    config.cache_clear()


@pytest.fixture
def hub(monkeypatch):
    """Hub configurado, com `resolve-tenant` controlável pelo teste."""
    from app.auth import hub as modulo

    estado: dict[str, Any] = {"chamadas": [], "erro": None}

    async def resolver_token(self, sub, cod_ibge):
        estado["chamadas"].append((sub, cod_ibge))
        if estado["erro"] is not None:
            raise estado["erro"]
        return TOKEN

    monkeypatch.setattr(modulo.AutorizadorHub, "configurado", property(lambda self: True))
    monkeypatch.setattr(modulo.AutorizadorHub, "resolver_token", resolver_token)
    return estado


@pytest.fixture
def cliente():
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    def _montar(repo=None, cofre=None):
        app = FastAPI()
        app.include_router(rotas.router)
        app.dependency_overrides[repositorio] = lambda: repo or RepoFake()

        def _unidade(request: Request) -> str:
            request.state.claims = {"sub": "u@x"}
            return ENTE

        app.dependency_overrides[unidade_autorizada] = _unidade
        app.state.portas = {"fila_async": FilaFake, "lock": LockLivre(), "jobs": None,
                            "repo_vigencias": None, "cofre": cofre or CofreFake()}
        return TestClient(app, raise_server_exceptions=False)

    return _montar


def _get(cliente, query: str = "", **montar):
    return cliente(**montar).get(f"/dca/BF?anReferencia={EXERCICIO}&id_ente={ENTE}{query}",
                                 headers=HDR)


# --- Requirement: Fonte de dados escolhida por pedido ---------------------------------------

def test_siafic_escolhido_vai_publicsoft_no_job(cliente, hub):
    """Scenario: SIAFIC escolhido com worker padrão SICONFI."""
    resposta = _get(cliente, "&use_siconfi=false")

    assert resposta.status_code == 202, resposta.text
    assert FilaFake.enfileirados[0]["fonte"] == "publicsoft"


def test_siconfi_escolhido_nao_resolve_credencial(cliente, hub):
    """Scenario: SICONFI escolhido."""
    cofre = CofreFake()
    resposta = _get(cliente, "&use_siconfi=true", cofre=cofre)

    assert resposta.status_code == 202, resposta.text
    assert FilaFake.enfileirados[0]["fonte"] == "siconfi"
    assert hub["chamadas"] == []
    assert cofre.valores == {}


def test_pedido_sem_fonte_vale_publicsoft(cliente, hub):
    """Scenario: pedido sem fonte."""
    resposta = _get(cliente)

    assert resposta.status_code == 202, resposta.text
    assert FilaFake.enfileirados[0]["fonte"] == "publicsoft"


def test_troca_de_fonte_nao_serve_o_cache_da_outra(cliente, hub):
    """Scenario: troca de fonte não serve o cache da outra."""
    from app.services.pipeline.apuracao import VERSAO_API, versao_regras
    from app.services.pipeline.cache import versao_do_pedido

    siconfi = versao_do_pedido(versao_regras(EXERCICIO, "BF"), "BF", {"fonte": "siconfi"})
    repo = RepoFake(Registro(VERSAO_API, siconfi))

    assert _get(cliente, "&use_siconfi=true", repo=repo).status_code == 200
    assert _get(cliente, "&use_siconfi=false", repo=repo).status_code == 202


def test_use_siconfi_invalido(cliente, hub):
    """Scenario: parâmetro inválido."""
    resposta = _get(cliente, "&use_siconfi=talvez")

    assert resposta.status_code == 422
    assert FilaFake.enfileirados == []


def test_parametros_efetivos_preservam_a_fonte():
    """Requisito: Fonte de dados escolhida por pedido — a fonte entra na identidade."""
    from app.services.pipeline.cache import parametros_efetivos

    assert parametros_efetivos({"fonte": "publicsoft"}, None)["fonte"] == "publicsoft"


# --- Requirement: Credencial PublicSoft resolvida no servidor -------------------------------

def test_token_guardado_cifrado_e_fora_do_payload(cliente, hub):
    """Scenario: token guardado para o job."""
    from app.infra.fila.credencial import ler

    cofre = CofreFake()
    resposta = _get(cliente, "&use_siconfi=false", cofre=cofre)

    assert resposta.status_code == 202, resposta.text
    job = FilaFake.enfileirados[0]
    assert TOKEN not in str(job), "token no payload da fila"
    assert TOKEN not in str(cofre.valores), "token em claro no cofre"
    assert ler(cofre, job_id=job["job_id"]) == TOKEN
    assert hub["chamadas"] == [("u@x", ENTE)]


@pytest.mark.parametrize(("erro", "status_http"), [
    ("SemAcessoAUnidade", 403),
    ("EnteNaoEncontrado", 404),
    ("EnteSemToken", 409),
    ("HubIndisponivel", 503),
])
def test_falha_do_hub_nao_cria_job(cliente, hub, erro, status_http):
    """Scenario: ente inexistente no hub / ente sem token_ps / hub indisponível."""
    from app.auth import hub as modulo

    hub["erro"] = getattr(modulo, erro)("x")
    resposta = _get(cliente, "&use_siconfi=false")

    assert resposta.status_code == status_http
    assert FilaFake.enfileirados == []


@pytest.mark.parametrize(("status_hub", "corpo", "esperado"), [
    (200, {"token_ps": TOKEN}, TOKEN),
    (403, {}, "SemAcessoAUnidade"),
    (404, {}, "EnteNaoEncontrado"),
    (409, {}, "EnteSemToken"),
    (401, {}, "HubIndisponivel"),
    (500, {}, "HubIndisponivel"),
    (200, {}, "EnteSemToken"),
])
def test_resolver_token_no_hub(status_hub, corpo, esperado):
    """Requisito: Credencial PublicSoft resolvida no servidor — contrato do RGF."""
    from app.auth import hub as modulo

    chamadas = []

    async def http(url, json, headers):
        chamadas.append((url, json, headers))
        return {"status": status_hub, "corpo": corpo}

    autorizador = modulo.AutorizadorHub(base_url="http://hub", secret="s", http=http)
    if esperado == TOKEN:
        assert asyncio.run(autorizador.resolver_token("u@x", ENTE)) == TOKEN
    else:
        with pytest.raises(getattr(modulo, esperado)):
            asyncio.run(autorizador.resolver_token("u@x", ENTE))
    assert chamadas[0] == ("http://hub/internal/resolve-tenant",
                           {"sub": "u@x", "cod_ibge": ENTE}, {"X-Internal-Secret": "s"})


def test_resolver_token_rede_fora():
    """Scenario: hub indisponível."""
    from app.auth import hub as modulo

    async def http(url, json, headers):
        raise OSError("conexão recusada")

    autorizador = modulo.AutorizadorHub(base_url="http://hub", secret="s", http=http)
    with pytest.raises(modulo.HubIndisponivel):
        asyncio.run(autorizador.resolver_token("u@x", ENTE))


# --- Worker ---------------------------------------------------------------------------------

@pytest.mark.parametrize("anexo", ["BF", "BO"])
def test_apurador_real_aceita_fonte_no_payload(monkeypatch, anexo):
    """Scenario: SIAFIC escolhido com worker padrão SICONFI — `fonte` não vaza ao serviço.

    Regressão de produção (2026-10-06): `apurar() got multiple values for keyword argument 'fonte'`.
    """
    from app.services.pipeline import apuracao

    recebidos: dict[str, Any] = {}

    def servico(ente, exercicio, fonte=None, mapa=None, **kwargs):
        recebidos.update(fonte=fonte, **kwargs)

    monkeypatch.setattr(apuracao, "_servico_de", lambda _codigo: servico)
    monkeypatch.setattr(apuracao, "mapa_vigente", lambda *_a, **_k: None)

    apuracao.apurador(anexo, fonte_nome="siconfi",
                      parametros={"fonte": "siconfi"})(int(ENTE), EXERCICIO)

    assert recebidos["fonte"].__class__.__name__ == "_NoEscopo"

def test_worker_apura_na_fonte_do_payload(monkeypatch):
    """Scenario: SIAFIC escolhido com worker padrão SICONFI — o job apura pela fonte do payload."""
    # `worker` chama `load_dotenv()` na importação; o `.env` local vazaria para os outros testes.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *_a, **_k: False)
    import worker
    from app.services.pipeline import apuracao

    pedidos: dict[str, Any] = {}

    def apurador(anexo, **kwargs):
        pedidos.update(kwargs)
        return lambda *_: None

    class Sessao:
        def close(self):
            return None

    monkeypatch.setattr("app.core.database.sessao", Sessao)
    monkeypatch.setattr(apuracao, "apurador", apurador)
    monkeypatch.setattr(apuracao, "versao_regras", lambda *_a, **_k: "v")
    monkeypatch.setattr("app.services.pipeline.job.executar", lambda **_: None)

    asyncio.run(worker.apurar_anexo({"lock": None, "jobs": None}, job_id="j1", ente=ENTE,
                                    exercicio=EXERCICIO, anexo="BF", fonte="publicsoft"))

    assert pedidos["fonte_nome"] == "publicsoft"


def test_publicsoft_envia_token_e_responsavel():
    """Scenario: token guardado para o job — com `x-responsavel-contabilidade`, como RREO/RGF.

    Regressão de produção (2026-10-06): `401` em `/matriz-saldo/auditorias` sem esse header.
    """
    from app.infra.msc.publicsoft import PublicSoftMSC

    chamadas = []

    def http(url, params=None, headers=None, timeout=None):
        chamadas.append(headers)
        return {"status": "validado", "podeGerar": True}

    PublicSoftMSC(http=http, token=TOKEN, url_auditoria="https://api/auditorias",
                  responsavel="resp")._consultar_auditoria(2025, 13)

    assert chamadas == [{"x-authorization": TOKEN, "x-responsavel-contabilidade": "resp"}]
