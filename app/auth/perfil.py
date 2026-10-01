"""Flag do hub que libera a regra na tela.

O JWT só traz `sub`. `auditor_mapeamentos` e `adm_sistema` vivem em `GET /usuarios/me`
do hub (`regras-rgf-api`). O booleano fica em cache por um minuto, chaveado pelo hash
do token — o token em si não é guardado nem logado.
"""
from __future__ import annotations

import hashlib
import time

from app.core.config import config

TIMEOUT = 5.0
_TTL = 60.0
_cache: dict[str, tuple[float, bool]] = {}


class HubIndisponivel(RuntimeError):
    """O hub não confirmou o perfil. O acesso não é liberado."""


class SessaoRecusada(PermissionError):
    """O hub recusou o token."""


async def pode_ver_regra(token: str, http=None) -> bool:
    chave = hashlib.sha256(token.encode()).hexdigest()
    if http is None:
        guardado = _cache.get(chave)
        if guardado and time.monotonic() - guardado[0] < _TTL:
            return guardado[1]

    base = config().auth_api_url.rstrip("/")
    if not base:
        raise HubIndisponivel("AUTH_API_URL não configurada")
    resposta = await _perguntar(f"{base}/usuarios/me", token, http)
    status = resposta["status"]
    if status == 401:
        raise SessaoRecusada()
    if status != 200:
        raise HubIndisponivel(f"hub respondeu {status}")
    corpo = resposta.get("body") or {}
    permitido = bool(corpo.get("auditor_mapeamentos")) or bool(corpo.get("adm_sistema"))
    if http is None:
        _cache[chave] = (time.monotonic(), permitido)
        if len(_cache) > 256:
            _cache.pop(next(iter(_cache)))
    return permitido


async def _perguntar(url: str, token: str, http) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if http is not None:
        return await http(url, headers)
    import httpx

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as cliente:
            resposta = await cliente.get(url, headers=headers)
    except Exception as erro:
        raise HubIndisponivel(str(erro)) from erro
    corpo = resposta.json() if resposta.content else {}
    return {"status": resposta.status_code, "body": corpo}
