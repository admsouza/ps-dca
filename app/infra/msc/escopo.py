"""Cache de escopo da execução: vive enquanto o job executa, e morre com ele.

Por que existir, com o Redis já no caminho: o BF lê **três origens** (abertura do exercício,
encerramento e abertura do exercício anterior) × seis classes = 18 leituras por apuração, e o gate
de auditoria da PublicSoft é consultado uma vez por leitura. Sem memória de execução, isso são 18
idas ao Redis (com reidratação) e 18 chamadas HTTP de auditoria para responder sempre a mesma
coisa.

É também onde o dado do **exercício corrente** vive: a matriz ainda é retificável na fonte, e o
requisito é que esse dado não sobreviva ao job que o baixou. Fora de um `escopo()` aberto nada é
memorizado — CLI e teste seguem consultando a fonte a cada chamada.

Sem lock: a apuração de um job é síncrona e roda em uma thread só; jobs concorrentes abrem
escopos distintos, porque o `ContextVar` é copiado por contexto (inclusive em `asyncio.to_thread`).
"""
from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_atual: ContextVar[dict | None] = ContextVar("msc_escopo", default=None)


@contextmanager
def escopo():
    """Abre a memória de execução, descartada ao sair. Aninhar **reusa** a já aberta."""
    if _atual.get() is not None:
        yield
        return
    token = _atual.set({})
    try:
        yield
    finally:
        _atual.reset(token)


def obter_ou_buscar(chave: str, buscar: Callable[[], Any]) -> Any:
    """Valor memorizado no escopo atual, ou o que `buscar` devolver. Sem escopo, só busca."""
    memoria = _atual.get()
    if memoria is None:
        return buscar()
    if chave in memoria:
        return memoria[chave]
    valor = memoria[chave] = buscar()
    return valor


def ativo() -> bool:
    return _atual.get() is not None
