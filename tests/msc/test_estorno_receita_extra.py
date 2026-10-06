"""Relatório sintético de estorno de receita extra na PublicSoft."""
from __future__ import annotations

from decimal import Decimal

import pytest


class _Http:
    def __init__(self, resposta):
        self.resposta = resposta
        self.chamadas = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.chamadas.append({"url": url, "params": params, "headers": headers})
        return self.resposta


def _fonte(http, url="https://api.exemplo/contabilidade-tools/matriz-saldo/base-demonstrativos"):
    from app.infra.msc.publicsoft import PublicSoftMSC

    return PublicSoftMSC(http=http, token="tok", url_saldos=url, url_auditoria="https://api/auditoria")


def test_le_o_total_geral_com_o_token_da_fonte():
    http = _Http({"data": {"totalGeral": 115679.4}, "statusCode": 200})
    total = _fonte(http).estorno_receita_extra(2025)

    assert total == Decimal("115679.4")
    chamada = http.chamadas[0]
    assert chamada["url"].endswith(
        "/contabilidade-tools/relatorios-gerenciais/estorno-receita-extra"
    )
    assert chamada["params"] == {"exercicio": 2025, "tipo": "sintetico"}
    assert chamada["headers"] == {"x-authorization": "tok"}


def test_estorno_de_despesa_le_o_total_geral_zero():
    http = _Http({"data": {"totaisPorUnidadeGestora": [], "totalGeral": 0}, "statusCode": 200})
    total = _fonte(http).estorno_despesa_extra(2025)

    assert total == Decimal("0")
    assert http.chamadas[0]["url"].endswith(
        "/contabilidade-tools/relatorios-gerenciais/estorno-despesa-extra"
    )
    assert http.chamadas[0]["params"] == {"exercicio": 2025, "tipo": "sintetico"}
    assert http.chamadas[0]["headers"] == {"x-authorization": "tok"}


def test_sem_total_geral_falha():
    from app.infra.msc.publicsoft import EstornoIndisponivel

    with pytest.raises(EstornoIndisponivel):
        _fonte(_Http({"data": {"totaisPorUnidadeGestora": []}})).estorno_receita_extra(2025)
