"""Consulta da regra da célula — openspec/changes/dca-regra-na-celula."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_l27_mostra_a_soma_de_creditos_nas_duas_colunas():
    """Scenario: L27 mostra a soma de créditos nas duas colunas."""
    from app.services.regra_celula import consultar

    for coluna in ("exercicio_atual", "exercicio_anterior"):
        regra = consultar("BF", 2025, "L27", coluna)
        assert regra["origem"] == "period_change"
        assert regra["meses"] == list(range(1, 13))
        assert regra["natureza"] == "C"
        assert regra["contas"] == ["2188", "2288"]
        assert regra["fontes"] == ["860", "861", "862", "863", "869"]


def test_l28_no_exercicio_anterior_e_abertura():
    """Scenario: L28 no exercício anterior é abertura."""
    from app.services.regra_celula import consultar

    atual = consultar("BF", 2025, "L28", "exercicio_atual")
    anterior = consultar("BF", 2025, "L28", "exercicio_anterior")
    assert atual["origem"] == "period_change"
    assert anterior["origem"] == "abertura"
    assert "113520" in anterior["contas"]
    assert anterior["fontes"] == ["860", "861", "862", "863", "869"]


def test_l24_e_a_soma_das_filhas():
    """Scenario: L24 é a soma das filhas."""
    from app.services.regra_celula import consultar

    regra = consultar("BF", 2025, "L24", "exercicio_atual")
    assert regra["tipo"] == "soma"
    assert regra["filhas"] == ["L25", "L26", "L27", "L28"]
    assert regra["contas"] == []


def test_l60_soma_debitos_nas_duas_colunas():
    """Requisito: L60 segue a mesma origem mensal de L27, no lado do débito."""
    from app.services.bf.quadro_principal import apurar
    from app.services.regra_celula import consultar
    from tests.bf.conftest import ENTE, EXERCICIO, fonte_com

    for coluna in ("exercicio_atual", "exercicio_anterior"):
        regra = consultar("BF", 2025, "L60", coluna)
        assert regra["origem"] == "period_change"
        assert regra["natureza"] == "D"
    resultado = apurar(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={}))
    assert "period_change" in resultado.procedencia.origens_por_linha["L60"]


def test_anexo_sem_projecao_responde_indisponivel():
    """Scenario: anexo sem projeção responde 404."""
    from app.services.regra_celula import RegraIndisponivel, consultar

    with pytest.raises(RegraIndisponivel):
        consultar("BO", 2025, "L1", "exercicio_atual")


def test_linha_inexistente_e_linha_ambiguia():
    """Scenario: linha inexistente responde 404."""
    from app.services.regra_celula import RegraIndisponivel, consultar

    with pytest.raises(RegraIndisponivel):
        consultar("BF", 2025, "L99", "exercicio_atual")
    with pytest.raises(RegraIndisponivel):
        consultar("BF", 2025, "L1", "exercicio_atual")
    regra = consultar("BF", 2025, "L1", "exercicio_atual", quadro="QUADRO_PRINCIPAL")
    assert regra["codigo"] == "L1"


def _cliente(monkeypatch, permitido: bool):
    from app.routes import anexos as rotas

    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt", lambda _t: {"sub": "auditor@x"})

    async def perfil(_token, http=None):
        return permitido

    monkeypatch.setattr("app.auth.perfil.pode_ver_regra", perfil)
    app = FastAPI()
    app.include_router(rotas.router)
    return TestClient(app, raise_server_exceptions=False)


def test_quem_nao_e_auditor_recebe_403(monkeypatch):
    """Scenario: quem não é auditor recebe 403."""
    cliente = _cliente(monkeypatch, False)
    resposta = cliente.get(
        "/dca/BF/regra",
        params={"anReferencia": 2025, "linha": "L27", "coluna": "exercicio_atual"},
        headers={"Authorization": "Bearer t"},
    )
    assert resposta.status_code == 403
    assert "2188" not in resposta.text


def test_rota_de_linha_inexistente_responde_404(monkeypatch):
    """Scenario: linha inexistente responde 404."""
    cliente = _cliente(monkeypatch, True)
    resposta = cliente.get(
        "/dca/BF/regra",
        params={"anReferencia": 2025, "linha": "L99", "coluna": "exercicio_atual"},
        headers={"Authorization": "Bearer t"},
    )
    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Consulta indisponível."
