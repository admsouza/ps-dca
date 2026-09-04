"""Portas do domínio — o que o núcleo precisa do mundo, declarado por ele.

As implementações vivem em `app/infra/`. O domínio não sabe se a direção do saldo veio de um
markdown ou de um banco, nem se os registros vieram do SICONFI, da PublicSoft ou de uma lista
literal de teste. Inverter essa dependência é o que torna a apuração verificável sem
infraestrutura.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.domain.bo.modelo import Registro


class DirecaoSaldo(Protocol):
    """Diz se uma conta acumula por crédito. `None` = desconhecida, e a célula não é apurada."""

    def credora(self, conta: str) -> bool | None: ...


class FonteSaldos(Protocol):
    """Devolve os registros da MSC de um ente, exercício, mês e classe contábil."""

    def registros(self, ente: int, ano: int, mes: int, classe: int) -> Sequence[Registro]: ...
