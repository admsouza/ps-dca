"""Domínio do recorte: chave da unidade, grupos de poder e visibilidade pelo poder do hub.

Change `pipeline-dca-por-unidade-gestora`.
"""
from __future__ import annotations

from app.domain import recorte
from tests.bo.conftest import registro

UNIDADES = {"ug:1": "10131", "ug:2": "10132", "ug:4": "20231", "ug:0": ""}


def test_unidade_e_a_ug_quando_a_fonte_a_informa():
    """Scenario: ente com UG"""
    r = registro("621200000", "C", "1.00", poder_orgao="10131")._replace(unidade_gestora="3")
    assert recorte.unidade(r) == "ug:3"


def test_unidade_e_o_po_quando_nao_ha_ug():
    """Scenario: ente sem UG / registro sem PO"""
    assert recorte.unidade(registro("621200000", "C", "1.00", poder_orgao="20231")) == "po:20231"
    assert recorte.unidade(registro("621200000", "C", "1.00")) == "po:"


def test_recortes_por_grupo_de_poder_e_por_unidade():
    """Requisito: recortes apurados no mesmo job (tabela de chaves)"""
    assert recorte.recortes(UNIDADES) == {
        "poder:executivo": {"ug:1", "ug:2"},
        "poder:legislativo": {"ug:4"},
        "poder:executivo+legislativo": {"ug:1", "ug:2", "ug:4"},
        "ug:0": {"ug:0"}, "ug:1": {"ug:1"}, "ug:2": {"ug:2"}, "ug:4": {"ug:4"},
    }


def test_visiveis_pelo_poder():
    """Requisito: recortes visíveis pelo poder autorizado no hub"""
    chaves = ["consolidado", *recorte.recortes(UNIDADES)]
    assert recorte.visiveis(chaves, UNIDADES, ["consolidado"]) == [
        "consolidado", "poder:executivo", "poder:legislativo", "poder:executivo+legislativo",
        "ug:0", "ug:1", "ug:2", "ug:4"]
    assert recorte.visiveis(chaves, UNIDADES, ["executivo"]) == [
        "poder:executivo", "ug:1", "ug:2"]
    assert recorte.visiveis(chaves, UNIDADES, ["legislativo"]) == ["poder:legislativo", "ug:4"]
    assert recorte.visiveis(chaves, UNIDADES, ["executivo", "legislativo"]) == [
        "poder:executivo", "poder:legislativo", "poder:executivo+legislativo",
        "ug:1", "ug:2", "ug:4"]
    assert recorte.visiveis(chaves, UNIDADES, ["judiciario"]) == []
    assert recorte.visiveis(chaves, UNIDADES, []) == []


def test_padrao_pelo_poder():
    """Requisito: padrão sem `recorte`"""
    assert recorte.padrao(["consolidado", "executivo"]) == "consolidado"
    assert recorte.padrao(["executivo"]) == "poder:executivo"
    assert recorte.padrao(["legislativo"]) == "poder:legislativo"
    assert recorte.padrao(["legislativo", "executivo"]) == "poder:executivo+legislativo"
    assert recorte.padrao(["judiciario"]) is None
    assert recorte.padrao([]) is None


def test_chave_valida():
    """Scenario: recorte malformado"""
    for chave in ("consolidado", "poder:executivo", "poder:executivo+legislativo", "ug:0",
                  "ug:12", "po:20231", "po:"):
        assert recorte.valida(chave), chave
    for chave in ("99", "ug:", "ug:x", "po:2023", "poder:judiciario", "consolidado "):
        assert not recorte.valida(chave), chave
