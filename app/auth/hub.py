"""Autorização de unidade contra o hub — `POST {AUTH_API_URL}/internal/authorize`.

O mesmo contrato que `regras-rgf-api/app/utils/demonstrativos_client.py` já usa em produção:
`{"sub", "cod_ibge"}` com `X-Internal-Secret`, e `403` significa "sem acesso à unidade".

**Por que não basta o claim do token.** No hub, quem pode ler qual ente é dado de banco, não de
token: um usuário ganha ou perde unidade sem reemitir JWT. Ler a permissão de um claim entregaria
autorização congelada no momento da emissão.

Falha de rede vira `503`, nunca `200`: indisponibilidade do hub não pode virar acesso liberado
(fail closed).
"""
from __future__ import annotations

import logging

from app.core.config import config

logger = logging.getLogger(__name__)

TIMEOUT = 3.0
CAMINHO = "/internal/authorize"


class HubIndisponivel(RuntimeError):
    """O hub não respondeu. O acesso **não** é liberado por isso."""


class SemAcessoAUnidade(PermissionError):
    """O hub negou: este usuário não tem a unidade pedida."""


class AutorizadorHub:
    """Confirma no hub que `sub` pode ler `cod_ibge`."""

    def __init__(self, base_url: str | None = None, secret: str | None = None, http=None) -> None:
        cfg = config()
        self._base = (base_url or cfg.auth_api_url).rstrip("/")
        self._secret = secret or cfg.s2s_secret
        self._http = http

    @property
    def configurado(self) -> bool:
        return bool(self._base and self._secret)

    async def autorizar(self, sub: str, cod_ibge: str) -> None:
        if not self.configurado:
            raise HubIndisponivel("AUTH_API_URL/S2S_API_SECRET não configurados")

        try:
            resposta = await self._chamar(sub, cod_ibge)
        except Exception as erro:
            logger.error("hub inacessível | unidade=%s -> %s", cod_ibge, erro)
            raise HubIndisponivel(str(erro)) from erro

        codigo = resposta["status"]
        if codigo == 403:
            raise SemAcessoAUnidade(f"usuário sem acesso à unidade {cod_ibge}")
        if codigo != 200:
            # 401 e 5xx são problema **nosso** com o hub, não do requisitante.
            raise HubIndisponivel(f"hub respondeu {codigo}")

    async def _chamar(self, sub: str, cod_ibge: str) -> dict:
        corpo = {"sub": sub, "cod_ibge": cod_ibge}
        cabecalhos = {"X-Internal-Secret": self._secret}

        if self._http is not None:                      # dublê nos testes
            return await self._http(f"{self._base}{CAMINHO}", json=corpo, headers=cabecalhos)

        import httpx

        async with httpx.AsyncClient(timeout=TIMEOUT) as cliente:
            resposta = await cliente.post(f"{self._base}{CAMINHO}", json=corpo,
                                          headers=cabecalhos)
        return {"status": resposta.status_code}
