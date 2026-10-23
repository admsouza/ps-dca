"""A entrada da DVP não altera BO, BF nem BP — as bases canônicas seguem isoladas por diretório."""
from __future__ import annotations

import pytest

from app.infra.regras.carregador import carregar

EXERCICIO = 2025


@pytest.mark.parametrize("demonstrativo, documento, linhas", [
    ("bo", "IPC07", 69),
    ("bf", "IPC06", 80),
    ("bp", "IPC04", 58),
])
def test_anexos_ja_apurados_permanecem_iguais(demonstrativo, documento, linhas):
    """Scenario: anexos já apurados permanecem iguais.

    O carregador varre `knowledge/rules/<demonstrativo>/`: regra da DVP num diretório errado
    entraria no mapa do vizinho sem erro nenhum, e o demonstrativo sairia com linha a mais.
    """
    mapa = carregar(EXERCICIO, demonstrativo=demonstrativo)
    assert mapa.vigencia.documento == documento
    assert len(mapa.linhas) == linhas
    assert {linha.id.split(".")[0] for linha in mapa.linhas} == {demonstrativo}
