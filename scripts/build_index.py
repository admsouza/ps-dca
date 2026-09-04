"""Índice `rule_id -> localização`, gerado a partir dos YAMLs.

Nunca editado à mão: a task 5 do validador confere o índice contra a base e falha se
divergirem. Saída ordenada por `rule_id` para que o arquivo gerado seja estável no diff.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts._carregar import carregar_regras
from scripts._relatorio import configurar_saida

DESTINO = "indexes/rules_index.json"


def construir(base: Path) -> dict[str, dict]:
    """Mapeia cada `rule_id` para arquivo, demonstrativo, quadro, documento e página."""
    indice: dict[str, dict] = {}
    for regra, arquivo, _linha in carregar_regras(base):
        rule_id = regra.get("rule_id")
        if not rule_id:
            continue
        indice[rule_id] = {
            "file": str(arquivo.relative_to(base)).replace("\\", "/"),
            "demonstrativo": (regra.get("demonstrativo") or {}).get("codigo"),
            "quadro": (regra.get("quadro") or {}).get("codigo"),
            "document": (regra.get("source") or {}).get("document"),
            "page": (regra.get("source") or {}).get("page"),
        }
    return dict(sorted(indice.items()))


def gravar(base: Path) -> Path:
    destino = base / DESTINO
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(construir(base), ensure_ascii=False, indent=2) + "\n"
    destino.write_text(texto, encoding="utf-8", newline="\n")
    return destino


def main() -> int:
    configurar_saida()
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("knowledge")
    destino = gravar(base)
    print(f"✓ Índice gerado                   {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
