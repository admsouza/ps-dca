"""Rastreabilidade viva: todo cenário de spec tem teste, e todo teste aponta um cenário.

Substitui a tabela de-para que a fase VERIFY pediria — uma tabela em markdown envelhece em
silêncio; este teste quebra no momento em que alguém acrescenta cenário sem teste.

A convenção que ele impõe: o docstring do teste começa com `Scenario: <nome exato>`, ou com
`Requisito:` quando cobre uma exigência do texto do requisito que não virou cenário próprio.

Vale para toda capability, ativa ou arquivada. Capability nova entra sozinha na varredura.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.conftest import RAIZ_REPO

OPENSPEC = RAIZ_REPO / "openspec"

# Contagem de cenários por capability, conferida quando a spec foi aprovada. Mudança aqui é
# mudança de escopo: só com decisão registrada na change correspondente.
CENARIOS_ESPERADOS = {
    "dca/base-canonica-regras": 51,
    "dca/balanco-orcamentario": 43,
    "pipeline/plataforma": 63,
}

# Capabilities cuja fase TEST já começou — só delas se exige teste por cenário.
# `pipeline/plataforma` entrou ao fechar os 63 cenários — fase TEST concluída, F2/F3 por
# implementar. Os testes existem e são vermelhos de propósito; a cobertura passa a ser exigida
# daqui para a frente, e cenário novo sem teste quebra o build.
COM_TESTES = ("dca/base-canonica-regras", "dca/balanco-orcamentario", "pipeline/plataforma")


def _specs() -> dict[str, Path]:
    """Capability -> spec em vigor, preferindo a mesclada à da change ativa ou arquivada."""
    encontrados: dict[str, Path] = {}
    for raiz, prioridade in ((OPENSPEC / "specs", 0),
                             (OPENSPEC / "changes", 1),
                             (OPENSPEC / "changes" / "archive", 2)):
        for caminho in sorted(raiz.rglob("spec.md")):
            partes = caminho.parts
            if "specs" not in partes:
                continue
            indice = len(partes) - 1 - partes[::-1].index("specs")
            capability = "/".join(partes[indice + 1:-1])
            if capability and (capability not in encontrados or prioridade == 0):
                encontrados.setdefault(capability, caminho)
    return encontrados


def _cenarios(caminho: Path) -> list[str]:
    return re.findall(r"^#### Scenario: (.+)$", caminho.read_text(encoding="utf-8"), re.M)


def _docstrings() -> dict[str, str]:
    docs: dict[str, str] = {}
    for arquivo in sorted(Path(__file__).parent.rglob("test_*.py")):
        if arquivo.name == Path(__file__).name:
            continue
        texto = arquivo.read_text(encoding="utf-8")
        for nome, corpo in re.findall(
            r'^def (test_\w+)\([^)]*\):\n    """(.*?)"""', texto, re.S | re.M
        ):
            docs[f"{arquivo.name}::{nome}"] = corpo
    return docs


@pytest.mark.parametrize("capability", COM_TESTES)
def test_todo_cenario_do_spec_tem_teste(capability):
    """Requisito: cada `#### Scenario:` do spec é exercitado por ao menos um teste."""
    specs = _specs()
    assert capability in specs, f"spec de {capability} não encontrado"
    descobertos = "\n".join(_docstrings().values()).lower()
    sem_cobertura = [c for c in _cenarios(specs[capability]) if c.lower() not in descobertos]
    assert sem_cobertura == [], (
        f"{capability} — cenários sem teste que os cite no docstring:\n  - "
        + "\n  - ".join(sem_cobertura)
    )


@pytest.mark.parametrize("capability", sorted(CENARIOS_ESPERADOS))
def test_spec_nao_perdeu_cenarios(capability):
    """Requisito: a contagem de cenários só muda com decisão registrada na change."""
    specs = _specs()
    assert capability in specs, f"spec de {capability} não encontrado"
    assert len(_cenarios(specs[capability])) == CENARIOS_ESPERADOS[capability]


def test_todo_teste_declara_o_que_cobre():
    """Requisito: nenhum teste sem docstring dizendo qual cenário ou requisito ele cobre."""
    mudos = [nome for nome, corpo in _docstrings().items()
             if not corpo.strip().startswith(("Scenario:", "Requisito:"))]
    assert mudos == [], "testes sem Scenario:/Requisito: no docstring:\n  - " + "\n  - ".join(
        mudos)
