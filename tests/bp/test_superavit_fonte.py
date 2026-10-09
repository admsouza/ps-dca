"""Quadro do Superávit / Déficit Financeiro por fonte (IPC 04, p. 13)."""
from __future__ import annotations

from decimal import Decimal

from app.services.bp.quadro_principal import apurar
from tests.bo.conftest import registro
from tests.bp.conftest import ENTE, EXERCICIO, FontePorAno, celula
from tests.bp.test_anterior_publicado import DCAFake

QUADRO = "SUPERAVIT_DEFICIT"
ATUAL = "exercicio_atual"
ANTERIOR = "exercicio_anterior"


def _fonte(atual: list, anterior: list | None = None) -> FontePorAno:
    return FontePorAno({
        EXERCICIO: {8: atual},
        EXERCICIO - 1: {8: anterior or []},
    })


def _saldo(conta: str, natureza: str, valor: str, fonte: str, complemento: str = ""):
    return registro(conta, natureza, valor, fonte_recursos=fonte, complemento_fonte=complemento)


def _codigos(resultado) -> list[str]:
    return [linha.codigo for linha in resultado.mapa.linhas if linha.quadro == QUADRO]


def test_cide_de_cuitegi_2025(apurar_bp):
    """Scenario: CIDE de Cuitegi 2025"""
    fonte = _fonte(
        [_saldo("821110100", "C", "9262.55", "1750"),
         _saldo("821110200", "C", "3617.06", "1750")],
        [_saldo("821110100", "C", "835.46", "1750")],
    )
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, QUADRO, "17500000") == Decimal("12879.61")
    assert celula(resultado, QUADRO, "17500000", ANTERIOR) == Decimal("835.46")


def test_taxa_de_administracao_do_rpps(apurar_bp):
    """Scenario: taxa de administração do RPPS"""
    fonte = _fonte(
        [_saldo("821110100", "C", "61862.85", "1802")],
        [_saldo("821110100", "D", "212922.03", "1802")],
    )
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, QUADRO, "18020000") == Decimal("61862.85")
    assert celula(resultado, QUADRO, "18020000", ANTERIOR) == Decimal("-212922.03")


def test_complemento_e_linha_propria(apurar_bp):
    """Scenario: complemento é linha própria"""
    fonte = _fonte([
        _saldo("821110100", "C", "10.00", "1500"),
        _saldo("821110100", "C", "3.00", "1500", "1001"),
    ])
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, QUADRO, "15000000") == Decimal("10.00")
    assert celula(resultado, QUADRO, "15001001") == Decimal("3.00")
    rotulo = next(linha.rotulo for linha in resultado.mapa.linhas
                  if linha.codigo == "15001001")
    assert "Impostos" in next(linha.rotulo for linha in resultado.mapa.linhas
                              if linha.codigo == "15000000")
    assert "manutenção" in rotulo


def test_fonte_de_exercicio_anterior_da_vinculacao_entra(apurar_bp):
    """Scenario: fonte de exercício anterior da vinculação entra"""
    fonte = _fonte(
        [_saldo("821110200", "D", "15855.84", "2500")],
        [_saldo("821110100", "D", "701304.54", "2500"),
         _saldo("821110200", "D", "1283427.34", "2500")],
    )
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, QUADRO, "25000000") == Decimal("-15855.84")
    assert celula(resultado, QUADRO, "25000000", ANTERIOR) == Decimal("-1984731.88")
    assert celula(resultado, QUADRO, "Total") == Decimal("-15855.84")


def test_totais_somam_as_linhas(apurar_bp):
    """Scenario: totais de Cuitegi"""
    fonte = _fonte(
        [_saldo("821110100", "C", "10.00", "1750"),
         _saldo("821110200", "D", "4.00", "2500")],
        [_saldo("821110100", "C", "7.00", "1750")],
    )
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, QUADRO, "Total") == Decimal("6.00")
    assert celula(resultado, QUADRO, "Total", ANTERIOR) == Decimal("7.00")


def test_saldo_so_no_ano_anterior_ainda_aparece(apurar_bp):
    """Scenario: saldo só no ano anterior ainda aparece"""
    fonte = _fonte([], [_saldo("821110100", "C", "835.46", "1750")])
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, QUADRO, "17500000") == Decimal("0.00")
    assert celula(resultado, QUADRO, "17500000", ANTERIOR) == Decimal("835.46")


def test_linha_zerada_nao_aparece(apurar_bp):
    """Requisito: linha com saldo zero nas duas colunas não aparece."""
    fonte = _fonte([
        _saldo("821110100", "C", "5.00", "1500"),
        _saldo("821110100", "D", "5.00", "1500"),
    ])
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert "15000000" not in _codigos(resultado)
    assert celula(resultado, QUADRO, "Total") == Decimal("0.00")


def test_as_duas_visoes_sao_iguais(apurar_bp):
    """Scenario: as duas visões são iguais"""
    fonte = _fonte([_saldo("821110100", "C", "10.00", "1750")])
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert resultado.visoes["consolidado"].matriz == resultado.matriz


def test_coluna_anterior_nao_vem_do_iab():
    """Requisito: a coluna anterior deste quadro é a MSC do ano anterior, com o I-AB vazio."""
    fonte = _fonte(
        [_saldo("821110100", "C", "10.00", "1750")],
        [_saldo("821110100", "C", "4.00", "1750")],
    )
    resultado = apurar(ENTE, EXERCICIO, fonte, dca=DCAFake([]))
    assert celula(resultado, QUADRO, "17500000", ANTERIOR) == Decimal("4.00")


def test_compensacao_continua_nao_apurada(apurar_bp):
    """Scenario: compensação fora de escopo"""
    fonte = _fonte([_saldo("821110100", "C", "10.00", "1750")])
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    compensacao = [linha for linha in resultado.mapa.linhas if linha.quadro == "CONTAS_COMPENSACAO"]
    assert compensacao
    assert all(set(resultado.matriz[linha.id].values()) == {None} for linha in compensacao)
