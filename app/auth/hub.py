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
CAMINHO_TENANT = "/internal/resolve-tenant"
# Vocabulário de `usuario_poder` no hub. Valor fora dele não concede nada.
PODERES = ("consolidado", "executivo", "judiciario", "legislativo")


class HubIndisponivel(RuntimeError):
    """O hub não respondeu. O acesso **não** é liberado por isso."""


class SemAcessoAUnidade(PermissionError):
    """O hub negou: este usuário não tem a unidade pedida."""


class EnteNaoEncontrado(LookupError):
    """O hub não conhece a unidade."""


class EnteSemToken(LookupError):
    """A unidade não tem `token_ps` configurado no hub."""


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

    async def autorizar(self, sub: str, cod_ibge: str) -> tuple[str, ...]:
        """Confirma o vínculo e devolve os poderes do usuário (`regras-rgf-api` CH-46).

        Hub anterior à CH-46, sem o campo, devolve `()`: BO e BP respondem `403` até o hub subir —
        fail closed, nunca o consolidado por omissão.
        """
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
        poderes = (resposta.get("corpo") or {}).get("poderes") or []
        return tuple(p for p in poderes if p in PODERES)

    async def resolver_token(self, sub: str, cod_ibge: str) -> str:
        """`token_ps` da unidade — `POST /internal/resolve-tenant`, o contrato do RGF e do RREO.

        Vai para a PublicSoft em `x-authorization`. Nunca é logado.
        """
        if not self.configurado:
            raise HubIndisponivel("AUTH_API_URL/S2S_API_SECRET não configurados")

        try:
            resposta = await self._chamar(sub, cod_ibge, CAMINHO_TENANT)
        except Exception as erro:
            logger.error("hub inacessível ao resolver token | unidade=%s -> %s", cod_ibge, erro)
            raise HubIndisponivel(str(erro)) from erro

        codigo = resposta["status"]
        if codigo == 403:
            raise SemAcessoAUnidade(f"usuário sem acesso à unidade {cod_ibge}")
        if codigo == 404:
            raise EnteNaoEncontrado(f"unidade {cod_ibge} não encontrada no hub")
        if codigo == 409:
            raise EnteSemToken(f"unidade {cod_ibge} sem token PublicSoft configurado")
        if codigo != 200:
            raise HubIndisponivel(f"hub respondeu {codigo}")
        corpo = resposta.get("corpo") or {}
        token = corpo.get("token_ps")
        # Sem token SIAFIC o hub responde 200 com `token_ps = cod_ibge` e `siafic_disponivel=false`
        # (fallback MSC CSV do RREO/RGF). Usar isso como `x-authorization` dá 401 na PublicSoft.
        if not token or corpo.get("siafic_disponivel") is False:
            raise EnteSemToken(f"unidade {cod_ibge} sem token PublicSoft (SIAFIC) no hub")
        return str(token)

    async def _chamar(self, sub: str, cod_ibge: str, caminho: str = CAMINHO) -> dict:
        corpo = {"sub": sub, "cod_ibge": cod_ibge}
        cabecalhos = {"X-Internal-Secret": self._secret}

        if self._http is not None:                      # dublê nos testes
            return await self._http(f"{self._base}{caminho}", json=corpo, headers=cabecalhos)

        import httpx

        async with httpx.AsyncClient(timeout=TIMEOUT) as cliente:
            resposta = await cliente.post(f"{self._base}{caminho}", json=corpo,
                                          headers=cabecalhos)
        dados = resposta.json() if resposta.status_code == 200 else {}
        return {"status": resposta.status_code, "corpo": dados if isinstance(dados, dict) else {}}
