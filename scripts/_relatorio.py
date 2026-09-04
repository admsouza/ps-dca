"""Tipos comuns aos scripts da base canônica.

`Relatorio` é o retorno de `validate_rules.validar` e de `check_sources.verificar`; o
`exit_code` é derivado dos erros, não passado à mão — relatório com erro e exit 0 seria a
falha silenciosa que o delta spec proíbe.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any


def configurar_saida() -> None:
    """Força UTF-8 no stdout/stderr.

    O console do Windows abre em cp1252 e derruba o script no primeiro acento ou `✓` —
    falha de terminal virando falha de validação.
    """
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Erro:
    mensagem: str
    rule_id: str | None = None
    arquivo: str | None = None
    linha: int | None = None

    def __str__(self) -> str:
        local = f"{self.arquivo}:{self.linha}" if self.arquivo else ""
        return f"ERROR {self.rule_id or ''}\n  {self.mensagem}\n  Source: {local}".rstrip()


@dataclass
class Relatorio:
    erros: list[Erro] = field(default_factory=list)
    contagens: dict[str, Any] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return 1 if self.erros else 0

    def erro(self, mensagem: str, *, rule_id: str | None = None,
             arquivo: str | None = None, linha: int | None = None) -> None:
        self.erros.append(Erro(mensagem, rule_id, arquivo, linha))
