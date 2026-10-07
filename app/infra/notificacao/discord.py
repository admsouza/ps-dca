"""Notificação no Discord, no padrão do RREO e do RGF. Síncrona, e sempre tolerante a falha.

Formatos de `regras-rgf-api/worker.py` (por anexo e resumo do pipeline) e de
`jobs_rgf_completo.py` (requisição recebida). A regra que não muda: a notificação **nunca** altera o
desfecho do job — quem trata a exceção é `services/pipeline/notificacao.py`, e aqui ela só é
levantada.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from app.infra.notificacao.ente import rotulo_ente

logger = logging.getLogger(__name__)

CORES = {"verde": 0x2ECC71, "cinza": 0x95A5A6, "vermelho": 0xE74C3C, "azul": 0x3498DB,
         "roxo": 0x9B59B6, "laranja": 0xF39C12}
FONTES = {"siconfi": "SICONFI", "publicsoft": "MSC-SIAFIC"}
TIMEOUT = 5
LIMITE_ERRO = 900
LIMITE_ERRO_RESUMO = 300


def formatar_duracao(ms: int | None) -> str:
    """`18.7s` abaixo de um minuto, `1m 13s` acima — o `fmt_duracao` dos irmãos."""
    ms = int(ms or 0)
    if ms < 59_950:
        return f"{(ms + 50) // 100 / 10:.1f}s"   # meio para cima: 850 ms é 0.9s, não 0.8s
    total = (ms + 500) // 1000
    return f"{total // 60}m {total % 60}s"


class DiscordNotificador:
    def __init__(self, webhook: str, http=None,
                 rotulo: Callable[[str], str] = rotulo_ente) -> None:
        self._webhook = webhook
        self._http = http
        self._rotulo = rotulo

    def enviar(self, mensagem: dict) -> None:
        montar = {"percurso": self._percurso, "recebida": self._recebida}.get(
            mensagem.get("tipo"), self._anexo)
        self._postar(montar(mensagem))

    # ─── mensagens ───────────────────────────────────────────────────────────

    def _anexo(self, m: dict) -> dict:
        ente = f"**{self._rotulo(m['ente'])}** | {m['exercicio']}"
        titulo = f"DCA {m['anexo']} — "
        if m.get("desfecho") == "cache":
            return _embed(titulo + "Cache ✅", f"{ente} | Dados já em cache", "cinza")
        if m.get("desfecho") == "erro":
            erro = str(m.get("erro") or "erro")[:LIMITE_ERRO]
            return _embed(titulo + "Falhou ❌", f"{ente}\n```{erro}```", "vermelho")
        return _embed(titulo + "Concluído ✅",
                      f"{ente} | Tempo: {formatar_duracao(m.get('duracao_ms'))}", "verde")

    def _percurso(self, m: dict) -> dict:
        anexos = m.get("anexos") or []
        falhas = [a for a in anexos if a["status"] == "erro"]
        concluidos = len(anexos) - len(falhas)
        titulo = (f"{'⚠️' if falhas else '✅'} {self._rotulo(m['ente'])}  {m['exercicio']} "
                  f"[Anual] — {m.get('solicitante') or 'desconhecido'}")
        descricao = (f"Fila concluída com {len(falhas)} falha(s)." if falhas
                     else f"{concluidos} anexo(s) concluído(s) com sucesso.")
        campos = [
            {"name": "Fonte MSC", "value": _fonte(m.get("fonte")), "inline": True},
            {"name": "Tempo total", "value": formatar_duracao(m.get("duracao_ms")),
             "inline": True},
            {"name": "Detalhamento", "value": "\n".join(_linha(a) for a in anexos) or "—",
             "inline": False},
        ]
        if falhas:
            campos.append({"name": "Erros", "inline": False, "value": "\n\n".join(
                f"**{a['anexo']}:** {str(a.get('erro_detalhe') or '—')[:LIMITE_ERRO_RESUMO]}"
                for a in falhas)})
        return _embed(titulo, descricao, "laranja" if falhas else "roxo", campos)

    def _recebida(self, m: dict) -> dict:
        anexos = m.get("anexos") or []
        alvo = "" if m.get("percurso") else f" {', '.join(anexos)}"
        modo = "Reprocessar" if m.get("forcar") else "Processar"
        titulo = (f"DCA{alvo} — Requisição Recebida ({modo}) [Anual] — "
                  f"{m.get('solicitante') or 'desconhecido'}")
        descricao = (
            f"Solicitação aceita e {'pipeline' if m.get('percurso') else ', '.join(anexos)} "
            f"enfileirado.\n"
            f"Ente: **{self._rotulo(m['ente'])}** | Exercício: **{m['exercicio']}**\n"
            f"Fonte MSC: **{_fonte(m.get('fonte'))}**\n"
            f"Fila => {', '.join(anexos)}"
        )
        return _embed(titulo, descricao, "azul")

    # ─── envio ───────────────────────────────────────────────────────────────

    def _postar(self, embed: dict) -> None:
        corpo = {"embeds": [embed]}
        if self._http is not None:
            self._http(self._webhook, json=corpo, timeout=TIMEOUT)
            return

        import requests

        resposta = requests.post(self._webhook, json=corpo, timeout=TIMEOUT)
        resposta.raise_for_status()


def de_configuracao(cfg) -> DiscordNotificador | None:
    """Canal de operação. `None` sem webhook — ambiente local apura sem notificar."""
    return DiscordNotificador(cfg.discord_webhook) if cfg.discord_webhook else None


def _embed(titulo: str, descricao: str, cor: str, campos: list[dict] | None = None) -> dict:
    embed = {"title": titulo, "description": descricao, "color": CORES[cor]}
    if campos:
        embed["fields"] = campos
    return embed


def _fonte(nome: str | None) -> str:
    return FONTES.get(str(nome or "").lower(), str(nome or "—"))


def _linha(anexo: dict) -> str:
    status = anexo["status"]
    if status == "em_cache":
        return f"{anexo['anexo']} — cache ✅"
    if status == "already_queued":
        return f"{anexo['anexo']} — em andamento ⏳"
    marca = "❌" if status == "erro" else "✅"
    return f"{anexo['anexo']} — {formatar_duracao(anexo.get('duracao_ms'))} {marca}"
