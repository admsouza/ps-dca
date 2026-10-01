"""Projeção da regra de uma célula, a partir da `Linha` que a apuração já usa.

Sem origem de saldo: isso é do anexo. BO e BF entregam um `OrigemCelula` e recebem
o mesmo contrato.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.bo.modelo import Linha

_ANTERIOR = "_anterior"
_ATUAL = "_atual"


@dataclass(frozen=True)
class OrigemCelula:
    nome: str
    meses: tuple[int, ...] = ()


def projetar(linha: Linha, coluna: str, origem: OrigemCelula,
             codigos: dict[str, str]) -> dict:
    """Contrato da consulta. `codigos` traduz o id da regra filha no código da linha."""
    contas = _contas(linha, coluna)
    filhas = tuple(codigos.get(ref.regra, ref.regra) for ref in linha.referencias)
    fontes = next((f.valores for f in linha.filtros if f.campo == "fonte_recurso"), ())
    return {
        "codigo": linha.codigo,
        "coluna": coluna,
        "rotulo": linha.rotulo,
        "tipo": "soma" if filhas and not contas else "contas",
        "origem": origem.nome,
        "meses": list(origem.meses),
        "natureza": linha.apenas_natureza,
        "contas": list(contas),
        "fontes": list(fontes),
        "filhas": list(filhas),
    }


def coluna_conhecida(linha: Linha, coluna: str) -> bool:
    if _coluna(linha, coluna):
        return True
    return bool(linha.referencias) and (
        coluna.endswith(_ATUAL) or coluna.endswith(_ANTERIOR)
    )


def _contas(linha: Linha, coluna: str) -> tuple[str, ...]:
    par = coluna[: -len(_ANTERIOR)] + _ATUAL if coluna.endswith(_ANTERIOR) else coluna
    for cid in (coluna, par):
        declarada = _coluna(linha, cid)
        if declarada and declarada.contas:
            return tuple(conta.cc for conta in declarada.contas)
    return ()


def _coluna(linha: Linha, coluna: str):
    return next((c for c in linha.colunas if c.id == coluna), None)
