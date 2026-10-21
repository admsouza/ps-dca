"""Contrato HTTP, cache e agregação da compensação atual por recorte."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.pipeline.cache import identidade_do_pedido, parametros_efetivos
from app.services.pipeline.resultado import para_dados
from tests.pipeline.conftest import RepoFake
from tests.pipeline.test_rota_anterior_por_recorte import (  # noqa: F401
    _cache_com_unidades,
    _reprocessar,
    api,
)
from tests.recorte.test_anterior_por_recorte import _bp, _fonte, _fonte_ano

COMPENSACAO = "CONTAS_COMPENSACAO"
ATUAL = "exercicio_atual"
D = Decimal


def _celula(resultado, codigo: str):
    linha = next(linha for linha in resultado.mapa.linhas
                 if linha.quadro == COMPENSACAO and linha.codigo == codigo)
    return resultado.matriz[linha.id][ATUAL]


def test_individuais_formam_grupos_e_consolidado_sem_soma_parcial():
    dados = _fonte_ano(
        {"1": "1.00", "2": "1.00", "4": "1.00"},
        po={"1": "10131", "2": "10132", "4": "20231"},
    )
    fonte = _fonte({classe: [r._replace(unidade_gestora="") for r in registros]
                    for classe, registros in dados.items()})
    valores = {
        "po:10131": {"C:L2": "100.00"},
        "po:10132": {"C:L2": "50.00"},
        "po:20231": {"C:L2": "0.00"},
    }

    resultado = _bp(fonte, valores_atuais_por_recorte=valores)

    assert _celula(resultado.recortes["poder:executivo"].resultado, "L2") == D("150.00")
    assert _celula(resultado.recortes["poder:legislativo"].resultado, "L2") == D("0.00")
    assert _celula(resultado, "L2") == D("150.00")
    assert _celula(resultado, "L3") is None
    assert resultado.procedencia.valores_atuais_por_recorte == valores
    assert para_dados(resultado)["procedencia"]["valores_atuais_por_recorte"] == valores

    incompleto = _bp(fonte, valores_atuais_por_recorte={
        "po:10131": {"C:L2": "100.00"}, "po:20231": {"C:L2": "0.00"}
    })
    assert _celula(incompleto.recortes["poder:executivo"].resultado, "L2") is None
    linha = next(linha.id for linha in incompleto.mapa.linhas
                 if linha.quadro == COMPENSACAO and linha.codigo == "L2")
    assert any(n.rule_id == linha and n.coluna == ATUAL
               for n in incompleto.diagnostico.nao_apuradas)


@pytest.mark.parametrize("mapa", [
    {"consolidado": {"C:L2": "1.00"}},
    {"poder:executivo": {"C:L2": "1.00"}},
    {"ug:3": {"P:L3": "1.00"}},
    {"ug:3": {"C:L1": "1.00"}},
])
def test_entrada_invalida_responde_422_sem_job(api, mapa):  # noqa: F811
    cliente, fila = api(RepoFake(), "BP")

    resposta = _reprocessar(cliente, "BP", {"valores_atuais_por_recorte": mapa})

    assert resposta.status_code == 422
    assert fila.chamadas == []


def test_unidade_nao_autorizada_responde_403_sem_job(api):  # noqa: F811
    cliente, fila = api(_cache_com_unidades(), "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {
        "valores_atuais_por_recorte": {"ug:20": {"C:L2": "1.00"}}
    })

    assert resposta.status_code == 403
    assert fila.chamadas == []


def test_atual_e_anterior_chegam_juntos_ao_job(api):  # noqa: F811
    cliente, fila = api(RepoFake(), "BP")
    anterior = {"po:10131": {"origem": "manual", "valores": {"P:L3": "7.00"}}}
    atuais = {"po:10131": {"C:L2": "9.00"}}

    resposta = _reprocessar(cliente, "BP", {
        "anterior_por_recorte": anterior,
        "valores_atuais_por_recorte": atuais,
    })

    assert resposta.status_code == 202
    assert fila.chamadas[0]["anterior_por_recorte"] == anterior
    assert fila.chamadas[0]["valores_atuais_por_recorte"] == atuais


def test_alterar_o_atual_nao_muda_a_coluna_anterior():
    dados = _fonte_ano({"1": "1.00", "4": "1.00"})
    escolhas = {"ug:1": {"origem": "manual", "valores": {"P:L3": "7.00"}}}
    antes = _bp(_fonte(dados), escolhas=escolhas, agora=("ug:1",))
    depois = _bp(
        _fonte(dados),
        escolhas=escolhas,
        agora=("ug:1",),
        valores_atuais_por_recorte={"ug:1": {"C:L2": "9.00"}},
    )

    for primeiro, segundo in (
        (antes, depois),
        (antes.recortes["ug:1"].resultado, depois.recortes["ug:1"].resultado),
        (antes.recortes["poder:executivo"].resultado,
         depois.recortes["poder:executivo"].resultado),
    ):
        assert {linha: celulas["exercicio_anterior"]
                for linha, celulas in primeiro.matriz.items()} == {
                    linha: celulas["exercicio_anterior"]
                    for linha, celulas in segundo.matriz.items()
                }


class _Registro:
    def __init__(self, valores):
        self.procedencia = {"valores_atuais_por_recorte": valores}
        self.resultado = None


def test_omissao_reaplica_vazio_limpa_so_a_unidade_e_identidade_muda():
    salvo = {"ug:1": {"C:L2": "100.00"}, "ug:4": {"C:L2": "5.00"}}
    registro = _Registro(salvo)

    assert parametros_efetivos({}, registro)["valores_atuais_por_recorte"] == salvo
    efetivo = parametros_efetivos({
        "valores_atuais_por_recorte": {"ug:1": {}}
    }, registro)
    assert efetivo["valores_atuais_por_recorte"] == {"ug:4": {"C:L2": "5.00"}}
    assert identidade_do_pedido(anexo="BP", valores_atuais_por_recorte=salvo) != (
        identidade_do_pedido(anexo="BP", valores_atuais_por_recorte=efetivo[
            "valores_atuais_por_recorte"]))

