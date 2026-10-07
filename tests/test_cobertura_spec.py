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
    "dca/base-canonica-regras": 83,  # 51 do IPC 07 + 32 do IPC 06 (ipc06-bf-regras-canonicas)
    "dca/balanco-orcamentario": 46,
    # 45 da apuração + 4 do quadro anexo
    # + 3 da persistência do mapa manual (`bf-anterior-manual-persistido`)
    # + 7 do Manual que alimenta (I) (`bf-manual-anexo-alimenta-receita-i`)
    # + 5 do completar G8, mantendo o total sem parcela (`bf-completar-nao-apuradas-g8`)
    # + 1 de L61 nos dois exercícios (soma dos débitos de period_change).
    "dca/balanco-financeiro": 65,
    # 12 da fonte por demonstrativo + 3 da competência de encerramento por API.
    "dca/fonte-msc": 15,
    # 63 da plataforma + 9 da entrada do BF no pipeline (`bf-no-pipeline`)
    # + 4 da vigência por anexo (`vigencia-por-anexo`)
    # + 4 do mapa manual persistido (`bf-anterior-manual-persistido`)
    # + 3 de visualizar sem reprocessar (`pipeline-visualizar-sem-reprocessar`)
    # + 6 das notificações no padrão RREO/RGF (`pipeline-notificacao-discord-padrao`).
    "pipeline/plataforma": 89,
    # 11 do percurso completo (`pipeline-completo-dca`) + 2 da notificação por anexo
    # (`pipeline-notificacao-discord-padrao`) + 4 da origem do BP (`pipeline-percurso-origem-bp`).
    "pipeline/processamento-completo": 17,
    # 16 da apuração do BP (`bp-apuracao-f1`) + 7 da origem publicada
    # (`bp-anterior-publicado-siconfi`)
    # + 4 do espelho do I-AB, − 1 da exclusão intra revogada (`bp-espelho-iab`).
    "dca/balanco-patrimonial": 26,
}

# Capabilities cuja fase TEST já começou — só delas se exige teste por cenário.
# `pipeline/plataforma` entrou ao fechar os 63 cenários — fase TEST concluída, F2/F3 por
# implementar. Os testes existem e são vermelhos de propósito; a cobertura passa a ser exigida
# daqui para a frente, e cenário novo sem teste quebra o build.
COM_TESTES = ("dca/base-canonica-regras", "dca/balanco-orcamentario",
              "dca/balanco-financeiro", "dca/fonte-msc", "pipeline/plataforma",
              "pipeline/processamento-completo", "dca/balanco-patrimonial")


def _specs() -> dict[str, list[Path]]:
    """Capability -> specs em vigor.

    A mesclada em `openspec/specs/` vence sozinha. Enquanto não houver mesclagem, valem **todos**
    os deltas das changes ativas: duas changes podem tocar a mesma capability ao mesmo tempo — é o
    caso de `pipeline/plataforma`, com a plataforma e a entrada do BF —, e escolher um delta só
    faria a contagem de cenários cair sem que nenhum tivesse sido removido.
    """
    mescladas: dict[str, list[Path]] = {}
    ativas: dict[str, list[Path]] = {}
    arquivadas: dict[str, list[Path]] = {}
    for raiz, destino in ((OPENSPEC / "specs", mescladas),
                          (OPENSPEC / "changes", ativas),
                          (OPENSPEC / "changes" / "archive", arquivadas)):
        for caminho in sorted(raiz.rglob("spec.md")):
            partes = caminho.parts
            if "specs" not in partes:
                continue
            if destino is ativas and "archive" in partes:
                continue
            indice = len(partes) - 1 - partes[::-1].index("specs")
            capability = "/".join(partes[indice + 1:-1])
            if capability:
                destino.setdefault(capability, []).append(caminho)

    encontrados = dict(mescladas)
    for capability in set(ativas) | set(arquivadas):
        if capability in encontrados:
            continue        # já mesclada: a spec em vigor é a única fonte
        # Sem mesclagem, a spec em vigor é a **soma** do que foi aprovado: uma capability pode ter
        # delta numa change ativa e noutra já arquivada — é o caso de `pipeline/plataforma`, com a
        # plataforma em curso e a entrada do BF já encerrada.
        encontrados[capability] = ativas.get(capability, []) + arquivadas.get(capability, [])
    return encontrados


def _cenarios(caminhos: list[Path]) -> list[str]:
    return [cenario for caminho in caminhos
            for cenario in re.findall(r"^#### Scenario: (.+)$",
                                      caminho.read_text(encoding="utf-8"), re.M)]


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
