"""Quadro Anexo do BF — a receita orçamentária por fonte, em bruto, dedução e líquido.

O quadro principal apresenta a receita já líquida (`L1`); é o anexo que abre as três parcelas. As
colunas `(c)` e `(f)` são **derivadas** da própria linha, pelo mesmo mecanismo que o BO usa em
`saldo = c − b`.
"""
from __future__ import annotations

from decimal import Decimal

from tests.bf.conftest import ENTE, EXERCICIO, fonte_com
from tests.bo.conftest import registro, saldo

ANEXO = "QUADRO_ANEXO"


def _por_codigo(resultado, quadro=ANEXO):
    return {linha.codigo: resultado.matriz[linha.id]
            for linha in resultado.mapa.linhas if linha.quadro == quadro}


def test_saldo_do_anexo_e_derivado_nao_somado(apurar_bf):
    """Scenario: saldo do anexo é derivado, não somado"""
    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500"),
                   saldo("621310100", "150.00", fonte_recursos="1500")]},
        e2025={}, a2024={},
    )
    anexo = _por_codigo(apurar_bf(ENTE, EXERCICIO, fonte))
    assert anexo["L1"]["receita_orcamentaria_atual"] == Decimal("1000.00")
    assert anexo["L1"]["deducoes_atual"] == Decimal("150.00")
    assert anexo["L1"]["saldo_atual"] == Decimal("850.00")
    assert anexo["L14"]["saldo_atual"] == Decimal("850.00")


def test_coluna_derivada_com_parcela_nao_apurada(apurar_bf):
    """Scenario: coluna derivada com parcela não apurada

    Subtrair com uma parcela ausente afirmaria um líquido que não se sabe.
    """
    from app.infra.pcasp.natureza import do_pcasp

    class SemDirecao:
        def credora(self, conta):
            return None if conta.startswith("6213") else do_pcasp().credora(conta)

        def credora_prefixo(self, prefixo):
            return do_pcasp().credora_prefixo(prefixo)

    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500"),
                   registro("621310100", "D", "150.00", fonte_recursos="1500")]},
        e2025={}, a2024={},
    )
    anexo = _por_codigo(apurar_bf(ENTE, EXERCICIO, fonte, direcao=SemDirecao()))
    assert anexo["L1"]["deducoes_atual"] is None
    assert anexo["L1"]["saldo_atual"] is None, "não pode subtrair com a parcela que existe"


def test_total_do_anexo_fecha_nas_seis_colunas(apurar_bf):
    """Requisito: `L14` fecha `L1 + L2 + L10` em cada uma das seis colunas."""
    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500"),
                   saldo("621200000", "300.00", fonte_recursos="1540"),
                   saldo("621200000", "70.00", fonte_recursos="1800")]},
        a2024={6: [saldo("621200000", "900.00", fonte_recursos="1500")]},
        e2025={}, e2024={}, a2023={},
    )
    anexo = _por_codigo(apurar_bf(ENTE, EXERCICIO, fonte))
    for coluna in ("receita_orcamentaria_atual", "deducoes_atual", "saldo_atual",
                   "receita_orcamentaria_anterior", "deducoes_anterior", "saldo_anterior"):
        parcelas = sum(anexo[c][coluna] or Decimal(0) for c in ("L1", "L2", "L10"))
        assert anexo["L14"][coluna] == parcelas, coluna


def test_colunas_do_exercicio_anterior_vem_do_ano_anterior(apurar_bf):
    """Requisito: no anexo, como no principal, a coluna anterior é o exercício anterior."""
    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500")]},
        a2024={6: [saldo("621200000", "800.00", fonte_recursos="1500")]},
        e2025={}, e2024={}, a2023={},
    )
    anexo = _por_codigo(apurar_bf(ENTE, EXERCICIO, fonte))
    assert anexo["L1"]["receita_orcamentaria_atual"] == Decimal("1000.00")
    assert anexo["L1"]["receita_orcamentaria_anterior"] == Decimal("800.00")


def test_o_anexo_detalha_o_que_o_principal_traz_liquido(apurar_bf):
    """Scenario: o anexo detalha o que o principal traz líquido"""
    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500"),
                   saldo("621310100", "150.00", fonte_recursos="1500")]},
        e2025={}, a2024={},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    anexo = _por_codigo(resultado)
    principal = _por_codigo(resultado, "QUADRO_PRINCIPAL")
    assert anexo["L14"]["saldo_atual"] == principal["L1"]["exercicio_atual"]
    assert resultado.diagnostico.conferencia_anexo is not None
    assert resultado.diagnostico.conferencia_anexo["diferenca"] == Decimal("0.00")


def test_fonte_ausente_vira_residuo_nao_rateio(apurar_bf):
    """Scenario: fonte ausente vira resíduo, não rateio

    Medido em Recife: 450.202.814,72 em dois registros da conta sintética `6.2.1.2.0.00.00`.
    """
    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500"),
                   saldo("621200000", "450.00", fonte_recursos="")]},
        e2025={}, a2024={},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    anexo = _por_codigo(resultado)
    assert anexo["L14"]["receita_orcamentaria_atual"] == Decimal("1000.00"), "sem rateio"
    residuos = [r for r in resultado.diagnostico.residuos if r.campo == "fonte_recurso"]
    assert residuos and residuos[0].valor == Decimal("450.00")
