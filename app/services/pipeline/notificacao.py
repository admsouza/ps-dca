"""Notificação de fim de job no canal de operação (P6).

Duas regras, e as duas vêm do requisito: a notificação **nunca** altera o desfecho do job, e a
falta de canal configurado não é erro — ambiente local apura sem webhook.

Canal fora do ar é logado e ignorado. Deixar a exceção do webhook subir transformaria job
concluído em job perdido.
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class Notificador(Protocol):
    def enviar(self, mensagem: dict) -> None: ...


def notificar_fim(notificador: Notificador | None, *, ente: str, exercicio: int, anexo: str,
                  duracao_ms: int, desfecho: str, erro: str | None = None) -> bool:
    """Devolve se notificou. `False` sem canal, ou quando o canal falhou."""
    if notificador is None:
        return False

    mensagem = {
        "ente": ente,
        "exercicio": exercicio,
        "anexo": anexo,
        "duracao_ms": duracao_ms,
        "desfecho": desfecho,
        "erro": erro,
    }
    try:
        notificador.enviar(mensagem)
        return True
    except Exception:
        logger.warning(
            "falha ao notificar fim de job — resultado permanece gravado | anexo=%s ente=%s "
            "desfecho=%s", anexo, ente, desfecho, exc_info=True,
        )
        return False
