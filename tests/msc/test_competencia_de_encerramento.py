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
        return self.resposta


def _publicsoft(http):
    from app.infra.msc.publicsoft import PublicSoftMSC

    return PublicSoftMSC(http=http, token="t", url_saldos="https://api/base-demonstrativos")


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


def test_publicsoft_encerramento_com_auditoria_pendente_e_sem_dados():
    """Scenario: encerramento na PublicSoft — o gate de auditoria

    O servidor audita a própria competência pedida (13) e responde 409 se não liberada: sem
    dados, não erro. Não há pré-check em `/auditorias` (exige JWT; o worker só tem token_ps).
    """
    import requests

    def http(url, params=None, headers=None, timeout=None):
        assert "auditoria" not in url
        assert params["meReferencia"] == 13
        resposta = requests.Response()
        resposta.status_code = 409
        raise requests.HTTPError(response=resposta)

    assert _publicsoft(http).registros(ente=2611606, ano=EXERCICIO, mes=DEZEMBRO, classe=1,
                                       matriz=Matriz.ENCERRAMENTO,
                                       tipo_saldo=TipoSaldo.ABERTURA) == []


def test_publicsoft_propaga_erro_que_nao_e_409():
    """Scenario: só o 409 é "sem dados" — 401/5xx são falha de credencial/transporte e não
    podem virar demonstrativo vazio."""
    import requests

    def http(url, params=None, headers=None, timeout=None):
        resposta = requests.Response()
        resposta.status_code = 401
        raise requests.HTTPError(response=resposta)

    with pytest.raises(requests.HTTPError):
        _publicsoft(http).registros(ente=2611606, ano=EXERCICIO, mes=DEZEMBRO, classe=1)


@pytest.mark.parametrize("matriz", list(Matriz))
def test_publicsoft_envia_so_os_parametros_do_contrato(matriz):
    """Scenario: query do `base-demonstrativos` dentro do DTO

    O Nest valida com `forbidNonWhitelisted`: qualquer campo fora do DTO vira 400.
    Regressão de produção (2026-10-06): `tipoMatriz=encerramento` derrubou o BF.
    """
    http = HttpFake()
    _publicsoft(http).registros(ente=2611606, ano=EXERCICIO, mes=DEZEMBRO, classe=1,
                                matriz=matriz, tipo_saldo=TipoSaldo.ABERTURA)
    assert set(http.chamadas[0]["params"]) == {"anReferencia", "meReferencia", "classeConta",
                                                "idTv"}


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
