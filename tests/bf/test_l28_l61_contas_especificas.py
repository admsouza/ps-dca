"""L28/L61 por crédito/débito mensal — openspec/changes/bf-l28-l61-contas-especificas."""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bf.conftest import ENTE, EXERCICIO, FontePorOrigem
from tests.bo.conftest import registro


class FontePorMes(FontePorOrigem):
    """Como `FontePorOrigem`, mas o `period_change` devolve registros distintos por competência."""

    def __init__(self, por_mes: dict[int, list]):
        super().__init__({})
        self._por_mes = por_mes

    def registros(self, ente: int, ano: int, mes: int, classe: int, matriz=None, tipo_saldo=None):
        self.chamadas.append({"ente": ente, "ano": ano, "mes": mes, "classe": classe,
                              "matriz": matriz, "tipo_saldo": tipo_saldo})
        if getattr(tipo_saldo, "name", str(tipo_saldo)) == "PERIODO":
            return list(self._por_mes.get(mes, []))
        return []


def _id_de(resultado, codigo: str) -> str:
    return next(linha.id for linha in resultado.mapa.linhas
                if linha.quadro == "QUADRO_PRINCIPAL" and linha.codigo == codigo)


def test_l28_soma_creditos_de_todos_os_meses(apurar_bf):
    """Scenario: L28 soma os créditos de todos os meses."""
    conta = "1.1.3.5.2.00.00"
    por_mes = {
        1: [registro(conta, "C", "100.00", fonte_recursos="1860")],
        6: [registro(conta, "C", "250.00", fonte_recursos="1861"),
            registro(conta, "D", "40.00", fonte_recursos="1861")],
        12: [registro(conta, "C", "10.00", fonte_recursos="1869")],
    }
    resultado = apurar_bf(ENTE, EXERCICIO, FontePorMes(por_mes))
    l28 = _id_de(resultado, "L28")
    assert resultado.matriz[l28]["exercicio_atual"] == Decimal("360.00")   # débito não subtraído


def test_l28_ignora_fonte_fora_das_extraorcamentarias(apurar_bf):
    """Scenario: L28 ignora fonte fora das extraorçamentárias."""
    conta = "1.1.3.5.2.00.00"
    por_mes = {
        1: [
            registro(conta, "C", "10.00", fonte_recursos="1860"),
            registro(conta, "C", "99.00", fonte_recursos="1500"),
        ],
    }
    resultado = apurar_bf(ENTE, EXERCICIO, FontePorMes(por_mes))
    l28 = _id_de(resultado, "L28")
    assert resultado.matriz[l28]["exercicio_atual"] == Decimal("10.00")


def test_l28_conta_sem_escrituracao_contribui_zero(apurar_bf):
    """Scenario: conta sem escrituração contribui zero."""
    resultado = apurar_bf(ENTE, EXERCICIO, FontePorMes({}))
    l28 = _id_de(resultado, "L28")
    assert resultado.matriz[l28]["exercicio_atual"] == Decimal("0.00")
    assert not any(n.rule_id == l28 for n in resultado.diagnostico.nao_apuradas)


def test_l61_soma_debitos_de_todos_os_meses(apurar_bf):
    """Scenario: L61 soma os débitos de todos os meses."""
    conta = "1.1.3.8.1.06.00"
    por_mes = {
        3: [registro(conta, "D", "500.00", fonte_recursos="1860"),
            registro(conta, "C", "30.00", fonte_recursos="1860")],
        9: [registro(conta, "D", "75.00", fonte_recursos="1869")],
    }
    resultado = apurar_bf(ENTE, EXERCICIO, FontePorMes(por_mes))
    l61 = _id_de(resultado, "L61")
    assert resultado.matriz[l61]["exercicio_atual"] == Decimal("575.00")   # crédito não subtraído


def test_l61_soma_debitos_dos_doze_meses_nos_dois_exercicios(apurar_bf):
    """Scenario: L61 soma os débitos dos doze meses nos dois exercícios."""
    from tests.bf.conftest import fonte_com

    conta = "1.1.3.5.2.00.00"
    fonte = fonte_com(
        p2025={1: [registro(conta, "D", "10.00", fonte_recursos="1860"),
                   registro(conta, "C", "4.00", fonte_recursos="1860")]},
        p2024={1: [registro(conta, "D", "3.00", fonte_recursos="1861"),
                   registro(conta, "C", "8.00", fonte_recursos="1861")]},
        a2024={1: [registro(conta, "C", "7.00", fonte_recursos="1860")]},
        a2025={}, e2025={},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    l61 = resultado.matriz[_id_de(resultado, "L61")]
    l28 = resultado.matriz[_id_de(resultado, "L28")]
    assert l61["exercicio_atual"] == Decimal("120.00")        # 10 × 12; crédito não entra
    assert l61["exercicio_anterior"] == Decimal("36.00")      # 3 × 12 do ano anterior
    assert l28["exercicio_anterior"] == Decimal("7.00")       # snapshot, não os 8 × 12


def test_l61_ignora_fonte_fora_das_extraorcamentarias(apurar_bf):
    """Scenario: L61 ignora fonte fora das extraorçamentárias."""
    conta = "1.1.3.8.1.06.00"
    por_mes = {
        3: [
            registro(conta, "D", "10.00", fonte_recursos="1860"),
            registro(conta, "D", "99.00", fonte_recursos="1500"),
            registro(conta, "C", "4.00", fonte_recursos="1860"),
        ],
    }
    resultado = apurar_bf(ENTE, EXERCICIO, FontePorMes(por_mes))
    l61 = _id_de(resultado, "L61")
    assert resultado.matriz[l61]["exercicio_atual"] == Decimal("10.00")


def test_l28_l61_fora_da_whitelist_de_override_manual():
    """Scenario: L28/L61 fora da whitelist de override manual."""
    from app.services.bf.informados import LinhaDesconhecida, validar_valores_sem_mapeamento

    with pytest.raises(LinhaDesconhecida):
        validar_valores_sem_mapeamento({"L28": "1.00"})
    with pytest.raises(LinhaDesconhecida):
        validar_valores_sem_mapeamento({"L61": "1.00"})
