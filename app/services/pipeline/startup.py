"""Preparação do worker antes de consumir a fila.

Duas coisas, nesta ordem: verificar as dependências e liberar os locks órfãos que o processo
anterior deixou. Worker de pé consumindo fila que não sabe gravar é o pior desfecho — o job sai da
fila, falha, e ninguém vê.

Fica em service, e não em `worker.py`, por dois motivos: o worker segue um wrapper fino que
delega, e o startup fica testável sem `arq` no processo do teste.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

logger = logging.getLogger(__name__)


class DependenciaIndisponivel(RuntimeError):
    """Redis ou Postgres fora do ar no boot. Explícito, e não silencioso."""


class Trava(Protocol):
    def limpar_orfaos(self) -> int: ...


def preparar(lock: Trava) -> int:
    """Libera locks órfãos remanescentes. Devolve quantos."""
    liberados = lock.limpar_orfaos()
    if liberados:
        logger.warning("startup: %d lock(s) órfão(s) liberado(s) antes de consumir a fila",
                       liberados)
    else:
        logger.info("startup: nenhum lock órfão remanescente")
    return liberados


def soltar_jobs_interrompidos(redis, fila: str) -> int:
    """Devolve à fila os jobs que o processo anterior pegou e não terminou.

    `arq:in-progress:<id>` marca job em execução e faz o worker seguinte recusar o id.
    No boot o dono anterior já morreu: apagar a chave dos ids ainda na fila devolve o
    job ao poll. DEL de chave ausente conta zero — job sem dono fica intocado.
    """
    from arq.constants import in_progress_key_prefix

    ids = redis.zrange(fila, 0, -1)
    if not ids:
        return 0
    soltos = int(redis.delete(*(
        in_progress_key_prefix + (i.decode() if isinstance(i, bytes) else i) for i in ids
    )))
    if soltos:
        logger.warning("startup: %d job(s) interrompido(s) devolvido(s) à fila", soltos)
    return soltos


def verificar_dependencias(*, redis: Callable[[], object], banco: Callable[[], object]) -> dict:
    """Testa cada dependência e registra o resultado. Falha nomeia qual caiu e por quê."""
    estado: dict[str, str] = {}
    falhas: list[str] = []

    for nome, ping in (("redis", redis), ("banco", banco)):
        try:
            ping()
        except Exception as erro:
            estado[nome] = "falha"
            falhas.append(f"{nome}: {type(erro).__name__}: {erro}")
            logger.error("dependência indisponível no startup | %s -> %s", nome, erro)
        else:
            estado[nome] = "ok"
            logger.info("dependência verificada no startup | %s -> ok", nome)

    if falhas:
        raise DependenciaIndisponivel("; ".join(falhas))
    return estado
