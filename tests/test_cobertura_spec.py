"""Rastreabilidade viva: todo cenário do spec tem teste, e todo teste aponta um cenário.

Substitui a tabela de-para que a fase VERIFY pediria — uma tabela em markdown envelhece em
silêncio; este teste quebra no momento em que alguém acrescenta cenário sem teste.

A convenção que ele impõe: o docstring do teste começa com `Scenario: <nome exato>`, ou com
`Requisito:` quando cobre uma exigência do texto do requisito que não virou cenário próprio.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.conftest import RAIZ_REPO

CAPABILITY = "dca/base-canonica-regras"


def _spec() -> Path:
    """Localiza o delta spec, esteja a change ativa, arquivada ou já mesclada."""
    candidatos = [
        RAIZ_REPO / "openspec" / "specs" / CAPABILITY / "spec.md",
        *sorted((RAIZ_REPO / "openspec" / "changes").glob(f"*/specs/{CAPABILITY}/spec.md")),
        *sorted((RAIZ_REPO / "openspec" / "changes" / "archive").glob(
            f"*/specs/{CAPABILITY}/spec.md")),
    ]
    for caminho in candidatos:
        if caminho.is_file():
            return caminho
    pytest.fail(f"spec de {CAPABILITY} não encontrado")


def _cenarios_do_spec() -> list[str]:
    texto = _spec().read_text(encoding="utf-8")
    return re.findall(r"^#### Scenario: (.+)$", texto, re.M)


def _docstrings_dos_testes() -> dict[str, str]:
    docs: dict[str, str] = {}
    for arquivo in sorted(Path(__file__).parent.glob("test_*.py")):
        if arquivo.name == Path(__file__).name:
            continue
        texto = arquivo.read_text(encoding="utf-8")
        for nome, corpo in re.findall(
            r'^def (test_\w+)\([^)]*\):\n    """(.*?)"""', texto, re.S | re.M
        ):
            docs[f"{arquivo.name}::{nome}"] = corpo
    return docs


def test_todo_cenario_do_spec_tem_teste():
    """Requisito: cada `#### Scenario:` do delta spec é exercitado por ao menos um teste."""
    docs = _docstrings_dos_testes()
    descobertos = "\n".join(docs.values()).lower()
    sem_cobertura = [c for c in _cenarios_do_spec() if c.lower() not in descobertos]
    assert sem_cobertura == [], (
        "cenários sem teste que os cite no docstring:\n  - " + "\n  - ".join(sem_cobertura)
    )


def test_todo_teste_declara_o_que_cobre():
    """Requisito: nenhum teste sem docstring dizendo qual cenário ou requisito ele cobre."""
    docs = _docstrings_dos_testes()
    mudos = [nome for nome, corpo in docs.items()
             if not corpo.strip().startswith(("Scenario:", "Requisito:"))]
    assert mudos == [], "testes sem Scenario:/Requisito: no docstring:\n  - " + "\n  - ".join(mudos)


def test_spec_nao_perdeu_cenarios():
    """Requisito: a contagem de cenários do IPC 07 é 49 — muda só com decisão registrada."""
    assert len(_cenarios_do_spec()) == 49
