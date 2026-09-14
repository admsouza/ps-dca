"""Cenários da leitura da MSC pelo BO — par por competência e apuração mensal.

Sem rede: a fonte é um fake que registra o que foi pedido e devolve registros por competência.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.bo.modelo import Registro

ENTE = 2505204
EXERCICIO = 2025


class FonteFake:
    """Registra as leituras e devolve saldos que crescem com a competência."""

    def __init__(self, por_competencia: dict[int, Decimal] | None = None):
        self.leituras: list[dict] = []
        self._por_competencia = por_competencia or {}

    def registros(self, ente, ano, mes, classe, matriz=None, tipo_saldo=None):
        self.leituras.append({"ente": ente, "ano": ano, "mes": mes, "classe": classe,
                              "matriz": matriz, "tipo_saldo": tipo_saldo})
        valor = self._por_competencia.get(mes)
        if valor is None or classe != 6:
            return []
        # `6.2.1.2` é credora: entra como receita realizada.
        return [Registro(conta="621200000", natureza="C", valor=valor,
                         natureza_receita="11000000")]


@pytest.fixture
def apurar():
    from app.services.bo.quadro_principal import apurar as f
    return f


def test_duas_consultas_por_apuracao(apurar):
    """Scenario: duas consultas por apuração."""
    fonte = FonteFake()
    apurar(ente=ENTE, exercicio=EXERCICIO, fonte=fonte)
    assert [leitura["classe"] for leitura in fonte.leituras] == [5, 6]
    assert {leitura["mes"] for leitura in fonte.leituras} == {12}
    assert len({(leitura["matriz"], leitura["tipo_saldo"]) for leitura in fonte.leituras}) == 1


def test_competencia_12_le_a_matriz_de_encerramento(apurar):
    """Scenario: a troca de origem não muda valor nenhum — origem da competência 12."""
    from app.infra.msc.fonte import Matriz, TipoSaldo

    fonte = FonteFake()
    apurar(ente=ENTE, exercicio=EXERCICIO, fonte=fonte)
    for leitura in fonte.leituras:
        assert leitura["matriz"] is Matriz.ENCERRAMENTO
        assert leitura["tipo_saldo"] is TipoSaldo.ABERTURA


def test_apuracao_mensal_de_um_ente_que_presta_contas_por_mes(apurar):
    """Scenario: apuração mensal de um ente que presta contas por mês.

    Cobre também o Scenario: valores mensais são acumulados até o mês — os acumulados de Cuitegi
    medidos em 2026-09-14 (março, junho, setembro e dezembro de 2025).
    """
    from app.infra.msc.fonte import Matriz, TipoSaldo

    acumulado = {
        3: Decimal("10942851.04"),
        6: Decimal("22477392.39"),
        9: Decimal("34047498.07"),
        12: Decimal("50723704.91"),
    }
    valores = []
    for competencia in (3, 6, 9, 12):
        fonte = FonteFake(acumulado)
        resultado = apurar(ente=ENTE, exercicio=EXERCICIO, fonte=fonte,
                           competencia=competencia)
        celulas = resultado.matriz["bo.quadro_principal.receitas.l2"]
        valores.append(celulas["receitas_realizadas"])

        esperado = ((Matriz.CONSOLIDADA, TipoSaldo.ENCERRAMENTO) if competencia != 12
                    else (Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA))
        for leitura in fonte.leituras:
            assert (leitura["matriz"], leitura["tipo_saldo"]) == esperado
            assert leitura["mes"] == competencia
        assert resultado.procedencia.competencia == competencia

    assert valores == sorted(valores), "acumulados devem ser monotônicos"
    assert valores == [acumulado[m] for m in (3, 6, 9, 12)]


def test_matriz_de_encerramento_lida_pelo_encerramento_e_recusada():
    """Scenario: a matriz de encerramento lida pelo encerramento é recusada."""
    from app.infra.msc.fonte import Matriz, TipoSaldo, fonte_de

    # O par existe só para o BP; nenhum caminho do BO o produz, em nenhuma competência.
    for competencia in range(1, 13):
        fonte = fonte_de("BO", competencia=competencia)
        assert not (fonte.matriz is Matriz.ENCERRAMENTO
                    and fonte.tipo_saldo is TipoSaldo.ENCERRAMENTO)


def test_msce_fora_de_dezembro_e_recusada():
    """Requisito: a matriz de encerramento não é pedida fora da competência 12."""
    from app.infra.msc.fonte import Matriz, TipoSaldo
    from app.infra.msc.siconfi import SiconfiMSC

    with pytest.raises(ValueError):
        SiconfiMSC(http=lambda *a, **k: {"items": [], "hasMore": False}).registros(
            ente=ENTE, ano=EXERCICIO, mes=6, classe=6,
            matriz=Matriz.ENCERRAMENTO, tipo_saldo=TipoSaldo.ABERTURA,
        )


def test_procedencia_completa(apurar):
    """Scenario: procedência completa."""
    fonte = FonteFake({12: Decimal("100.00")})
    resultado = apurar(ente=ENTE, exercicio=EXERCICIO, fonte=fonte)
    procedencia = resultado.procedencia
    assert procedencia.matriz == "encerramento"
    assert procedencia.tipo_saldo == "abertura"
    assert procedencia.competencia == 12
    assert procedencia.classes == (5, 6)


def test_competencia_sem_dados_nao_cai_para_dezembro(apurar):
    """Scenario: competência sem dados não cai para dezembro."""
    fonte = FonteFake({12: Decimal("100.00")})     # só dezembro tem dado
    resultado = apurar(ente=ENTE, exercicio=EXERCICIO, fonte=fonte, competencia=6)
    assert resultado.diagnostico.sem_dados is True
    assert {leitura["mes"] for leitura in fonte.leituras} == {6}
    assert resultado.procedencia.competencia == 6
