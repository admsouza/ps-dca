"""L27 e L60 líquidos só quando a fonte expõe o estorno de receita extra."""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bf.conftest import ENTE, EXERCICIO, FontePorOrigem, fonte_com
from tests.bo.conftest import registro


def _deposito(natureza: str, valor: str):
    return registro("218800000", natureza, valor, fonte_recursos="1860")


def _fonte(estornos: dict[int, Decimal] | None):
    base = fonte_com(
        p2025={2: [_deposito("C", "100.00"), _deposito("D", "80.00")]},
        p2024={2: [_deposito("C", "100.00"), _deposito("D", "80.00")]},
    )
    if estornos is None:
        return _SoMes1(base._por_origem)
    return _ComEstorno(base._por_origem, estornos)


class _SoMes1(FontePorOrigem):
    """O BF lê os doze meses; o lançamento de teste existe só em janeiro."""

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz=None, tipo_saldo=None):
        if getattr(tipo_saldo, "name", "") == "PERIODO" and mes != 1:
            return []
        return super().registros(ente, ano, mes, classe, matriz, tipo_saldo)


class _ComEstorno(_SoMes1):
    def __init__(self, por_origem, estornos: dict[int, Decimal]):
        super().__init__(por_origem)
        self.estornos = estornos

    def estorno_receita_extra(self, exercicio: int) -> Decimal:
        if exercicio not in self.estornos:
            from app.infra.msc.publicsoft import EstornoIndisponivel

            raise EstornoIndisponivel(exercicio)
        return self.estornos[exercicio]


def _valor(resultado, codigo: str, coluna: str):
    linha = next(item for item in resultado.mapa.linhas if item.codigo == codigo)
    return resultado.matriz[linha.id][coluna]


def test_publicsoft_abate_o_total_geral_nas_duas_colunas(apurar_bf):
    """Scenario: PublicSoft abate o total geral nas duas colunas."""
    fonte = _fonte({2025: Decimal("10.00"), 2024: Decimal("3.00")})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)

    assert _valor(resultado, "L27", "exercicio_atual") == Decimal("90.00")
    assert _valor(resultado, "L27", "exercicio_anterior") == Decimal("97.00")
    assert _valor(resultado, "L60", "exercicio_atual") == Decimal("70.00")
    assert _valor(resultado, "L60", "exercicio_anterior") == Decimal("77.00")
    assert _valor(resultado, "L24", "exercicio_atual") == Decimal("90.00")
    assert _valor(resultado, "L57", "exercicio_atual") == Decimal("70.00")
    assert _valor(resultado, "L25", "exercicio_atual") == Decimal("0.00")
    assert resultado.procedencia.estorno_receita_extra == {
        "2025": "10.00",
        "2024": "3.00",
    }


def test_siconfi_nao_abate(apurar_bf):
    """Scenario: SICONFI não abate."""
    resultado = apurar_bf(ENTE, EXERCICIO, _fonte(None))

    assert _valor(resultado, "L27", "exercicio_atual") == Decimal("100.00")
    assert _valor(resultado, "L60", "exercicio_atual") == Decimal("80.00")
    assert resultado.procedencia.estorno_receita_extra is None


def test_relatorio_sem_total_geral_nao_publica_o_bruto(apurar_bf):
    """Scenario: Relatório sem total geral não publica o bruto."""
    from app.infra.msc.publicsoft import EstornoIndisponivel

    with pytest.raises(EstornoIndisponivel):
        apurar_bf(ENTE, EXERCICIO, _fonte({}))
