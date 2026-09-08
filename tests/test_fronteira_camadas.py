"""A fronteira de camadas é verificada, não confiada ao code review.

Task 2.5 da change `plataforma-pipeline-dca`. O núcleo (`app/domain/`) é o que permite apurar os
11 valores do caso de referência sem subir container; qualquer import de I/O ou framework que
alcance o núcleo — direto ou por transitividade — mata essa propriedade em silêncio.

A varredura segue o fecho transitivo dos imports `app.*` a partir de todo módulo do domínio, e não
só a primeira linha de cada arquivo: um `domain/` limpo que importe um módulo de `infra/` que
importe `sqlalchemy` está igualmente contaminado.
"""
from __future__ import annotations

import ast
from pathlib import Path

from tests.conftest import RAIZ_REPO

# Nenhuma destas pode ser alcançável a partir de `app/domain/`: são I/O, framework ou
# dependência da F2/F3 (`pyproject.toml`, extra `plataforma`).
PROIBIDAS = frozenset({
    "requests", "pandas", "yaml", "sqlalchemy", "redis", "fastapi", "arq", "alembic",
    "psycopg2", "uvicorn", "gunicorn", "pydantic", "jose", "cryptography",
})

DOMINIO = RAIZ_REPO / "app" / "domain"


def _modulo_de(caminho: Path) -> str:
    relativo = caminho.relative_to(RAIZ_REPO).with_suffix("")
    partes = relativo.parts[:-1] if relativo.name == "__init__" else relativo.parts
    return ".".join(partes)


def _caminho_de(modulo: str) -> Path | None:
    base = RAIZ_REPO / Path(*modulo.split("."))
    for candidato in (base.with_suffix(".py"), base / "__init__.py"):
        if candidato.is_file():
            return candidato
    return None


def _importados(caminho: Path) -> set[str]:
    """Módulos raiz e módulos `app.*` importados por este arquivo."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            nomes.add(no.module)
    return nomes


def _fecho_de(raiz: Path) -> dict[str, Path]:
    """Todo módulo alcançável a partir de `raiz` por imports `app.*`."""
    pendentes = [p for p in sorted(raiz.rglob("*.py"))]
    alcancados = {_modulo_de(p): p for p in pendentes}
    while pendentes:
        atual = pendentes.pop()
        for nome in _importados(atual):
            if not nome.startswith("app."):
                continue
            for modulo in (nome, nome.rsplit(".", 1)[0]):   # `from app.x import y`: y pode ser nome
                caminho = _caminho_de(modulo)
                if caminho and modulo not in alcancados:
                    alcancados[modulo] = caminho
                    pendentes.append(caminho)
    return alcancados


def test_dominio_nao_alcanca_io_nem_framework():
    """Requisito: o núcleo de apuração é isolado de HTTP, banco e fila.

    Falha nomeando o módulo do fecho e a dependência proibida — o build quebra na hora em que
    alguém cruza a fronteira, e não na revisão.
    """
    fecho = _fecho_de(DOMINIO)
    assert "app.domain.bo.matriz" in fecho, "varredura não encontrou o domínio"

    violacoes = [
        f"{modulo} importa {nome}"
        for modulo, caminho in sorted(fecho.items())
        for nome in sorted(_importados(caminho))
        if nome.split(".")[0] in PROIBIDAS
    ]
    assert not violacoes, "fronteira de camadas cruzada:\n  " + "\n  ".join(violacoes)
