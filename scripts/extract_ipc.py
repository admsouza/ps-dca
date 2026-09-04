"""Extração geométrica do IPC 07 — ferramenta de desenvolvimento, fora do CI.

As páginas de regra são **paisagem rotacionada 90°**: no espaço do PDF, a linha da tabela é uma
banda em `x` e a coluna é uma banda em `y` (`docs/source-analysis-ipc07.md` §1.1). Extração
linear de texto embaralha a associação célula→coluna; por isso aqui as palavras são agrupadas por
coordenada, não por ordem de leitura.

Saída: `knowledge/sources/<ipc>/extracted.md`, que é insumo da transcrição — nunca a base
canônica em si. Nada aqui grava YAML de regra.

    python -m scripts.extract_ipc                 # todas as páginas
    python -m scripts.extract_ipc 8 9             # só as páginas indicadas
"""
from __future__ import annotations

import sys
from pathlib import Path

from scripts._relatorio import configurar_saida

RAIZ_REPO = Path(__file__).resolve().parent.parent
PDF = RAIZ_REPO / "docs" / "referencia" / "ipc" / "IPC07 - BO atualizacoes - 20200117.pdf"
DESTINO = RAIZ_REPO / "knowledge" / "sources" / "ipc07" / "extracted.md"

TOLERANCIA_LINHA = 6.0   # pontos: palavras dentro desta faixa de `x` são da mesma linha da tabela

# Só as páginas de matriz são rotacionadas. Nas de texto corrido, agrupar por `x` embaralha as
# frases — ali vale a ordem de leitura normal.
PAGINAS_DE_TABELA = frozenset(range(8, 14))


def palavras(pagina) -> list[tuple[float, float, str]]:
    """(x, y, texto) de cada palavra, no espaço do PDF."""
    return [(p[0], p[1], p[4]) for p in pagina.get_text("words")]


def agrupar_por_banda(itens, indice: int, tolerancia: float) -> list[list]:
    """Agrupa itens cuja coordenada `indice` esteja dentro de `tolerancia` do grupo."""
    grupos: list[list] = []
    for item in sorted(itens, key=lambda i: i[indice]):
        if grupos and abs(item[indice] - grupos[-1][0][indice]) <= tolerancia:
            grupos[-1].append(item)
        else:
            grupos.append([item])
    return grupos


def extrair(caminho: Path, paginas: list[int] | None = None) -> str:
    import pymupdf  # `fitz` é o nome antigo e está deprecado

    documento = pymupdf.open(caminho)
    partes: list[str] = [
        f"# Extração geométrica — {caminho.name}",
        "",
        "> Gerado por `scripts/extract_ipc.py`. Insumo de transcrição, **não** é a base canônica.",
        "> Página rotacionada: a linha da tabela é banda em `x`; a coluna, banda em `y`.",
        "",
    ]

    for numero in range(1, documento.page_count + 1):
        if paginas and numero not in paginas:
            continue
        pagina = documento[numero - 1]
        partes.append(f"## Página {numero}")
        partes.append("")

        if numero not in PAGINAS_DE_TABELA:
            texto = pagina.get_text("text").strip()
            partes += [texto or "_(sem texto extraível)_", ""]
            continue

        itens = palavras(pagina)
        if not itens:
            partes += ["_(sem texto extraível)_", ""]
            continue

        # Rotacionada: agrupa por x (linha da tabela) e ordena cada linha por y decrescente,
        # que é a ordem visual das colunas da esquerda para a direita.
        for banda in agrupar_por_banda(itens, 0, TOLERANCIA_LINHA):
            texto = " ".join(t for _x, _y, t in sorted(banda, key=lambda i: -i[1]))
            x = banda[0][0]
            if texto.strip():
                partes.append(f"- `x={x:7.1f}` {texto}")
        partes.append("")

    documento.close()
    return "\n".join(partes) + "\n"


def main() -> int:
    configurar_saida()
    paginas = [int(a) for a in sys.argv[1:]] or None
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(extrair(PDF, paginas), encoding="utf-8", newline="\n")
    print(f"✓ Extraído                        {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
