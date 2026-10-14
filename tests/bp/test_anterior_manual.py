"""Coluna anterior manual do BP por unidade (`pipeline-anterior-por-recorte`).

Capability `dca/balanco-patrimonial`: `P:`/`FP:`/`C:` (folhas) e `S:<fonte>` (Superávit).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.bp.quadro_principal import apurar
from tests.bp.conftest import ENTE, EXERCICIO, FontePorAno, celula, fp
from tests.bp.test_superavit_fonte import _saldo

PRINCIPAL, SUPERAVIT = "QUADRO_PRINCIPAL", "SUPERAVIT_DEFICIT"
ATUAL, ANTERIOR = "exercicio_atual", "exercicio_anterior"
D = Decimal


def _manual(valores: dict[str, str], atual: list | None = None, classe8: list | None = None):
    fonte = FontePorAno({EXERCICIO: {1: atual or [], 8: classe8 or []}})
    return apurar(ENTE, EXERCICIO, fonte, anterior="manual", valores_anteriores=valores)


def _motivos(resultado, quadro: str, codigo: str) -> list[str]:
    rule_id = next(i.id for i in resultado.mapa.linhas if i.quadro == quadro and i.codigo == codigo)
    return [n.motivo for n in resultado.diagnostico.nao_apuradas
            if n.rule_id == rule_id and n.coluna == ANTERIOR]


def test_folhas_por_prefixo_e_totalizadora_pela_calculation():
    """Scenario: Câmara digitada"""
    r = _manual({"P:L3": "100.00", "P:L4": "50.00", "S:1500": "20.00"})

    assert celula(r, PRINCIPAL, "L3", ANTERIOR) == D("100.00")
    assert celula(r, PRINCIPAL, "L4", ANTERIOR) == D("50.00")
    assert celula(r, PRINCIPAL, "L2", ANTERIOR) == D("150.00")
    assert r.procedencia.origem_exercicio_anterior == "manual"
    assert r.procedencia.valores_anteriores == {"P:L3": "100.00", "P:L4": "50.00",
                                                "S:1500": "20.00"}


def test_superavit_une_as_fontes_informadas_e_soma_o_total():
    """Scenario: Câmara digitada — Superávit"""
    r = _manual({"S:1500": "20.00", "S:1700": "5.00"},
                classe8=[_saldo("821110100", "C", "9.00", "1700")])

    assert celula(r, SUPERAVIT, "1500", ANTERIOR) == D("20.00")
    assert celula(r, SUPERAVIT, "1500", ATUAL) == D("0.00")
    assert celula(r, SUPERAVIT, "1700", ANTERIOR) == D("5.00")
    assert celula(r, SUPERAVIT, "1700", ATUAL) == D("9.00")
    assert celula(r, SUPERAVIT, "Total", ANTERIOR) == D("25.00")


def test_fonte_de_n_nao_informada_fica_nao_apurada():
    """Scenario: folha não informada — Superávit"""
    r = _manual({"S:1500": "20.00"}, classe8=[_saldo("821110100", "C", "9.00", "1700")])

    assert celula(r, SUPERAVIT, "1700", ANTERIOR) is None
    assert celula(r, SUPERAVIT, "Total", ANTERIOR) == D("20.00")


def test_superavit_sem_nenhuma_fonte_informada_fica_nao_apurado():
    r = _manual({"P:L3": "1.00"}, classe8=[_saldo("821110100", "C", "9.00", "1700")])

    assert celula(r, SUPERAVIT, "Total", ANTERIOR) is None
    assert _motivos(r, SUPERAVIT, "Total") == ["não informado"]


def test_folha_nao_informada_fica_nao_apurada_com_motivo():
    """Scenario: folha não informada"""
    r = _manual({"P:L3": "100.00"})

    assert celula(r, PRINCIPAL, "L5", ANTERIOR) is None
    assert _motivos(r, PRINCIPAL, "L5") == ["não informado"]


def test_quadro_fp_e_compensacao_por_prefixo():
    r = _manual({"FP:L2": "10.00", "C:L2": "7.00"})

    assert celula(r, "ATIVOS_PASSIVOS_FINANCEIROS", "L2", ANTERIOR) == D("10.00")
    assert celula(r, "CONTAS_COMPENSACAO", "L2", ANTERIOR) == D("7.00")


def test_coluna_atual_nao_muda_com_o_manual():
    atual = [fp("111110100", "100.00", "F")]
    msce = apurar(ENTE, EXERCICIO, FontePorAno({EXERCICIO: {1: atual}, EXERCICIO - 1: {}}),
                  anterior="msce_exercicio_anterior")
    r = _manual({"P:L3": "1.00"}, atual)

    assert celula(r, PRINCIPAL, "L3", ATUAL) == celula(msce, PRINCIPAL, "L3", ATUAL) == D("100.00")


@pytest.mark.parametrize("valores, trecho", [
    ({"X:L3": "1.00"}, "prefixo"),
    ({"P:L999": "1.00"}, "L999"),
    ({"P:L2": "1.00"}, "totalizadora"),
    ({"S:15": "1.00"}, "4 dígitos"),
    ({"S:1500": "abc"}, "valor inválido"),
    ({"P:L3": "1,00"}, "valor inválido"),
    ({"L3": "1.00"}, "prefixo"),
])
def test_validacao_antes_do_job(valores, trecho):
    """Scenario: totalizadora informada — e as demais recusas"""
    from app.services.bp.informados import validar_valores_anteriores

    with pytest.raises(ValueError, match=trecho):
        validar_valores_anteriores(EXERCICIO, valores)


def test_validacao_aceita_o_manual_valido():
    from app.services.bp.informados import validar_valores_anteriores

    validar_valores_anteriores(EXERCICIO, {"P:L3": "100.00", "FP:L2": "1", "C:L2": "-2.50",
                                           "S:1500": "20.00"})
