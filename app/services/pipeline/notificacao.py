"""Notificação no canal de operação (P6): fim de anexo, fim de percurso e requisição recebida.

Duas regras, e as duas vêm do requisito: a notificação **nunca** altera o desfecho do job, e a
falta de canal configurado não é erro — ambiente local apura sem webhook.

Canal fora do ar é logado e ignorado. Deixar a exceção do webhook subir transformaria job
concluído em job perdido.

Aqui só se monta o dado (`tipo` + fatos); o texto, a cor e o rótulo do ente são da infra
(`infra/notificacao/discord.py`), no padrão do RREO e do RGF.
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class Notificador(Protocol):
    def enviar(self, mensagem: dict) -> None: ...


def notificar_fim(notificador: Notificador | None, *, ente: str, exercicio: int, anexo: str,
                  duracao_ms: int, desfecho: str, erro: str | None = None) -> bool:
    """Fim de um anexo. `desfecho`: `sucesso` | `erro` | `cache`. Devolve se notificou."""
    return _enviar(notificador, {
        "tipo": "anexo", "ente": ente, "exercicio": exercicio, "anexo": anexo,
        "duracao_ms": duracao_ms, "desfecho": desfecho, "erro": erro,
    })


def notificar_percurso(notificador: Notificador | None, *, ente: str, exercicio: int,
                       duracao_ms: int, falhas: int, anexos: list[dict],
                       solicitante: str | None = None, fonte: str | None = None) -> bool:
    """Resumo do percurso, depois das mensagens por anexo — o resumo do pipeline do RGF."""
    return _enviar(notificador, {
        "tipo": "percurso", "ente": ente, "exercicio": exercicio, "duracao_ms": duracao_ms,
        "desfecho": "sucesso" if not falhas else "com_erros", "falhas": falhas,
        "solicitante": solicitante, "fonte": fonte,
        "anexos": [{"anexo": a["anexo"], "status": a["status"],
                    "duracao_ms": a.get("duracao_ms"),
                    "erro_detalhe": a.get("erro_detalhe")} for a in anexos],
    })


def notificar_recebida(notificador: Notificador | None, *, ente: str, exercicio: int,
                       anexos: list[str], percurso: bool, forcar: bool,
                       solicitante: str | None, fonte: str | None) -> bool:
    """Pedido aceito com job enfileirado. Leitura servida do cache não chama isto."""
    return _enviar(notificador, {
        "tipo": "recebida", "ente": ente, "exercicio": exercicio, "anexos": list(anexos),
        "percurso": percurso, "forcar": forcar, "solicitante": solicitante, "fonte": fonte,
    })


def _enviar(notificador: Notificador | None, mensagem: dict) -> bool:
    """`False` sem canal, ou quando o canal falhou."""
    if notificador is None:
        return False
    try:
        notificador.enviar(mensagem)
        return True
    except Exception:
        logger.warning(
            "falha ao notificar (%s) — resultado permanece gravado | ente=%s exercicio=%s "
            "anexo=%s", mensagem["tipo"], mensagem.get("ente"), mensagem.get("exercicio"),
            mensagem.get("anexo"), exc_info=True,
        )
        return False
