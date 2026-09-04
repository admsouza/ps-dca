"""Fonte PublicSoft — `base-demonstrativos`, com gate de auditoria.

Implementa `FonteSaldos`. A diferença que o adapter absorve, além do camelCase: antes de
buscar saldos, a auditoria do exercício/mês precisa estar `validado` **e** `podeGerar`.
Reprovado significa **sem dados** — conjunto vazio, não exceção: um demonstrativo em auditoria
não é uma falha de transporte, e tratá-lo como erro esconderia a diferença.
"""
from __future__ import annotations

import os
from collections.abc import Sequence

from app.domain.bo.modelo import Registro
from app.infra.msc.normalizacao import itens, normalizar

URL_SALDOS = os.getenv("PUBLICSOFT_API_URL", "")
URL_AUDITORIA = os.getenv("PUBLICSOFT_AUDIT_URL", "")
TIMEOUT = int(os.getenv("PUBLICSOFT_TIMEOUT", "120"))
SSL_VERIFY = os.getenv("PUBLICSOFT_SSL_VERIFY", "true").lower() not in ("false", "0", "no")


def _http_requests(url: str, params: dict | None = None, headers: dict | None = None,
                   timeout: int = TIMEOUT) -> dict:
    import requests

    resposta = requests.get(url, params=params, headers=headers, timeout=timeout,
                            verify=SSL_VERIFY)
    resposta.raise_for_status()
    return resposta.json()


class PublicSoftMSC:
    """Adapter da API do ente. `http` é injetável para teste sem rede."""

    def __init__(self, http=_http_requests, token: str = "",
                 url_saldos: str = URL_SALDOS, url_auditoria: str = URL_AUDITORIA,
                 timeout: int = TIMEOUT):
        self._http = http
        self._token = token
        self._url_saldos = url_saldos
        self._url_auditoria = url_auditoria
        self._timeout = timeout

    def registros(self, ente: int, ano: int, mes: int, classe: int) -> Sequence[Registro]:
        if not self._auditoria_liberada(ano, mes):
            return []

        resposta = self._http(
            self._url_saldos,
            params={"anReferencia": ano, "meReferencia": mes,
                    "classeConta": classe, "idTv": "ending_balance"},
            headers=self._cabecalhos(),
            timeout=self._timeout,
        ) or {}
        return [normalizar(item) for item in itens(resposta)]

    def _auditoria_liberada(self, ano: int, mes: int) -> bool:
        resposta = self._http(
            self._url_auditoria,
            params={"exercicio": ano, "mesMsc": mes},
            headers=self._cabecalhos(),
            timeout=self._timeout,
        ) or {}
        return resposta.get("status") == "validado" and resposta.get("podeGerar") is True

    def _cabecalhos(self) -> dict:
        return {"x-authorization": self._token} if self._token else {}
