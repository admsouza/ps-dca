"""BP espelha o `DCA-Anexo I-AB` declarado (`bp-espelho-iab`, PO 2026-10-07).

Saldos sintéticos com os números de Cuitegi (planilha `SICONFI_DCA_2831_ANUAL_1.xls`); a medição
real contra a planilha e o `tt/dca` fica registrada em `docs/entes-homologacao/cuitegi/`.
"""
from __future__ import annotations

from decimal import Decimal

from tests.bp.conftest import ENTE, EXERCICIO, FontePorAno, celula, fp

PRINCIPAL = "QUADRO_PRINCIPAL"
FP = "ATIVOS_PASSIVOS_FINANCEIROS"


def test_cuitegi_2025_igual_ao_iab_declarado(apurar_bp):
    """Scenario: Cuitegi 2025 igual ao I-AB declarado"""
    fonte = FontePorAno({EXERCICIO: {
        1: [fp("111110100", "26431637.72", "F"), fp("123110101", "20651902.91", "P"),
            fp("121120100", "29230791.29", "P")],          # intra: entra no consolidado declarado
        2: [fp("211110101", "2647434.03", "F"), fp("221110100", "119311755.53", "P"),
            fp("231110000", "-45644857.64")],
    }})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, PRINCIPAL, "L1") == Decimal("76314331.92")
    assert celula(resultado, PRINCIPAL, "L15") == Decimal("76314331.92")
    assert celula(resultado, PRINCIPAL, "L32") == Decimal("-45644857.64")
    assert resultado.diagnostico.equilibrio["exercicio_atual"] == Decimal("0.00")


def test_conta_intra_entra_na_linha(apurar_bp):
    """Scenario: conta intra entra na linha"""
    fonte = FontePorAno({EXERCICIO: {1: [fp("121120100", "90.00", "P"),
                                         fp("121110101", "10.00", "P")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, PRINCIPAL, "L10") == Decimal("100.00")


def test_passivo_financeiro_pela_composicao_do_iab(apurar_bp):
    """Scenario: passivo financeiro pela composição do I-AB"""
    fonte = FontePorAno({EXERCICIO: {
        2: [fp("211110101", "2647434.03", "F")],
        6: [fp("631100000", "70972.63"), fp("631710000", "387532.93"),
            fp("622130500", "0.00")],
    }})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, FP, "L5") == Decimal("3105939.59")


def test_inscricao_em_duas_contas_nao_e_contada_duas_vezes(apurar_bp):
    """Scenario: inscrição em duas contas não é contada duas vezes"""
    fonte = FontePorAno({EXERCICIO: {
        2: [fp("211110101", "6496569.60", "F")],
        6: [fp("631100000", "73610.41"), fp("622130500", "48335.00"),
            fp("631710000", "48335.00"), fp("622130100", "10.00")],   # 6.2.2.1.3.01 fora da L5
    }})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, FP, "L5") == Decimal("6618515.01")
