"""Conjuntos de códigos válidos, lidos das tabelas oficiais em `docs/contas-stn/`.

As tabelas são markdown com uma linha de cabeçalho e uma de separador; cada linha de dado é
`|c1|c2|…|`. Nenhum código é inventado aqui: se não está na tabela, não entra no conjunto.

Normalização (`normalizar`): só dígitos. É o que permite casar `2111.00.20` com `2111.00.2.0`,
as duas grafias do mesmo código que o IPC 07 usa em páginas diferentes (R6).
"""
from __future__ import annotations

import sys
from pathlib import Path

TABELAS = {
    "conta_contabil": ("PCASP.md", 7),          # coluna CONTA, 9 dígitos
    "natureza_receita": ("natureza-receita.md", 7),  # coluna NR
    "natureza_despesa": ("natureza_despesa.md", 5),  # coluna Código
}
FUNCAO_SUBFUNCAO = "funcao-subfuncao.md"


def normalizar(codigo: str) -> str:
    """Só os dígitos — descarta pontos, hífens e espaços da grafia do documento."""
    return "".join(c for c in codigo if c.isdigit())


def _celulas(linha: str) -> list[str]:
    if not linha.startswith("|"):
        return []
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def _coluna(caminho: Path, indice: int) -> set[str]:
    codigos: set[str] = set()
    with caminho.open(encoding="utf-8") as fh:
        for linha in fh:
            celulas = _celulas(linha)
            if len(celulas) <= indice or set(celulas[0]) <= {"-"}:
                continue
            valor = normalizar(celulas[indice])
            if valor:
                codigos.add(valor)
    return codigos


def carregar(raiz_docs: Path) -> dict[str, set[str]]:
    """Mapeia domínio -> conjunto de códigos normalizados.

    Chaves: `conta_contabil`, `natureza_receita`, `natureza_despesa`, `funcao`, `subfuncao`.
    """
    conjuntos: dict[str, set[str]] = {}
    for dominio, (arquivo, indice) in TABELAS.items():
        caminho = raiz_docs / arquivo
        conjuntos[dominio] = _coluna(caminho, indice) if caminho.is_file() else set()

    funcoes: set[str] = set()
    subfuncoes: set[str] = set()
    caminho = raiz_docs / FUNCAO_SUBFUNCAO
    if caminho.is_file():
        with caminho.open(encoding="utf-8") as fh:
            for linha in fh:
                celulas = _celulas(linha)
                if len(celulas) < 2 or set(celulas[0]) <= {"-"}:
                    continue
                funcao = normalizar(celulas[0].split("-")[0])
                subfuncao = normalizar(celulas[1].split("-")[0])
                if funcao:
                    funcoes.add(funcao)
                if subfuncao:
                    subfuncoes.add(subfuncao)
    conjuntos["funcao"] = funcoes
    conjuntos["subfuncao"] = subfuncoes
    return conjuntos


def main() -> int:
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/contas-stn")
    for dominio, codigos in sorted(carregar(raiz).items()):
        print(f"{dominio:20} {len(codigos):>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
