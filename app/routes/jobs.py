"""Acompanhamento de job: `GET /jobs/{job_id}` (polling) e `GET /sse/jobs/{job_id}` (stream).

O estado é `processing`, `done` ou `error`. O resultado aparece na conclusão; o motivo, no erro.
`not_found` é resposta legítima: o TTL do job vence, e o resultado segue no cache do anexo.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.infra.fila import job_manager
from app.routes.dependencias import unidade_autorizada

router = APIRouter(tags=["DCA — jobs"])
logger = logging.getLogger(__name__)

INTERVALO_SSE = 2.0
LIMITE_SSE = 900          # 30 min a 2s — o job tem timeout de 1h, mas a stream não fica pendurada


class EstadoJob(BaseModel):
    job_id: str
    status: str
    resultado: Any = None
    erro: str | None = None
    ente: str | None = None
    exercicio: int | None = None
    anexo: str | None = None


def _estado(request: Request, job_id: str) -> dict:
    return job_manager.estado(request.app.state.portas["jobs"], job_id)


@router.get("/jobs/{job_id}", response_model=EstadoJob, summary="Estado de um job (polling)")
def consultar_job(
    request: Request,
    job_id: Annotated[str, Path()],
    _ente: Annotated[str, Depends(unidade_autorizada)],
) -> dict:
    return _estado(request, job_id)


@router.get("/sse/jobs/{job_id}", summary="Estado de um job (stream de eventos)")
async def acompanhar_job(
    request: Request,
    job_id: Annotated[str, Path()],
    _ente: Annotated[str, Depends(unidade_autorizada)],
) -> StreamingResponse:
    """Mesma informação do polling, empurrada. Encerra no estado final ou quando o cliente sai."""

    async def eventos():
        for _ in range(LIMITE_SSE):
            if await request.is_disconnected():
                return
            estado = _estado(request, job_id)
            yield f"data: {json.dumps(estado, ensure_ascii=False)}\n\n"
            if estado["status"] in ("done", "error", job_manager.DESCONHECIDO):
                return
            await asyncio.sleep(INTERVALO_SSE)

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
