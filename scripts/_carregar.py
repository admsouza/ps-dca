"""Leitura dos YAMLs da base, preservando o número de linha de cada regra.

O delta spec exige que todo erro cite `arquivo:linha`. `yaml.safe_load` descarta posição, então
a linha é recuperada por varredura do texto: cada item de lista sob `rules:`/`policies:` começa
com `- ` na coluna do bloco, e a ordem dos itens no texto é a mesma da lista carregada.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import yaml

_ITEM = re.compile(r"^(\s*)-\s")


def linhas_dos_itens(texto: str, chave: str) -> list[int]:
    """Números de linha (1-based) de cada item da lista sob `chave`."""
    linhas: list[int] = []
    dentro = False
    indentacao: int | None = None
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if re.match(rf"^{chave}:\s*$", linha):
            dentro = True
            continue
        if not dentro:
            continue
        if linha.strip() and not linha[0].isspace() and not linha.startswith("-"):
            break  # outra chave de topo encerra o bloco
        casou = _ITEM.match(linha)
        if not casou:
            continue
        largura = len(casou.group(1))
        if indentacao is None:
            indentacao = largura
        if largura == indentacao:
            linhas.append(numero)
    return linhas


def _itens(base: Path, subdiretorio: str, chave: str) -> Iterator[tuple[dict, Path, int]]:
    raiz = base / subdiretorio
    if not raiz.is_dir():
        return
    for arquivo in sorted(raiz.rglob("*.yaml")):
        texto = arquivo.read_text(encoding="utf-8")
        dados = yaml.safe_load(texto) or {}
        itens = dados.get(chave) or []
        posicoes = linhas_dos_itens(texto, chave)
        for indice, item in enumerate(itens):
            linha = posicoes[indice] if indice < len(posicoes) else None
            yield item, arquivo, linha


def carregar_regras(base: Path) -> Iterator[tuple[dict, Path, int]]:
    yield from _itens(base, "rules", "rules")


def carregar_policies(base: Path) -> Iterator[tuple[dict, Path, int]]:
    yield from _itens(base, "policies", "policies")
