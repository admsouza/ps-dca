"""Recortes da DCA: consolidado, grupo de poder e unidade.

Change `pipeline-dca-por-unidade-gestora`.

A unidade é a UG quando a fonte a informa (base por UG da PublicSoft) e o poder/órgão (PO) quando
não informa (SICONFI, MSC importada por CSV). Cada recorte é uma apuração completa sobre os
registros dele — somar resultados de recortes erraria Déficit e Superávit do BO.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from app.domain.bo.modelo import Registro

CONSOLIDADO = "consolidado"

# Poder do hub → `poder_orgao` municipais (PO 2026-10-09: RPPS fica no Executivo).
PODER_ORGAO = {"executivo": ("10131", "10132"), "legislativo": ("20231",)}

# Chave do grupo → poderes que ele soma. A ordem é a de apresentação.
GRUPOS = {
    "poder:executivo": ("executivo",),
    "poder:legislativo": ("legislativo",),
    "poder:executivo+legislativo": ("executivo", "legislativo"),
}

ROTULOS = {
    CONSOLIDADO: "Consolidado do ente",
    "poder:executivo": "Poder Executivo",
    "poder:legislativo": "Poder Legislativo",
    "poder:executivo+legislativo": "Poderes Executivo e Legislativo",
}

# Nomenclatura da STN (`docs/contas-stn/poder-orgao.md`), só os códigos municipais.
NOMES_PO = {
    "10131": "Poder Executivo – Prefeitura Municipal",
    "10132": "Poder Executivo – RPPS Municipal",
    "20231": "Poder Legislativo - Câmara Municipal",
    "20232": "Poder Legislativo - Tribunal de Contas do Município",
    "": "Sem poder/órgão identificado",
}

_CHAVE = re.compile(r"consolidado|poder:(executivo|legislativo|executivo\+legislativo)"
                    r"|ug:\d+|po:(\d{5})?")


def valida(chave: str) -> bool:
    return bool(_CHAVE.fullmatch(chave))


def unidade(registro: Registro) -> str:
    """`ug:<id>` se o registro traz UG; senão `po:<poder_orgao>` (`po:` quando vazio)."""
    if registro.unidade_gestora:
        return f"ug:{registro.unidade_gestora}"
    return f"po:{registro.poder_orgao}"


def _poder(poder_orgao: str) -> str | None:
    return next((p for p, codigos in PODER_ORGAO.items() if poder_orgao in codigos), None)


def recortes(unidades: Mapping[str, str]) -> dict[str, set[str]]:
    """`{unidade: poder_orgao}` → `{chave do recorte: unidades que ele soma}`.

    Unidade com PO fora de `PODER_ORGAO` (ou com mais de um, que chega aqui vazio) não entra em
    grupo: só o consolidado a soma, e só quem tem `consolidado` a vê.
    """
    saida = {chave: {u for u, po in unidades.items() if _poder(po) in poderes}
             for chave, poderes in GRUPOS.items()}
    saida.update({u: {u} for u in sorted(unidades, key=_ordem)})
    return saida


def visiveis(chaves: Iterable[str], unidades: Mapping[str, str],
             poderes: Iterable[str], ugs: Iterable[str] = ()) -> list[str]:
    """As chaves que o usuário pode ler, em ordem de apresentação.

    `ugs` vazio = sem restrição por UG (só o poder decide). Preenchido, só passam as unidades
    autorizadas; `consolidado` e grupos exigem **todas** as unidades que somam autorizadas — do
    contrário o total entregaria o valor da UG negada.
    """
    poderes = set(poderes)
    if CONSOLIDADO in poderes:
        permitidas = set(chaves)
    else:
        permitidas = {chave for chave, exigidos in GRUPOS.items() if set(exigidos) <= poderes}
        permitidas |= {u for u, po in unidades.items() if _poder(po) in poderes}
    autorizadas = {f"ug:{u}" for u in ugs}
    if autorizadas:
        somadas = recortes(unidades) | {CONSOLIDADO: set(unidades)}
        permitidas = {c for c in permitidas if somadas.get(c, {c}) <= autorizadas}
    return sorted((c for c in chaves if c in permitidas), key=_ordem)


def padrao(poderes: Iterable[str]) -> str | None:
    """Recorte servido sem `recorte` no pedido. `None` = nenhum recorte para este usuário."""
    poderes = set(poderes)
    if CONSOLIDADO in poderes:
        return CONSOLIDADO
    return next((chave for chave, exigidos in reversed(GRUPOS.items())
                 if set(exigidos) <= poderes), None)


def tipo(chave: str) -> str:
    return chave.split(":", 1)[0]


def _ordem(chave: str) -> tuple:
    """Consolidado, grupos na ordem de `GRUPOS`, unidades por número (`ug:2` antes de `ug:10`)."""
    if chave == CONSOLIDADO:
        return (0,)
    if chave in GRUPOS:
        return (1, list(GRUPOS).index(chave))
    codigo = chave.split(":", 1)[1]
    return (2, int(codigo) if codigo.isdigit() else -1, codigo)
