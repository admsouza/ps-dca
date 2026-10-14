"""`Estorno`: total do ente e totais por instituição, como o `ps-erp` os devolve.

Change `bf-por-unidade-gestora`, D2/D4.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

BASE = "https://api.exemplo/contabilidade-tools/matriz-saldo/base-demonstrativos"


def _estorno(resposta: dict):
    from app.infra.msc.publicsoft import PublicSoftMSC

    fonte = PublicSoftMSC(http=lambda *a, **k: resposta, token="t", url_saldos=BASE,
                          responsavel="")
    return fonte.estorno_receita_extra(2025)


def test_le_total_por_unidade_e_poder_orgao():
    """Scenario: UG / PO"""
    estorno = _estorno({"data": {"totalGeral": 115.5, "totaisPorUnidadeGestora": [
        {"idInstituicao": 3, "valor": 100.0, "poderOrgao": "10131"},
        {"idInstituicao": 4, "valor": 15.5, "poderOrgao": None}]}})

    assert estorno.total == Decimal("115.5")
    assert estorno.por_unidade == {"ug:3": Decimal("100.0"), "ug:4": Decimal("15.5")}
    assert estorno.poder_orgao == {"ug:3": "10131", "ug:4": None}


def test_campo_poder_orgao_ausente_e_diferente_de_nulo():
    """Scenario: resposta sem o campo poderOrgao (ps-erp anterior à change)"""
    estorno = _estorno({"data": {"totalGeral": 10, "totaisPorUnidadeGestora": [
        {"idInstituicao": 3, "valor": 10}]}})

    assert estorno.poder_orgao is None
    assert estorno.por_unidade == {"ug:3": Decimal("10")}


def test_sem_totais_por_unidade_falha():
    """Scenario: resposta sem totais por unidade"""
    from app.infra.msc.publicsoft import EstornoIndisponivel

    with pytest.raises(EstornoIndisponivel):
        _estorno({"data": {"totalGeral": 10}})


@pytest.mark.parametrize("item", [
    {"valor": 1}, {"idInstituicao": 3}, {"idInstituicao": 3, "valor": None},
    {"idInstituicao": None, "valor": 1}, {"idInstituicao": 3, "valor": "abc"},
])
def test_item_sem_instituicao_ou_valor_falha_como_indisponivel(item):
    from app.infra.msc.publicsoft import EstornoIndisponivel

    with pytest.raises(EstornoIndisponivel):
        _estorno({"data": {"totalGeral": 10, "totaisPorUnidadeGestora": [item]}})
