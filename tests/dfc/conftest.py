"""Fixtures da DFC (IPC 08). O serviço ainda não existe: a importação acontece na fixture.

Contrato exercitado:

    app.services.dfc.quadro_principal  apurar(ente, exercicio, fonte, ...) -> Resultado
    app.services.dfc.informados        CODIGOS_SEM_MAPEAMENTO, validar_valores_informados

A DFC lê `MSCE`/abertura, classes 1 a 6, em N e em N−1 — `L35` é o caixa de N−1 (D3).
"""
from __future__ import annotations

import pytest

POA = 4314902           # Porto Alegre/RS — gabarito em docs/entes-homologacao/porto-alegre/
CUITEGI = 2505204       # Cuitegi/PB — DFC **consolidada**, mesmo recorte da MSC
EXERCICIO = 2025
ATUAL = "exercicio_atual"
ANTERIOR = "exercicio_anterior"
PRINCIPAL = "QUADRO_PRINCIPAL"
TRANSFERENCIAS = "TRANSFERENCIAS_RECEBIDAS_CONCEDIDAS"
FUNCAO = "DESEMBOLSOS_PESSOAL_POR_FUNCAO"
JUROS = "JUROS_ENCARGOS_DIVIDA"


@pytest.fixture
def apurar_dfc():
    from app.services.dfc.quadro_principal import apurar

    return apurar


def celula(resultado, codigo: str, coluna: str = ATUAL, quadro: str = PRINCIPAL):
    rule_id = next(linha.id for linha in resultado.mapa.linhas
                   if linha.quadro == quadro and linha.codigo == codigo)
    return resultado.matriz[rule_id][coluna]
