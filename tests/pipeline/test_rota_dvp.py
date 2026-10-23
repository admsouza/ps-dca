"""`GET /dca/I-HI` ponta a ponta, com as portas fakes que o resto do pipeline já usa."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tests.pipeline.conftest import LockFake

ENTE = "2507507"
EXERCICIO = 2025
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}


class RegistroFake:
    def __init__(self, dados: dict, versao_api: str, versao_regras: str):
        self.ente, self.exercicio, self.anexo = ENTE, EXERCICIO, "I-HI"
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


class FilaFake:
    pendente = None

    def __init__(self):
        self.chamadas: list[dict] = []

    def enfileirar(self, ente, exercicio, anexo, job_id, **kwargs):
        self.chamadas.append({"ente": ente, "exercicio": exercicio, "anexo": anexo, **kwargs})


@pytest.fixture
def cliente(monkeypatch):
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    monkeypatch.setattr("app.auth.autorizacao.verificar_jwt",
                        lambda _t: {"sub": "u@x", "unidade": ENTE})

    def _autorizada(request: Request) -> str:
        request.state.poderes = ("consolidado",)
        return ENTE

    def _montar(repo, fila=None):
        fila = fila or FilaFake()
        app = FastAPI()
        app.include_router(rotas.router)
        app.dependency_overrides[repositorio] = lambda: repo
        app.dependency_overrides[unidade_autorizada] = _autorizada
        app.state.portas = {"fila_async": lambda: fila, "lock": LockFake(), "jobs": None,
                            "repo_vigencias": None, "base_url": ""}
        return TestClient(app, raise_server_exceptions=False)

    return _montar


def test_rota_da_dvp_serve_o_resultado_em_cache(cliente):
    """Scenario: VPA antes de VPD, resultado por último"""
    from app.services.dvp.quadro_principal import apurar
    from app.services.pipeline.apuracao import VERSAO_API, versao_regras
    from app.services.pipeline.cache import versao_do_pedido
    from app.services.pipeline.resultado import para_dados
    from tests.bp.conftest import FontePorAno

    resultado = apurar(int(ENTE), EXERCICIO, FontePorAno({}))
    versao = versao_do_pedido(versao_regras(EXERCICIO, "I-HI"), "I-HI", {"fonte": "publicsoft"})
    registro = RegistroFake(para_dados(resultado), VERSAO_API, versao)

    resposta = cliente(RepoFake(registro)).get(f"/dca/I-HI?anReferencia={EXERCICIO}", headers=HDR)

    assert resposta.status_code == 200
    corpo = resposta.json()
    linhas = corpo["resultado"]["linhas"] if "resultado" in corpo else corpo["linhas"]
    assert len(linhas) == 19
    assert linhas[0]["codigo"] == "L1" and linhas[0]["grupo"] == "VPA"
    assert linhas[-1]["codigo"] == "L19" and linhas[-1]["grupo"] == "RESULTADO"


def test_reprocessar_a_dvp_enfileira(cliente):
    """Requisito: `POST /dca/I-HI/reprocessar` responde 202 e enfileira o anexo canônico."""
    fila = FilaFake()
    resposta = cliente(RepoFake(), fila).post(
        f"/dca/i-hi/reprocessar?anReferencia={EXERCICIO}", headers=HDR)

    assert resposta.status_code == 202, resposta.text
    assert fila.chamadas and fila.chamadas[0]["anexo"] == "I-HI"


def _dvp_gravada() -> dict:
    from tests.recorte.test_dvp_por_unidade import N, _dvp, _fonte, para_dados

    return para_dados(_dvp(_fonte(N)))


def _cliente_recorte(repo, lock, jobs, poderes):
    from tests.pipeline.test_rota_recorte import _cliente

    return _cliente(repo, lock, jobs, poderes, anexo="I-HI", resultado=_dvp_gravada())


def _get_recorte(cliente, query: str = ""):
    from tests.pipeline.test_rota_recorte import _get

    return _get(cliente, "I-HI", query)


def test_leitura_de_recorte_nao_enfileira(repo, lock, jobs):
    """Scenario: leitura de recorte não enfileira"""
    r = _get_recorte(_cliente_recorte(repo, lock, jobs, ["consolidado"]), "&recorte=ug:4")

    assert r.status_code == 200
    corpo = r.json()
    ids = {linha["codigo"]: linha["rule_id"] for linha in corpo["linhas"]}
    assert corpo["recorte"] == "ug:4" and corpo["matriz"][ids["L2"]]["exercicio_atual"] == "40.00"


def test_recorte_malformado_na_dvp(repo, lock, jobs):
    """Scenario: recorte malformado"""
    cliente = _cliente_recorte(repo, lock, jobs, ["consolidado"])
    assert _get_recorte(cliente, "&recorte=ug").status_code == 422
    assert _get_recorte(cliente, "&recorte=99").status_code == 422


def test_unidade_fora_do_poder_do_usuario_na_dvp(repo, lock, jobs):
    """Scenario: unidade fora do poder do usuário"""
    cliente = _cliente_recorte(repo, lock, jobs, ["legislativo"])
    assert _get_recorte(cliente, "&recorte=ug:1").status_code == 403
    assert _get_recorte(cliente, "&recorte=ug:4").status_code == 200


def test_resumo_publica_os_recortes_da_dvp(repo, lock, jobs):
    """Scenario: resumo publica os recortes da DVP"""
    from tests.pipeline.test_rota_recorte import _entrada, _resumo

    r = _resumo(_cliente_recorte(repo, lock, jobs, ["consolidado"]))
    assert [c["chave"] for c in _entrada(r, "I-HI")["recortes"]] == ["ug:1", "ug:4"]


@pytest.mark.parametrize("escolha", [
    {"origem": "msce_exercicio_anterior"},                              # msce não é escolha
    {"origem": "manual"},                                               # sem valores
    {"origem": "manual", "valores": {"L1": "1.00"}},                    # totalizadora
    {"origem": "manual", "valores": {"L19": "1.00"}},
    {"origem": "manual", "valores": {"P:L2": "1.00"}},                  # prefixo de quadro
])
def test_reprocessar_recusa_escolha_invalida_sem_job(cliente, escolha):
    """Requisito: escolhas inválidas por unidade respondem 422 antes de enfileirar"""
    fila = FilaFake()
    resposta = cliente(RepoFake(), fila).post(
        f"/dca/I-HI/reprocessar?anReferencia={EXERCICIO}", headers=HDR,
        json={"anterior_por_recorte": {"ug:3": escolha}})

    assert resposta.status_code == 422 and fila.chamadas == []


def test_reprocessar_aceita_manual_e_processado_por_unidade(cliente):
    """Requisito: pedido aceita `processado_exercicio_anterior`, `manual` e `padrao`"""
    fila = FilaFake()
    manual = {"origem": "manual", "valores": {"L2": "1.00"}}
    resposta = cliente(RepoFake(), fila).post(
        f"/dca/I-HI/reprocessar?anReferencia={EXERCICIO}", headers=HDR,
        json={"anterior_por_recorte": {
            "ug:1": {"origem": "processado_exercicio_anterior"}, "ug:3": manual,
            "ug:9": {"origem": "padrao"}}})

    assert resposta.status_code == 202, resposta.text
    assert fila.chamadas[0]["anterior_por_recorte"]["ug:3"] == manual
