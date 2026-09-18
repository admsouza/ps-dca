"""A competência de encerramento não tem o mesmo número nas duas APIs.

Medido em 2026-09-18, nos 4 entes de homologação: no SICONFI a matriz de encerramento está na
competência **12**, identificada por `co_tipo_matriz=MSCE`; pedir `me_referencia=13` devolve
**zero registros**. Na PublicSoft o encerramento é a competência especial **13** (`mesMsc=13`),
e 12 é dezembro.

É diferença de vocabulário de API, então mora no adapter — o domínio continua falando em
competência 1–12 mais a matriz, e nenhum serviço precisa saber o número de cada fonte.
"""
from __future__ import annotations

import pytest

from app.infra.msc.fonte import Matriz, TipoSaldo

EXERCICIO = 2026
DEZEMBRO = 12


class HttpFake:
    """Transporte que grava os parâmetros de cada chamada, sem rede."""

    def __init__(self, resposta: dict | None = None):
        self.resposta = resposta if resposta is not None else {"items": []}
        self.chamadas: list[dict] = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.chamadas.append({"url": url, "params": params or {}})
        if "auditoria" in str(url):
            return {"status": "validado", "podeGerar": True}
        return self.resposta


def _publicsoft(http):
    from app.infra.msc.publicsoft import PublicSoftMSC

    return PublicSoftMSC(http=http, token="t", url_saldos="https://api/base-demonstrativos",
                         url_auditoria="https://api/auditoria")


def test_publicsoft_pede_a_competencia_13_para_a_matriz_de_encerramento():
    """Scenario: encerramento na PublicSoft

    É `mesMsc=13`, a competência especial.

    Pedir 12 devolveria dezembro — posição do mês, não o encerramento do exercício.
    """
    http = HttpFake()
    _publicsoft(http).registros(ente=2611606, ano=EXERCICIO, mes=DEZEMBRO, classe=1,
                                matriz=Matriz.ENCERRAMENTO, tipo_saldo=TipoSaldo.ABERTURA)
    saldos = [c for c in http.chamadas if "base-demonstrativos" in c["url"]][0]
    assert saldos["params"]["meReferencia"] == 13


def test_publicsoft_audita_a_mesma_competencia_que_consulta():
    """Scenario: encerramento na PublicSoft — o gate de auditoria

    A auditoria do encerramento é a de `mesMsc=13`, não a de dezembro.

    Auditar 12 e ler 13 liberaria uma competência com base na validação de outra.
    """
    http = HttpFake()
    _publicsoft(http).registros(ente=2611606, ano=EXERCICIO, mes=DEZEMBRO, classe=1,
                                matriz=Matriz.ENCERRAMENTO, tipo_saldo=TipoSaldo.ABERTURA)
    auditoria = [c for c in http.chamadas if "auditoria" in c["url"]][0]
    assert auditoria["params"]["mesMsc"] == 13


@pytest.mark.parametrize("mes", [1, 6, 12])
def test_publicsoft_mantem_o_mes_na_matriz_consolidada(mes):
    """Scenario: consolidada mantém o mês pedido

    12 é dezembro, não o encerramento.
    """
    http = HttpFake()
    _publicsoft(http).registros(ente=2611606, ano=EXERCICIO, mes=mes, classe=1,
                                matriz=Matriz.CONSOLIDADA, tipo_saldo=TipoSaldo.ENCERRAMENTO)
    saldos = [c for c in http.chamadas if "base-demonstrativos" in c["url"]][0]
    assert saldos["params"]["meReferencia"] == mes


def test_siconfi_continua_na_competencia_12_para_o_encerramento():
    """Scenario: encerramento no SICONFI

    É `me_referencia=12` + `co_tipo_matriz=MSCE`.

    Medido nos 4 entes: `me_referencia=13` devolve zero registros. Traduzir 13 aqui produziria
    matriz vazia — e vazio numa apuração vira demonstrativo zerado, não erro.
    """
    from app.infra.msc.siconfi import SiconfiMSC

    http = HttpFake()
    SiconfiMSC(http=http, url="https://api", espera=lambda _: None).registros(
        ente=2611606, ano=EXERCICIO, mes=DEZEMBRO, classe=1,
        matriz=Matriz.ENCERRAMENTO, tipo_saldo=TipoSaldo.ABERTURA)
    params = http.chamadas[0]["params"]
    assert params["me_referencia"] == 12
    assert params["co_tipo_matriz"] == "MSCE"
