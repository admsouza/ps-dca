"""Validação dos valores informados da coluna anterior da DVP — sem tocar na fonte de dados.

Mesmo papel de `bp/informados.py`: a rota recusa o manual inválido antes de enfileirar o job. A DVP
tem um quadro só, então a chave é o código da linha (`L2`), sem prefixo de quadro.
"""
from __future__ import annotations

from decimal import Decimal

from app.domain.bo.modelo import MapaBO
from app.infra.regras.carregador import carregar_em_cache
from app.services.bf.informados import decimal_informado


def partir(valores: dict[str, str]) -> dict[str, Decimal]:
    """`{codigo: valor}`; recusa valor não decimal."""
    return {codigo: decimal_informado(codigo, bruto) for codigo, bruto in valores.items()}


def validar_valores_anteriores(exercicio: int, valores: dict[str, str]) -> None:
    """Código inexistente e linha totalizadora (a que tem `referencias`) são recusados."""
    informados = partir(valores)
    por_codigo = {linha.codigo: linha for linha in mapa_dvp(exercicio).linhas}
    for codigo in informados:
        linha = por_codigo.get(codigo)
        if linha is None:
            raise ValueError(f"linha {codigo} não existe na DVP")
        if linha.referencias:
            raise ValueError(f"linha {codigo} é totalizadora: informe as folhas")


def mapa_dvp(exercicio: int) -> MapaBO:
    return carregar_em_cache(exercicio, demonstrativo="dvp")
