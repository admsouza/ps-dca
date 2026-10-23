"""Conferência viva da DVP contra o `DCA-Anexo I-HI` do SICONFI.

Vai à rede. Fora da suíte padrão (`-m "not vivo"`); rode com `python -m pytest -m vivo`.
Espelha a medição de 2026-10-23 registrada em `openspec/changes/dvp-quadro-principal/`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.dvp.conftest import ANTERIOR, EXERCICIO, JP, POA, celula

pytestmark = pytest.mark.vivo


def test_joao_pessoa_2025_fecha_o_quadro(apurar_dvp):
    """Scenario: João Pessoa 2025 fecha o quadro."""
    from app.infra.msc.fonte import Matriz, TipoSaldo
    from app.infra.msc.siconfi import SiconfiMSC

    resultado = apurar_dvp(JP, EXERCICIO, SiconfiMSC())
    assert resultado.procedencia.matriz == str(Matriz.ENCERRAMENTO)
    assert resultado.procedencia.tipo_saldo == str(TipoSaldo.ABERTURA)
    assert resultado.procedencia.classes == (3, 4)
    assert celula(resultado, "L2") == Decimal("397963739.37")
    assert celula(resultado, "L6") == Decimal("11722481279.59")
    assert celula(resultado, "L14") == Decimal("9199369111.48")
    assert celula(resultado, "L1") == Decimal("17319103824.61")
    assert celula(resultado, "L9") == Decimal("17046926343.10")
    assert celula(resultado, "L19") == Decimal("272177481.51")


def test_porto_alegre_2025_fecha_os_totais(apurar_dvp):
    """Scenario: Porto Alegre 2025 fecha os totais."""
    from app.infra.msc.siconfi import SiconfiMSC

    resultado = apurar_dvp(POA, EXERCICIO, SiconfiMSC())
    assert celula(resultado, "L1") == Decimal("53603764288.49")
    assert celula(resultado, "L9") == Decimal("54984708163.98")
    assert celula(resultado, "L19") == Decimal("-1380943875.49")


def _total_publicado(ente: int, classe: str) -> Decimal:
    from app.infra.siconfi.dca import SiconfiDCA
    from app.services.bp.publicado import _CONTA, _valor

    for item in SiconfiDCA().itens(ente, EXERCICIO - 1, "DCA-Anexo I-HI"):
        achado = _CONTA.match(str(item.get("cod_conta") or ""))
        if not achado:
            continue
        digitos = "".join(achado.group(1).split("."))
        if digitos.startswith(classe) and set(digitos[1:]) <= {"0"}:
            return _valor(item)
    raise AssertionError(f"I-HI {EXERCICIO - 1} sem total da classe {classe} para {ente}")


def test_coluna_anterior_e_o_ihi_de_2024(apurar_dvp):
    """Scenario: coluna anterior é o I-HI do ano anterior."""
    from app.infra.msc.siconfi import SiconfiMSC

    fonte = SiconfiMSC()
    for ente in (JP, POA):
        resultado = apurar_dvp(ente, EXERCICIO, fonte)
        assert celula(resultado, "L1", ANTERIOR) == _total_publicado(ente, "4")
        assert celula(resultado, "L9", ANTERIOR) == _total_publicado(ente, "3")
