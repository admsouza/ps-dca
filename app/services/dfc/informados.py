"""Linhas da DFC sem conta declarada no IPC 08 — validação do que o contador digita.

Mesmo papel de `bf/informados.py`: a rota recusa o informado inválido **antes** de enfileirar o
job, por isso esta validação não toca na fonte de dados.

O IPC 08 item 17 manda o ente adaptar as linhas "Outros" que a norma não mapeia. Quem sabe o que
caiu nelas é o contador do ente, não a regra canônica (D10 de `ipc08-dfc-regras-canonicas`).
"""
from __future__ import annotations

from decimal import Decimal

from app.domain.bo.modelo import MapaBO
from app.infra.regras.carregador import carregar_em_cache
from app.services.bf.informados import decimal_informado

# As três linhas sem `columns` na base canônica (item 17): "Outros desembolsos operacionais",
# "Outros ingressos de investimentos" e "Outros ingressos de financiamentos".
CODIGOS_SEM_MAPEAMENTO = frozenset({"L16", "L21", "L30"})


class LinhaDesconhecida(ValueError):
    """Valor informado para linha que o IPC 08 mapeia, ou que não existe.

    Recusado antes de apurar.
    """


def partir(valores: dict[str, str]) -> dict[str, Decimal]:
    """`{codigo: valor}`; recusa valor não decimal."""
    return {codigo: decimal_informado(codigo, bruto) for codigo, bruto in valores.items()}


def validar_valores_informados(valores: dict[str, str]) -> None:
    """Recusa código fora das três linhas do item 17 e valor não decimal."""
    desconhecidos = sorted(set(valores) - CODIGOS_SEM_MAPEAMENTO)
    if desconhecidos:
        raise LinhaDesconhecida(
            f"linhas fora das três sem conta no IPC 08: {', '.join(desconhecidos)}")
    partir(valores)


def mapa_dfc(exercicio: int) -> MapaBO:
    return carregar_em_cache(exercicio, demonstrativo="dfc")
