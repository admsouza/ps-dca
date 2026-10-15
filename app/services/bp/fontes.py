"""Catálogo canônico de fontes de recursos usado pelo BP e pelo preenchimento manual."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[3]
_ARQUIVO = _RAIZ / "docs/contas-stn/fonte-recursos.md"
_SUFIXO_ANTERIOR = " - Exercícios Anteriores"


@dataclass(frozen=True)
class FonteRecurso:
    codigo: str
    nome: str


@cache
def _fontes_principais() -> dict[str, str]:
    fontes: dict[str, str] = {}
    for linha in _ARQUIVO.read_text(encoding="utf-8").splitlines():
        if not linha.startswith("|"):
            continue
        celulas = [celula.strip() for celula in linha.strip("|").split("|")]
        codigo = celulas[0]
        if len(codigo) != 3 or not codigo.isdigit():
            continue
        nome = celulas[1] if len(celulas) > 1 else ""
        if not nome:
            raise ValueError(f"fonte {codigo} sem nomenclatura em {_ARQUIVO}")
        if codigo in fontes:
            raise ValueError(f"fonte {codigo} duplicada em {_ARQUIVO}")
        fontes[codigo] = nome
    if not fontes:
        raise ValueError(f"catálogo de fontes vazio em {_ARQUIVO}")
    return fontes


@cache
def fontes_oficiais() -> tuple[FonteRecurso, ...]:
    fontes = [
        FonteRecurso(f"{prefixo}{codigo}", nome + (_SUFIXO_ANTERIOR if prefixo == "2" else ""))
        for codigo, nome in _fontes_principais().items()
        for prefixo in ("1", "2")
    ]
    return tuple(sorted(fontes, key=lambda fonte: fonte.codigo))


def fonte_oficial(codigo: str) -> bool:
    return len(codigo) == 4 and codigo[0] in ("1", "2") and codigo[1:] in _fontes_principais()


def rotulo_fonte(codigo: str) -> str:
    nome = _fontes_principais().get(codigo[1:4], codigo[1:4])
    return nome + (_SUFIXO_ANTERIOR if codigo.startswith("2") else "")