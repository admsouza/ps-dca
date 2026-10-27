"""Whitelist das linhas sem conta declarada — o mesmo mecanismo do BF.

A rota recusa o informado inválido **antes** de enfileirar o job; por isso a validação vive fora
da apuração e não toca na fonte de dados.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.dfc.conftest import EXERCICIO


def test_whitelist_e_as_tres_linhas_do_item_17():
    """Scenario: código fora da whitelist é recusado"""
    from app.services.dfc.informados import CODIGOS_SEM_MAPEAMENTO

    assert frozenset({"L16", "L21", "L30"}) == CODIGOS_SEM_MAPEAMENTO


def test_codigo_fora_da_whitelist_e_recusado():
    """Scenario: código fora da whitelist é recusado"""
    from app.services.dfc.informados import LinhaDesconhecida, validar_valores_informados

    with pytest.raises(LinhaDesconhecida):
        validar_valores_informados({"L15": "1.00"})


def test_valor_nao_decimal_e_recusado():
    """Requisito: valor não decimal é recusado antes de apurar."""
    from app.services.dfc.informados import validar_valores_informados

    with pytest.raises(ValueError):
        validar_valores_informados({"L16": "mil reais"})


def test_valor_valido_passa():
    """Requisito: as três linhas aceitam decimal."""
    from app.services.dfc.informados import partir, validar_valores_informados

    valores = {"L16": "12455111116.11", "L21": "0", "L30": "-1.50"}
    validar_valores_informados(valores)
    assert partir(valores)["L16"] == Decimal("12455111116.11")


def test_mapa_da_dfc_vem_do_ipc08():
    """Requisito: o carregador devolve o IPC 08, não o IPC 07 do BO."""
    from app.services.dfc.informados import mapa_dfc

    mapa = mapa_dfc(EXERCICIO)
    assert mapa.vigencia.documento == "IPC08"
    assert len(mapa.linhas) == 84
