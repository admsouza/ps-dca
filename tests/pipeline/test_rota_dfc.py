"""`GET /dca/DFC` ponta a ponta, com as portas fakes que o resto do pipeline já usa."""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tests.pipeline.conftest import LockFake
from tests.pipeline.test_rota_dvp import FilaFake, RepoFake

ENTE = "4314902"
EXERCICIO = 2025
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}


class RegistroFake:
    def __init__(self, dados: dict, versao_api: str, versao_regras: str):
        self.ente, self.exercicio, self.anexo = ENTE, EXERCICIO, "DFC"
        self.status = "ok"
        self.resultado = dados
        self.versao_api = versao_api
        self.versao_regras = versao_regras
        self.job_id = None
        self.atualizado_em = None
        self.duracao_ms = 1
        self.erro = None


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


def _resultado_dfc():
    from app.services.dfc.quadro_principal import apurar
    from tests.bp.conftest import FontePorAno

    return apurar(int(ENTE), EXERCICIO, FontePorAno({}))


def test_rota_da_dfc_serve_o_resultado_em_cache(cliente):
    """Scenario: os quadros da DFC saem na ordem do IPC 08"""
    from app.services.pipeline.apuracao import VERSAO_API, versao_regras
    from app.services.pipeline.cache import versao_do_pedido
    from app.services.pipeline.resultado import para_dados

    versao = versao_do_pedido(versao_regras(EXERCICIO, "DFC"), "DFC", {"fonte": "publicsoft"})
    registro = RegistroFake(para_dados(_resultado_dfc()), VERSAO_API, versao)

    resposta = cliente(RepoFake(registro)).get(f"/dca/DFC?anReferencia={EXERCICIO}", headers=HDR)

    assert resposta.status_code == 200
    corpo = resposta.json()
    linhas = corpo["resultado"]["linhas"] if "resultado" in corpo else corpo["linhas"]
    assert len(linhas) == 84
    assert linhas[0]["codigo"] == "L1" and linhas[0]["grupo"] == "OPERACIONAIS"
    assert linhas[35]["codigo"] == "L36" and linhas[35]["grupo"] == "CAIXA"
    assert linhas[-1]["quadro"] == "JUROS_ENCARGOS_DIVIDA"


def test_reprocessar_a_dfc_enfileira(cliente):
    """Requisito: `POST /dca/DFC/reprocessar` responde 202 e enfileira o anexo canônico."""
    fila = FilaFake()
    resposta = cliente(RepoFake(), fila).post(
        f"/dca/dfc/reprocessar?anReferencia={EXERCICIO}", headers=HDR)

    assert resposta.status_code == 202, resposta.text
    assert fila.chamadas and fila.chamadas[0]["anexo"] == "DFC"


def test_rota_e_cli_publicam_o_mesmo_json(cliente):
    """Requisito: o JSON da rota é o mesmo que `python -m app.cli.dfc --json` imprime."""
    import json

    from app.cli.dfc import _json as cli_json
    from app.services.pipeline.apuracao import VERSAO_API, versao_regras
    from app.services.pipeline.cache import versao_do_pedido
    from app.services.pipeline.resultado import para_dados

    resultado = _resultado_dfc()
    versao = versao_do_pedido(versao_regras(EXERCICIO, "DFC"), "DFC", {"fonte": "publicsoft"})
    resposta = cliente(RepoFake(RegistroFake(para_dados(resultado), VERSAO_API, versao))).get(
        f"/dca/DFC?anReferencia={EXERCICIO}", headers=HDR)

    do_cli = json.loads(cli_json(resultado))
    corpo = resposta.json()
    da_rota = corpo.get("resultado", corpo)
    assert da_rota["linhas"] == do_cli["linhas"]
    assert da_rota["matriz"] == do_cli["matriz"]
