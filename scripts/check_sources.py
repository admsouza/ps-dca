"""Integridade das fontes: o PDF do IPC e as tabelas da STN.

O PDF e as tabelas são a origem normativa da base canônica. Se um deles muda sem que o
metadata mude junto, toda regra transcrita passa a citar um documento que não existe mais —
por isso a divergência de hash é erro, não aviso.

Os arquivos são apenas lidos. Nada aqui escreve em `docs/`.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import yaml

from scripts._relatorio import Relatorio, configurar_saida


def sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _conferir(rel: Relatorio, rotulo: str, caminho: Path, esperado: str, origem: Path) -> None:
    if not esperado:
        rel.erro(f"{rotulo}: metadata sem sha256", arquivo=str(origem))
        return
    if not caminho.is_file():
        rel.erro(f"{rotulo}: arquivo não encontrado em {caminho}", arquivo=str(origem))
        return
    obtido = sha256(caminho)
    if obtido != esperado:
        rel.erro(
            f"{rotulo}: hash divergente — esperado {esperado}, obtido {obtido}",
            arquivo=str(caminho),
        )


def verificar(base: Path) -> Relatorio:
    """Confere o SHA-256 do PDF de cada IPC e das tabelas da STN declaradas no metadata."""
    rel = Relatorio()
    documentos = 0

    for meta in sorted((base / "sources").glob("*/metadata.yaml")):
        dados = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}

        if "tables" in dados:
            for tabela in dados["tables"] or []:
                _conferir(
                    rel, Path(tabela["file"]).name, Path(tabela["file"]),
                    tabela.get("sha256", ""), meta,
                )
            continue

        documento = dados.get("document", meta.parent.name.upper())
        caminho = Path(dados["path"]) if dados.get("path") else _pdf_padrao(base, dados)
        _conferir(rel, documento, caminho, dados.get("sha256", ""), meta)
        documentos += 1

    # O PDF é fonte externa imutável: fica em docs/referencia/, nunca copiado para dentro da base.
    duplicados = list(base.rglob("*.pdf"))
    for pdf in duplicados:
        rel.erro(f"PDF duplicado dentro da base canônica: {pdf}", arquivo=str(pdf))

    rel.contagens = {"documentos": documentos, "erros": len(rel.erros)}
    return rel


def _pdf_padrao(base: Path, dados: dict) -> Path:
    """Resolve o PDF relativo à raiz do repositório quando o metadata não traz `path`."""
    raiz_repo = base.parent
    return raiz_repo / "docs" / "referencia" / "ipc" / dados.get("file", "")


def main() -> int:
    configurar_saida()
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("knowledge")
    rel = verificar(base)
    for erro in rel.erros:
        print(erro)
    if not rel.erros:
        print(f"✓ Fontes íntegras                 {rel.contagens['documentos']} documento(s)")
    return rel.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
