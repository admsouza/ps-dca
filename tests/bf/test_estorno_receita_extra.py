"""L27 e L60 líquidos só quando a fonte expõe o estorno de receita extra."""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bf.conftest import ENTE, EXERCICIO, FontePorOrigem, fonte_com
from tests.bo.conftest import registro


def _deposito(natureza: str, valor: str):
    return registro("218800000", natureza, valor, fonte_recursos="1860")


def _fonte(receitas: dict[int, Decimal] | None, despesas: dict[int, Decimal] | None = None):
    base = fonte_com(
        p2025={2: [_deposito("C", "100.00"), _deposito("D", "80.00")]},
        p2024={2: [_deposito("C", "100.00"), _deposito("D", "80.00")]},
    )
    if receitas is None:
        return _SoMes1(base._por_origem)
    return _ComEstorno(base._por_origem, receitas, despesas or {})


class _SoMes1(FontePorOrigem):
    """O BF lê os doze meses; o lançamento de teste existe só em janeiro."""

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz=None, tipo_saldo=None):
        if getattr(tipo_saldo, "name", "") == "PERIODO" and mes != 1:
            return []
        return super().registros(ente, ano, mes, classe, matriz, tipo_saldo)


class _ComEstorno(_SoMes1):
    def __init__(self, por_origem, receitas: dict[int, Decimal], despesas: dict[int, Decimal]):
        super().__init__(por_origem)
        self.receitas = receitas
        self.despesas = despesas

    def estorno_receita_extra(self, exercicio: int) -> Decimal:
        return self._total(self.receitas, exercicio)

    def estorno_despesa_extra(self, exercicio: int) -> Decimal:
        return self._total(self.despesas, exercicio)

    @staticmethod
    def _total(valores: dict[int, Decimal], exercicio: int) -> Decimal:
        if exercicio not in valores:
            from app.infra.msc.publicsoft import EstornoIndisponivel

            raise EstornoIndisponivel(exercicio)
        return valores[exercicio]


def _valor(resultado, codigo: str, coluna: str):
    linha = next(item for item in resultado.mapa.linhas if item.codigo == codigo)
    return resultado.matriz[linha.id][coluna]


def test_publicsoft_abate_receita_nas_duas_e_despesa_so_na_l60(apurar_bf):
    """Scenario: PublicSoft abate receita em L27 e L60, e despesa só em L60."""
    fonte = _fonte(
        {2025: Decimal("10.00"), 2024: Decimal("3.00")},
        {2025: Decimal("4.00"), 2024: Decimal("1.00")},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)

    assert _valor(resultado, "L27", "exercicio_atual") == Decimal("90.00")
    assert _valor(resultado, "L27", "exercicio_anterior") == Decimal("97.00")
    assert _valor(resultado, "L60", "exercicio_atual") == Decimal("66.00")
    assert _valor(resultado, "L60", "exercicio_anterior") == Decimal("76.00")
    assert _valor(resultado, "L24", "exercicio_atual") == Decimal("90.00")
    assert _valor(resultado, "L57", "exercicio_atual") == Decimal("66.00")
    assert _valor(resultado, "L25", "exercicio_atual") == Decimal("0.00")
    assert resultado.procedencia.estorno_receita_extra == {"2025": "10.00", "2024": "3.00"}
    assert resultado.procedencia.estorno_despesa_extra == {"2025": "4.00", "2024": "1.00"}


def test_siconfi_nao_abate(apurar_bf):
    """Scenario: SICONFI não abate."""
    resultado = apurar_bf(ENTE, EXERCICIO, _fonte(None))

    assert _valor(resultado, "L27", "exercicio_atual") == Decimal("100.00")
    assert _valor(resultado, "L60", "exercicio_atual") == Decimal("80.00")
    assert resultado.procedencia.estorno_receita_extra is None
    assert resultado.procedencia.estorno_despesa_extra is None


def test_relatorio_sem_total_geral_nao_publica_o_bruto(apurar_bf):
    """Scenario: Relatório sem total geral não publica o bruto."""
    from app.infra.msc.publicsoft import EstornoIndisponivel

    with pytest.raises(EstornoIndisponivel):
        apurar_bf(ENTE, EXERCICIO, _fonte({}))
