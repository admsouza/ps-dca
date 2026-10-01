"""Consulta da regra de uma célula. Não lê saldo e não entra no cache do demonstrativo.

Só o BF entrega a origem do saldo. Outro anexo responde indisponível, mesmo que o mapa exista.
"""
from __future__ import annotations

from app.domain.bo.regra_celula import coluna_conhecida, projetar
from app.infra.regras.carregador import SemVigencia, carregar_em_cache
from app.services.pipeline.registry import AnexoDesconhecido, anexo


class RegraIndisponivel(LookupError):
    """Anexo, linha ou coluna fora do que a consulta sabe explicar."""


def consultar(anexo_codigo: str, exercicio: int, codigo: str, coluna: str,
              quadro: str | None = None) -> dict:
    try:
        descricao = anexo(anexo_codigo)
    except AnexoDesconhecido as erro:
        raise RegraIndisponivel from erro
    # ponytail: só BF explica a regra; vira registry quando o próximo anexo entrar
    if descricao.servico is None or descricao.base_canonica != "bf":
        raise RegraIndisponivel
    try:
        mapa = carregar_em_cache(exercicio, demonstrativo=descricao.base_canonica)
    except SemVigencia as erro:
        raise RegraIndisponivel from erro
    candidatas = [
        linha for linha in mapa.linhas
        if linha.codigo == codigo and (not quadro or linha.quadro == quadro)
    ]
    if len(candidatas) != 1:
        raise RegraIndisponivel
    linha = candidatas[0]
    if not coluna_conhecida(linha, coluna):
        raise RegraIndisponivel
    from app.services.bf.origem import origem_da_celula

    codigos = {item.id: item.codigo for item in mapa.linhas}
    return projetar(linha, coluna, origem_da_celula(linha.codigo, coluna), codigos)
