"""PublicSoft lê a base por unidade gestora, com recuo explícito para a base oficial (D4).

Change `pipeline-dca-por-unidade-gestora`.
"""
from __future__ import annotations

import pytest
import requests

from app.infra.msc.fonte import Matriz, TipoSaldo

BASE = "https://api/contabilidade-tools/matriz-saldo/base-demonstrativos"


def _publicsoft(http):
    from app.infra.msc.publicsoft import PublicSoftMSC
    return PublicSoftMSC(http=http, token="t", url_saldos=BASE)


def _ler(fonte, classe: int = 1):
    return fonte.registros(ente=2505204, ano=2025, mes=12, classe=classe,
                           matriz=Matriz.ENCERRAMENTO, tipo_saldo=TipoSaldo.ENCERRAMENTO)


def _erro(codigo: int):
    resposta = requests.Response()
    resposta.status_code = codigo
    return requests.HTTPError(response=resposta)


def test_le_a_base_por_ug_e_normaliza_a_unidade():
    """Scenario: ente com UG / normalização de camelCase"""
    urls = []

    def http(url, params=None, headers=None, timeout=None):
        urls.append(url)
        return {"data": [{"codConta": "111110100", "naturezaConta": "D", "valor": "10.00",
                          "poderOrgao": "10131", "idUnidadeGestora": 0,
                          "nomeUnidadeGestora": "Sem unidade gestora identificada"}]}

    [registro] = _ler(_publicsoft(http))
    assert urls == [f"{BASE}/unidades-gestoras"]
    assert (registro.unidade_gestora, registro.nome_unidade_gestora) == (
        "0", "Sem unidade gestora identificada")


def test_422_cai_na_base_oficial_uma_vez_por_job():
    """Scenario: base por UG indisponível para o ente (MSC importada por CSV)"""
    urls = []

    def http(url, params=None, headers=None, timeout=None):
        urls.append(url)
        if url.endswith("/unidades-gestoras"):
            raise _erro(422)
        return {"data": [{"codConta": "111110100", "naturezaConta": "D", "valor": "10.00",
                          "poderOrgao": "10131"}]}

    fonte = _publicsoft(http)
    assert _ler(fonte, 1)[0].unidade_gestora == ""
    assert _ler(fonte, 2)[0].poder_orgao == "10131"
    assert urls == [f"{BASE}/unidades-gestoras", BASE, BASE]


def test_409_continua_sendo_sem_dados():
    """Scenario: gate de auditoria da PublicSoft reprovado"""
    def http(url, params=None, headers=None, timeout=None):
        raise _erro(409)

    assert _ler(_publicsoft(http)) == []


def test_outro_erro_propaga():
    def http(url, params=None, headers=None, timeout=None):
        raise _erro(500)

    with pytest.raises(requests.HTTPError):
        _ler(_publicsoft(http))


def test_siconfi_nao_tem_ug():
    """Scenario: normalização — o SICONFI não traz UG: campo vazio."""
    from app.infra.msc.normalizacao import normalizar

    registro = normalizar({"conta_contabil": "111110100", "natureza_conta": "D",
                           "valor": "1.00", "poder_orgao": "20231"})
    assert (registro.unidade_gestora, registro.nome_unidade_gestora) == ("", "")


def test_422_so_em_n_menos_1_mantem_a_ug_do_exercicio_atual():
    """Scenario: N−1 sem UG num job por UG — o recuo vale por exercício, uma tentativa cada."""
    urls = []

    def http(url, params=None, headers=None, timeout=None):
        urls.append((params["anReferencia"], url.endswith("/unidades-gestoras")))
        if url.endswith("/unidades-gestoras") and params["anReferencia"] == 2024:
            raise _erro(422)
        ug = {"idUnidadeGestora": 3} if url.endswith("/unidades-gestoras") else {}
        return {"data": [{"codConta": "111110100", "naturezaConta": "D", "valor": "10.00",
                          "poderOrgao": "10131", **ug}]}

    fonte = _publicsoft(http)
    antes = fonte.registros(ente=2505204, ano=2024, mes=12, classe=1)
    atuais = [_ler(fonte, classe)[0] for classe in (1, 2, 5)]
    fonte.registros(ente=2505204, ano=2024, mes=12, classe=2)

    assert antes[0].unidade_gestora == ""
    assert [r.unidade_gestora for r in atuais] == ["3", "3", "3"]
    assert urls == [(2024, True), (2024, False), (2025, True), (2025, True), (2025, True),
                    (2024, False)]
