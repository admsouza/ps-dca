"""BP isolado ou consolidado (`bp-consolidado-sem-exclusao`, PO 2026-10-08).

Uma leitura da fonte: as duas visões incluem todas as contas e espelham o `I-AB` declarado.
"""
from __future__ import annotations

from decimal import Decimal

from tests.bp.conftest import ENTE, EXERCICIO, FontePorAno, celula, fp

PRINCIPAL = "QUADRO_PRINCIPAL"
FP = "ATIVOS_PASSIVOS_FINANCEIROS"
ATUAL = "exercicio_atual"


def _consolidado(resultado, quadro: str, codigo: str) -> Decimal | None:
    rule_id = next(linha.id for linha in resultado.mapa.linhas
                   if linha.quadro == quadro and linha.codigo == codigo)
    return resultado.visoes["consolidado"].matriz[rule_id][ATUAL]


def test_conta_intra_entra_nas_duas_visoes(apurar_bp):
    """Scenario: conta intra entra nas duas visões"""
    fonte = FontePorAno({EXERCICIO: {1: [fp("121120100", "90.00", "P"),
                                         fp("121110101", "10.00", "P")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, PRINCIPAL, "L10") == Decimal("100.00")
    assert _consolidado(resultado, PRINCIPAL, "L10") == Decimal("100.00")


def test_l34_inclui_a_23212_nas_duas_visoes(apurar_bp):
    """Scenario: L34 inclui a 2.3.2.1.2 nas duas visões"""
    fonte = FontePorAno({EXERCICIO: {2: [fp("232110000", "7.00"), fp("232120000", "3.00")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, PRINCIPAL, "L34") == Decimal("10.00")
    assert _consolidado(resultado, PRINCIPAL, "L34") == Decimal("10.00")


def test_quadro_fp_igual_nas_duas_visoes(apurar_bp):
    """Scenario: quadro F/P igual nas duas visões"""
    fonte = FontePorAno({EXERCICIO: {1: [fp("111110100", "26431637.72", "F"),
                                         fp("121120100", "29230791.29", "P")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    for codigo in ("L2", "L3"):
        assert _consolidado(resultado, FP, codigo) == celula(resultado, FP, codigo)
    assert celula(resultado, FP, "L3") == Decimal("29230791.29")


def test_equilibrio_igual_nas_duas_visoes(apurar_bp):
    """Scenario: equilíbrio igual nas duas visões"""
    fonte = FontePorAno({EXERCICIO: {1: [fp("121120100", "100.00", "P")],
                                     2: [fp("231110000", "100.00")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert resultado.diagnostico.equilibrio[ATUAL] == Decimal("0.00")
    assert resultado.visoes["consolidado"].equilibrio[ATUAL] == Decimal("0.00")


def test_fonte_lida_uma_vez(apurar_bp):
    """Scenario: fonte lida uma vez"""
    fonte = FontePorAno({EXERCICIO: {1: [fp("121120100", "1.00", "P")]},
                         EXERCICIO - 1: {1: [fp("121120100", "1.00", "P")]}})
    apurar_bp(ENTE, EXERCICIO, fonte)
    lidas = [(c["ano"], c["classe"]) for c in fonte.chamadas]
    assert lidas and len(lidas) == len(set(lidas))
