"""Compensação do exercício atual informada manualmente por unidade."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.bp.quadro_principal import apurar
from tests.bp.conftest import ENTE, EXERCICIO, FontePorAno, celula

COMPENSACAO = "CONTAS_COMPENSACAO"
ATUAL = "exercicio_atual"
D = Decimal


def _apurar(valores: dict[str, str]):
    return apurar(
        ENTE,
        EXERCICIO,
        FontePorAno({EXERCICIO: {}}),
        anterior="msce_exercicio_anterior",
        valores_atuais=valores,
    )


def test_folhas_zero_e_totalizadora_sao_aplicados_somente_no_atual():
    resultado = _apurar({"C:L2": "100.00", "C:L3": "50.00", "C:L7": "0.00"})

    assert celula(resultado, COMPENSACAO, "L2", ATUAL) == D("100.00")
    assert celula(resultado, COMPENSACAO, "L3", ATUAL) == D("50.00")
    assert celula(resultado, COMPENSACAO, "L1", ATUAL) == D("150.00")
    assert celula(resultado, COMPENSACAO, "L7", ATUAL) == D("0.00")
    assert celula(resultado, COMPENSACAO, "L4", ATUAL) is None
    assert celula(resultado, COMPENSACAO, "L2", "exercicio_anterior") is None
    assert resultado.procedencia.valores_atuais == {
        "C:L2": "100.00", "C:L3": "50.00", "C:L7": "0.00"
    }


@pytest.mark.parametrize("valores, trecho", [
    ({"P:L3": "1.00"}, "use somente C:"),
    ({"C:L999": "1.00"}, "L999"),
    ({"C:L1": "1.00"}, "totalizadora"),
    ({"C:L2": "abc"}, "valor inválido"),
])
def test_validacao_recusa_forma_valor_e_linha_invalidos(valores, trecho):
    from app.services.bp.informados import validar_valores_atuais

    with pytest.raises(ValueError, match=trecho):
        validar_valores_atuais(EXERCICIO, valores)

