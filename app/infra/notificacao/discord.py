"""Notificação de fim de job no Discord. Síncrona, e sempre tolerante a falha.

Reuso do padrão de `regras-rgf-api/app/utils/discord_notifier.py`. A regra que não muda: a
notificação **nunca** altera o desfecho do job — quem trata a exceção é
`services/pipeline/notificacao.py`, e aqui ela só é levantada.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CORES = {"sucesso": 0x2ECC71, "erro": 0xE74C3C}
TIMEOUT = 5


def formatar_duracao(ms: int) -> str:
    if ms < 1000:
        return f"{ms} ms"
    segundos = ms / 1000
    if segundos < 60:
        return f"{segundos:.1f} s"
    return f"{int(segundos // 60)} min {int(segundos % 60)} s"


class DiscordNotificador:
    def __init__(self, webhook: str, http=None) -> None:
        self._webhook = webhook
        self._http = http

    def enviar(self, mensagem: dict) -> None:
        desfecho = mensagem.get("desfecho", "sucesso")
        linhas = [
            f"**Ente:** {mensagem.get('ente')}  |  **Exercício:** {mensagem.get('exercicio')}",
            f"**Anexo:** {mensagem.get('anexo')}  |  "
            f"**Duração:** {formatar_duracao(int(mensagem.get('duracao_ms') or 0))}",
        ]
        if mensagem.get("erro"):
            linhas.append(f"**Motivo:** {mensagem['erro']}")

        corpo = {
            "embeds": [{
                "title": f"DCA — {mensagem.get('anexo')} "
                         f"{'concluído' if desfecho == 'sucesso' else 'com erro'}",
                "description": "\n".join(linhas),
                "color": CORES.get(desfecho, CORES["erro"]),
            }]
        }

        if self._http is not None:
            self._http(self._webhook, json=corpo, timeout=TIMEOUT)
            return

        import requests

        resposta = requests.post(self._webhook, json=corpo, timeout=TIMEOUT)
        resposta.raise_for_status()
