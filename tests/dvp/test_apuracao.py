"""Cenários sintéticos da apuração da DVP. O serviço ainda não existe: falham na importação.

A conferência contra ente real vive em `test_conferencia_viva.py` (marker `vivo`), como no BP:
a suíte padrão não vai à rede.
"""
from __future__ import annotations

from decimal import Decimal

from app.domain.bo.modelo import Registro
from tests.bo.conftest import saldo
from tests.bp.conftest import FontePorAno
from tests.dvp.conftest import EXERCICIO, JP, POA, celula


def test_deducao_de_imposto_reduz_l2(apurar_dvp):
    """Scenario: dedução de imposto reduz L2.

    `411210200` credora 2.000.000,00 e `411219700` devedora 1.052.431,74.
    Na direção da coluna a redutora sai. Na direção dela, L2 inflaria para 3.052.431,74.
    """
    fonte = FontePorAno({EXERCICIO: {4: [
        saldo("411210200", "2000000.00"),
        saldo("411219700", "1052431.74"),
    ]}})
    resultado = apurar_dvp(JP, EXERCICIO, fonte)
    assert celula(resultado, "L2") == Decimal("947568.26")


def test_conta_sintetica_entra_pela_direcao_do_prefixo(apurar_dvp):
    """Scenario: conta sintética usa o prefixo.

    `442510000` não é folha do PCASP. O saldo credor de 716,56 entra em L5.
    """
    fonte = FontePorAno({EXERCICIO: {4: [
        Registro("442510000", "C", Decimal("716.56")),
    ]}})
    resultado = apurar_dvp(POA, EXERCICIO, fonte)
    assert celula(resultado, "L5") == Decimal("716.56")


def test_transferencia_intra_permanece_em_l6(apurar_dvp):
    """Scenario: transferência intra permanece na linha."""
    # `451120100` (COTA RECEBIDA) é a folha real de `4.5.1` no PCASP; `451110100` não existe.
    fonte = FontePorAno({EXERCICIO: {4: [saldo("451120100", "1000.00")]}})
    resultado = apurar_dvp(JP, EXERCICIO, fonte)
    assert celula(resultado, "L6") == Decimal("1000.00")


def test_linha_sem_movimento_e_zero(apurar_dvp):
    """Scenario: linha sem movimento é zero."""
    fonte = FontePorAno({EXERCICIO: {4: [saldo("411210200", "1.00")]}})
    resultado = apurar_dvp(JP, EXERCICIO, fonte)
    assert celula(resultado, "L17") == Decimal("0.00")
