"""`GET /dca/BP?visao=` serve isolado ou consolidado do mesmo cache.

Change `bp-visao-consolidado-isolado`.

A visão é escolha de leitura: não entra na identidade do pedido e nunca enfileira job.
"""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tests.bp.conftest import FontePorAno, fp
from tests.pipeline.conftest import ENTE, EXERCICIO, RegistroFake


def _resultado_do_bp(com_visoes: bool = True) -> dict:
    """BP real apurado e serializado como o worker grava: intra só no ativo (100,00)."""
    from app.services.bp.quadro_principal import Anterior, apurar
    from app.services.pipeline.resultado import para_dados

    fonte = FontePorAno({EXERCICIO: {1: [fp("121120100", "100.00", "P")],
                                     2: [fp("231110000", "100.00")]}})
    dados = para_dados(apurar(int(ENTE), EXERCICIO, fonte, anterior=Anterior.MSCE))
    if not com_visoes:
        dados.pop("visoes")
    return dados


def _cliente(repo, lock, jobs, anexo: str, resultado: dict) -> TestClient:
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    repo.gravar(RegistroFake(ENTE, EXERCICIO, anexo, status="ok", resultado=resultado))

    def autorizada(request: Request) -> str:
        request.state.claims = {"sub": "u@x"}
        return ENTE

    class Fila:
        pendente = None

        def enfileirar(self, *args, **kwargs):
            raise AssertionError("trocar a visão não pode enfileirar")

    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo
    app.dependency_overrides[unidade_autorizada] = autorizada
    app.state.portas = {"fila_async": Fila, "lock": lock, "jobs": jobs, "repo_vigencias": None,
                        "base_url": ""}
    return TestClient(app)


def _get(cliente: TestClient, anexo: str, query: str = ""):
    return cliente.get(f"/dca/{anexo}?anReferencia={EXERCICIO}&id_ente={ENTE}{query}",
                       headers={"Authorization": "Bearer t", "X-Unidade-Id": ENTE})


def _l1(corpo: dict) -> Decimal:
    rule_id = next(linha["rule_id"] for linha in corpo["linhas"]
                   if linha["quadro"] == "QUADRO_PRINCIPAL" and linha["codigo"] == "L1")
    return Decimal(corpo["matriz"][rule_id]["exercicio_atual"])


def _equilibrio(corpo: dict) -> Decimal:
    return Decimal(corpo["diagnostico"]["equilibrio"]["exercicio_atual"])


def test_trocar_a_visao_nao_processa(repo, lock, jobs):
    """Scenario: trocar a visão não processa"""
    cliente = _cliente(repo, lock, jobs, "BP", _resultado_do_bp())

    isolado = _get(cliente, "BP", "&visao=isolado")
    consolidado = _get(cliente, "BP", "&visao=consolidado")
    padrao = _get(cliente, "BP")

    assert (isolado.status_code, consolidado.status_code) == (200, 200)
    assert (isolado.json()["visao"], consolidado.json()["visao"]) == ("isolado", "consolidado")
    assert padrao.json()["visao"] == "isolado"
    assert padrao.json()["matriz"] == isolado.json()["matriz"]
    assert (_l1(isolado.json()), _equilibrio(isolado.json())) == (
        Decimal("100.00"), Decimal("0.00"))
    assert (_l1(consolidado.json()), _equilibrio(consolidado.json())) == (
        Decimal("100.00"), Decimal("0.00"))
    assert "visoes" not in consolidado.json()


def test_visao_invalida(repo, lock, jobs):
    """Scenario: visão inválida"""
    cliente = _cliente(repo, lock, jobs, "BP", _resultado_do_bp())
    r = _get(cliente, "BP", "&visao=orgao")
    assert r.status_code == 422 and "visao inválida" in r.text


def test_visao_em_outro_anexo(repo, lock, jobs):
    """Scenario: visão em outro anexo"""
    cliente = _cliente(repo, lock, jobs, "BF", {"matriz": {}})
    assert _get(cliente, "BF", "&visao=consolidado").status_code == 422
    assert _get(cliente, "BF").status_code == 200


def test_cache_sem_a_visao_consolidada(repo, lock, jobs):
    """Scenario: cache sem a visão consolidada"""
    cliente = _cliente(repo, lock, jobs, "BP", _resultado_do_bp(com_visoes=False))
    r = _get(cliente, "BP", "&visao=consolidado")
    assert r.status_code == 409 and "reprocesse o BP" in r.text
    assert _get(cliente, "BP", "&visao=isolado").status_code == 200


def test_vigencia_publicada_preserva_a_visao_do_filtro():
    """Requisito: ida e volta pelo shape do banco não perde `visao` do filtro (D1)."""
    from app.infra.regras.carregador import carregar
    from app.infra.regras.vigencias import _achatar, _linha

    mapa = carregar(2025, demonstrativo="bp")
    com_filtro = [linha for linha in mapa.linhas if linha.filtros]
    assert len(com_filtro) == 21
    for linha in com_filtro:
        assert {f.visao for f in linha.filtros} == {"consolidado"}
        assert _linha(_achatar(linha)) == linha, linha.id
