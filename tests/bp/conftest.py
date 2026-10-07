"""Fixtures da apuração do Balanço Patrimonial (F1 do BP).

Contrato exercitado:

    app.services.bp.quadro_principal  apurar(ente, exercicio, fonte, ...) -> Resultado
    app.domain.bo.modelo              Registro.financeiro_permanente ("F" | "P" | "")

O BP lê uma origem só — `MSCE`/encerramento —, no exercício e no anterior. A fonte devolve
registros por `(ano, classe)`; o tipo de saldo pedido fica registrado para asserção.
"""
from __future__ import annotations

import pytest

from tests.bo.conftest import FonteFake, saldo

ENTE = 2505204          # Cuitegi/PB — gabarito do BP em docs/entes-homologacao/cuitegi/
EXERCICIO = 2025


@pytest.fixture
def apurar_bp():
    from app.services.bp.quadro_principal import apurar
    return apurar


class FontePorAno(FonteFake):
    """`{ano: {classe: [registros]}}`."""

    def __init__(self, por_ano: dict[int, dict[int, list]]):
        super().__init__({}, rotulo="por-ano")
        self._por_ano = por_ano

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz=None, tipo_saldo=None):
        self.chamadas.append({"ente": ente, "ano": ano, "mes": mes, "classe": classe,
                              "matriz": matriz, "tipo_saldo": tipo_saldo})
        return list(self._por_ano.get(ano, {}).get(classe, []))


def fp(conta: str, valor: str, atributo: str = ""):
    """Registro com saldo positivo na direção da conta e o atributo F/P do fato."""
    return saldo(conta, valor)._replace(financeiro_permanente=atributo)


def celula(resultado, quadro: str, codigo: str, coluna: str = "exercicio_atual"):
    rule_id = next(linha.id for linha in resultado.mapa.linhas
                   if linha.quadro == quadro and linha.codigo == codigo)
    return resultado.matriz[rule_id][coluna]
