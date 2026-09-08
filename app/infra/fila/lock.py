"""Lock por identidade, com recuperação de órfão — uma implementação, para os oito anexos.

O RGF tem seis arquivos para isto (`services/anexo_0{2..5}/orfaos.py`, `utils/rgf_orfaos.py`,
`services/rgf/lock_anexo.py`) e registra a dívida no próprio código. Aqui é um módulo, e o anexo é
parâmetro.

Órfão é lock cujo job não está mais `processing`: worker reiniciado, job perdido na fila, TTL do
estado vencido. Sem liberá-lo, a identidade fica bloqueada até alguém apagar a chave à mão.
"""
from __future__ import annotations

import logging
from typing import Protocol

from app.infra.fila import job_manager
from app.infra.fila.job_manager import Jobs

logger = logging.getLogger(__name__)


class Trava(Protocol):
    """Porta do lock. `adquirir` é atômico — `SET NX` no Redis."""

    def adquirir(self, ente: str, exercicio: int, anexo: str, job_id: str) -> bool: ...
    def liberar(self, ente: str, exercicio: int, anexo: str) -> None: ...
    def dono(self, ente: str, exercicio: int, anexo: str) -> str | None: ...


def adquirir_com_recuperacao(trava: Trava, jobs: Jobs | None, *, ente: str, exercicio: int,
                             anexo: str, job_id: str) -> str | None:
    """Toma o lock. Devolve `None` se tomou, ou o `job_id` do job **vivo** que já o detém.

    Lock cujo job não está mais em execução é liberado, o evento é logado, e a tomada é repetida —
    é a única forma de a identidade não ficar presa a um worker que morreu.
    """
    if trava.adquirir(ente, exercicio, anexo, job_id):
        return None

    dono = trava.dono(ente, exercicio, anexo)
    if dono and (jobs is None or job_manager.em_execucao(jobs, dono)):
        return dono

    logger.warning(
        "lock órfão liberado | ente=%s exercicio=%s anexo=%s job_morto=%s",
        ente, exercicio, anexo, dono,
    )
    trava.liberar(ente, exercicio, anexo)
    if trava.adquirir(ente, exercicio, anexo, job_id):
        return None

    # Outro processo venceu a corrida pelo lock recém-liberado: o job dele é o legítimo.
    return trava.dono(ente, exercicio, anexo)


def liberar(trava: Trava, *, ente: str, exercicio: int, anexo: str) -> None:
    trava.liberar(ente, exercicio, anexo)
