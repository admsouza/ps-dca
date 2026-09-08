"""Estado do job — o que o polling e a stream leem.

Um mecanismo só, sobre a porta `jobs`: em memória no teste, Redis em produção. O RGF distribui o
mesmo estado em quatro chaves (`job`, `meta`, `data`, `sub`) e reconstrói o status pela ausência de
uma delas; aqui é um documento por job, e `status` é campo, não inferência.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Protocol

logger = logging.getLogger(__name__)

STATUS_JOB = ("processing", "done", "error")

# O que o cliente recebe quando o `job_id` não existe mais — TTL vencido, ou id inventado.
DESCONHECIDO = "not_found"


class JobDesconhecido(LookupError):
    """`job_id` sem estado registrado."""


class Jobs(Protocol):
    """Porta do armazenamento de estado de job."""

    def gravar(self, job_id: str, estado: dict) -> None: ...
    def obter(self, job_id: str) -> dict | None: ...


def novo_id() -> str:
    return str(uuid.uuid4())


def criar(jobs: Jobs, job_id: str, *, ente: str, exercicio: int, anexo: str) -> dict:
    """Registra o job como `processing`, **sem** resultado."""
    estado = {
        "job_id": job_id,
        "status": "processing",
        "ente": ente,
        "exercicio": exercicio,
        "anexo": anexo,
        "resultado": None,
        "erro": None,
    }
    jobs.gravar(job_id, estado)
    return dict(estado)


def estado(jobs: Jobs, job_id: str) -> dict:
    """Estado atual. `not_found` em vez de exceção: TTL vencido é resposta, não falha."""
    atual = jobs.obter(job_id)
    if atual is None:
        return {"job_id": job_id, "status": DESCONHECIDO, "resultado": None, "erro": None}
    return atual


def exigir(jobs: Jobs, job_id: str) -> dict:
    """Como `estado`, mas levanta — para quem não pode seguir sem o job."""
    atual = jobs.obter(job_id)
    if atual is None:
        raise JobDesconhecido(job_id)
    return atual


def concluir(jobs: Jobs, job_id: str, resultado: Any) -> None:
    atual = jobs.obter(job_id) or {"job_id": job_id}
    jobs.gravar(job_id, {**atual, "status": "done", "resultado": resultado, "erro": None})


def falhar(jobs: Jobs, job_id: str, motivo: str) -> None:
    atual = jobs.obter(job_id) or {"job_id": job_id}
    jobs.gravar(job_id, {**atual, "status": "error", "resultado": None, "erro": motivo})


def em_execucao(jobs: Jobs, job_id: str) -> bool:
    """Se o job apontado por um lock ainda está de pé. É o que distingue lock vivo de órfão."""
    return estado(jobs, job_id)["status"] == "processing"
