"""Conferência viva da DFC contra a MSC do ente.

Vai à rede. Fora da suíte padrão (`-m "not vivo"`); rode com `python -m pytest -m vivo`.
Espelha a medição de 2026-10-27 registrada em `openspec/changes/dfc-apuracao-f1/`.

A DFC não tem anexo publicado no `tt/dca`: o aceite é a **identidade de caixa** da própria MSC —
`L34` tem de ser a variação de `1.1.1` entre os dois exercícios, e `L36` o `1.1.1` de N.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.dfc.conftest import CUITEGI, EXERCICIO, POA, celula

pytestmark = pytest.mark.vivo

# Caixa (`1.1.1`) de Porto Alegre na MSC de encerramento, saldo de abertura.
CAIXA_2024 = Decimal("2785855199.20")
CAIXA_2025 = Decimal("2854802415.12")
VARIACAO = CAIXA_2025 - CAIXA_2024                       # 68.947.215,92
# Resíduo que o ente preenche em `L16` (item 17) para a demonstração fechar — medido em
# 2026-10-27. É 7,4% dos ingressos operacionais.
L16_QUE_FECHA = "976884327.42"


@pytest.fixture
def fonte_viva():
    from app.infra.msc.siconfi import SiconfiMSC

    return SiconfiMSC()


def test_porto_alegre_2025_apura_as_84_linhas(apurar_dfc, fonte_viva):
    """Scenario: as 84 linhas apuram"""
    from app.infra.msc.fonte import Matriz, TipoSaldo

    resultado = apurar_dfc(POA, EXERCICIO, fonte_viva)
    assert resultado.procedencia.matriz == str(Matriz.ENCERRAMENTO)
    assert resultado.procedencia.tipo_saldo == str(TipoSaldo.ABERTURA)
    assert resultado.procedencia.classes == (1, 2, 3, 4, 5, 6)
    assert not resultado.diagnostico.nao_apuradas
    assert len(resultado.matriz) == 84


def test_porto_alegre_2025_fecha_a_identidade_de_caixa(apurar_dfc, fonte_viva):
    """Scenario: identidade de caixa em Porto Alegre 2025"""
    resultado = apurar_dfc(POA, EXERCICIO, fonte_viva,
                           valores_informados={"L16": L16_QUE_FECHA})
    assert celula(resultado, "L35") == CAIXA_2024
    assert celula(resultado, "L34") == VARIACAO
    assert celula(resultado, "L36") == CAIXA_2025


def test_porto_alegre_2025_valores_ja_medidos(apurar_dfc, fonte_viva):
    """Requisito: regressão dos valores medidos em D4 (docs/evidencia-dfc-d4-funcao-28.md)."""
    resultado = apurar_dfc(POA, EXERCICIO, fonte_viva)
    assert celula(resultado, "L14") == Decimal("115727775.84")
    assert celula(resultado, "L32") == Decimal("4278384.37")
    # L35 é o caixa de N−1, nunca o de N (D3)
    assert celula(resultado, "L35") == CAIXA_2024


def test_caixa_da_dfc_bate_com_o_balanco_financeiro(apurar_dfc, fonte_viva):
    """Requisito: `L35`/`L36` reproduzem `L29`/`L62` do BF do mesmo ente e exercício.

    Conferência cruzada entre demonstrativos: os dois leem a mesma MSC e têm de dizer o mesmo
    sobre o caixa (`docs/entes-homologacao/porto-alegre/auditoria-bf-2025.md`, linhas 65 e 109).
    """
    resultado = apurar_dfc(POA, EXERCICIO, fonte_viva,
                           valores_informados={"L16": L16_QUE_FECHA})
    assert celula(resultado, "L35") == CAIXA_2024        # BF L29, exercício 2025
    assert celula(resultado, "L36") == CAIXA_2025        # BF L62, exercício 2025


def test_remuneracao_das_disponibilidades_apura(apurar_dfc, fonte_viva):
    """Scenario: a remuneração das disponibilidades apura

    Antes de `dfc-naturezas-desdobramento` saía 0,00: o pattern `1321001x` não alcançava
    `13210101`. O mesmo valor deixou `L5`, que o recebia indevidamente — é reclassificação.
    """
    resultado = apurar_dfc(POA, EXERCICIO, fonte_viva)
    assert celula(resultado, "L9") == Decimal("776452523.68")
    assert celula(resultado, "L5") == Decimal("144308504.92")
    assert celula(resultado, "L2") == Decimal("13153640269.72"), "o total não muda"


def test_cuitegi_nao_conta_a_aquisicao_duas_vezes(apurar_dfc, fonte_viva):
    """Scenario: aquisição de ativo não entra duas vezes

    Cuitegi publica a DFC **consolidada**, o mesmo recorte da MSC — é o único ente em que
    apurado e publicado são comparáveis direto (`docs/entes-homologacao/cuitegi/`).
    """
    resultado = apurar_dfc(CUITEGI, EXERCICIO, fonte_viva)
    assert celula(resultado, "L23") == Decimal("1791501.94")
    assert celula(resultado, "L25") == Decimal("0.00")
    assert celula(resultado, "L22") == Decimal("1791501.94")


def test_cuitegi_confere_as_receitas_derivadas(apurar_dfc, fonte_viva):
    """Requisito: o bloco de receitas derivadas bate com o publicado, linha a linha."""
    resultado = apurar_dfc(CUITEGI, EXERCICIO, fonte_viva)
    assert celula(resultado, "L3") == Decimal("1962087.50")
    assert celula(resultado, "L4") == Decimal("5514405.94")
    assert celula(resultado, "L5") == Decimal("12278.74")
    assert celula(resultado, "L9") == Decimal("2846486.38")
    assert celula(resultado, "L35") == Decimal("19812433.77")
