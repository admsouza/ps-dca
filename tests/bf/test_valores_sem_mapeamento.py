"""Completar G8 no exercício atual — `openspec/changes/bf-completar-nao-apuradas-g8`."""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bf.conftest import ENTE, EXERCICIO, fonte_com


def _apurar(apurar_bf, **kwargs):
    return apurar_bf(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={}), **kwargs)


def _id_de(resultado, codigo: str) -> str:
    return next(linha.id for linha in resultado.mapa.linhas
                if linha.quadro == "QUADRO_PRINCIPAL" and linha.codigo == codigo)


def test_linha_sem_conta_sai_nao_apurada(apurar_bf):
    """Scenario: linha sem conta sai não apurada."""
    resultado = _apurar(apurar_bf)
    l22 = _id_de(resultado, "L22")
    assert resultado.matriz[l22]["exercicio_atual"] is None
    assert any(n.rule_id == l22 and n.coluna == "exercicio_atual"
               for n in resultado.diagnostico.nao_apuradas)


def test_completar_g8_no_atual(apurar_bf):
    """Scenario: completar G8 no exercício atual."""
    resultado = _apurar(apurar_bf, valores_sem_mapeamento={"L22": "1234567.89"})
    l22 = _id_de(resultado, "L22")
    assert resultado.matriz[l22]["exercicio_atual"] == Decimal("1234567.89")
    assert resultado.procedencia.valores_sem_mapeamento == {"L22": "1234567.89"}
    assert not any(n.rule_id == l22 and n.coluna == "exercicio_atual"
                   for n in resultado.diagnostico.nao_apuradas)
    assert resultado.procedencia.origem_exercicio_anterior == "msce_exercicio_anterior"


def test_total_soma_a_parcela_g8_informada(apurar_bf):
    """Scenario: o total soma a parcela G8 informada — L21 = L22 + L23."""
    resultado = _apurar(apurar_bf, valores_sem_mapeamento={"L22": "1234567.89"})
    l21 = _id_de(resultado, "L21")
    assert resultado.matriz[l21]["exercicio_atual"] == Decimal("1234567.89")


def test_codigo_fora_de_g8_e_recusado():
    """Scenario: código fora de G8 é recusado."""
    from app.services.bf.informados import LinhaDesconhecida, validar_valores_sem_mapeamento

    with pytest.raises(LinhaDesconhecida):
        validar_valores_sem_mapeamento({"L17": "1.00"})


def test_valor_nao_decimal_e_recusado():
    from app.services.bf.informados import validar_valores_sem_mapeamento

    with pytest.raises(ValueError):
        validar_valores_sem_mapeamento({"L22": "abc"})


def test_celula_none_do_anterior_processado_vira_nao_apurada():
    from app.services.bf.quadro_principal import Anterior, apurar

    pronto = {"matriz": {("QUADRO_PRINCIPAL", "L2"): {"exercicio_anterior": None},
                         ("QUADRO_PRINCIPAL", "L3"): {"exercicio_anterior": Decimal("1.00")}}}

    r = apurar(ENTE, EXERCICIO, fonte_com(), anterior=Anterior.PROCESSADO,
               anterior_pronto=pronto)

    ids = {i.codigo: i.id for i in r.mapa.linhas if i.quadro == "QUADRO_PRINCIPAL"}
    motivos = {(n.rule_id, n.coluna): n.motivo for n in r.diagnostico.nao_apuradas}
    assert r.matriz[ids["L2"]]["exercicio_anterior"] is None
    assert motivos[(ids["L2"], "exercicio_anterior")] == "não apurada no exercício anterior"
    assert (ids["L3"], "exercicio_anterior") not in motivos
