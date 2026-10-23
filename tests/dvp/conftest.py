"""Fixtures da DVP. O serviço ainda não existe: a importação acontece dentro da fixture.

Contrato: `app.services.dvp.quadro_principal.apurar`, mesma assinatura do BP,
coluna anterior pela MSC (`Anterior.MSCE`).
"""
from __future__ import annotations

from functools import partial

import pytest

JP = 2507507
POA = 4314902
EXERCICIO = 2025
ATUAL = "exercicio_atual"
ANTERIOR = "exercicio_anterior"


@pytest.fixture
def apurar_dvp():
    from app.services.dvp.quadro_principal import Anterior, apurar

    return partial(apurar, anterior=Anterior.MSCE)


def celula(resultado, codigo: str, coluna: str = ATUAL):
    rule_id = next(
        linha.id for linha in resultado.mapa.linhas
        if linha.quadro == "QUADRO_PRINCIPAL" and linha.codigo == codigo
    )
    return resultado.matriz[rule_id][coluna]
