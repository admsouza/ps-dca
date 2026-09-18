"""Fixtures da apuração do Balanço Financeiro (F1 do BF).

Contrato exercitado:

    app.infra.regras.carregador       carregar(exercicio, demonstrativo="bf") -> MapaBO
    app.domain.bo.saldo               saldo_da_celula_por_conta(registros, contas, direcao)
    app.domain.bo.matriz              apurar(mapa, registros, direcao, por_conta=False,
                                             registros_por_regra=None) -> Matriz
    app.services.bf.quadro_principal  apurar(ente, exercicio, fonte, ...) -> Resultado

Reusa os dublês do BO: o motor é o mesmo, medido em 2026-09-18 apurando o BF inteiro sem
alteração (`docs/evidencia-bf-medicao-2026-09-18.md`).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bo.conftest import DirecaoFake, FonteFake, registro, saldo  # noqa: F401

ENTE = 2611606          # Recife — o caso de referência do BF: 66 linhas 1:1 com o IPC 06
EXERCICIO = 2025


@pytest.fixture
def apurar_bf():
    from app.services.bf.quadro_principal import apurar
    return apurar


@pytest.fixture
def carregar_mapa():
    from app.infra.regras.carregador import carregar
    return carregar


@pytest.fixture
def mapa_bf(carregar_mapa):
    return carregar_mapa(exercicio=EXERCICIO, demonstrativo="bf")


class FontePorOrigem(FonteFake):
    """Fonte que devolve conjuntos diferentes por (exercício, tipo de saldo).

    Existe porque o BF lê três origens: o exercício, o encerramento do exercício e o exercício
    anterior — medido, não suposto (evidência §N1 e §G2).
    """

    def __init__(self, por_origem: dict[tuple[int, str], dict[int, list]]):
        super().__init__({}, rotulo="por-origem")
        self._por_origem = por_origem

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz=None, tipo_saldo=None):
        self.chamadas.append({"ente": ente, "ano": ano, "mes": mes, "classe": classe,
                              "matriz": matriz, "tipo_saldo": tipo_saldo})
        chave = (ano, getattr(tipo_saldo, "name", str(tipo_saldo)))
        return list(self._por_origem.get(chave, {}).get(classe, []))


def fonte_com(**por_origem) -> FontePorOrigem:
    """`fonte_com(a2025={6: [...]}, e2025={5: [...]}, a2024={1: [...]})`."""
    mapa = {}
    for chave, classes in por_origem.items():
        tipo = {"a": "ABERTURA", "e": "ENCERRAMENTO", "p": "PERIODO"}[chave[0]]
        mapa[(int(chave[1:]), tipo)] = classes
    return FontePorOrigem(mapa)


def dec(valor: str) -> Decimal:
    return Decimal(valor)
