"""Sessão HTTP dos adapters de fonte: pool de conexões e retry de status.

Duas coisas que `requests.get` avulso não dá, e que a medição do RREO obrigou
(`regras-rreo-api/app/utils/http_sessions.py`):

1. **Pool.** Uma apuração do BF faz 18 leituras paginadas; sem pool, é um handshake TLS por
   página.
2. **Retry de 429 e 5xx, com `Retry-After`.** O SICONFI limita taxa sob carga, e a resposta 429
   não levanta `OSError` — o retry por exceção do adapter não a vê. Sem isso, a página falha e a
   matriz sai incompleta.
"""
from __future__ import annotations

import os
from functools import lru_cache

TENTATIVAS = int(os.getenv("MSC_HTTP_RETRIES") or 3)     # `or`: variável vazia no .env
STATUS_RETENTAVEIS = (429, 500, 502, 503, 504)


@lru_cache(maxsize=4)
def sessao(pool: int = 12, verificar_ssl: bool = True):
    """Sessão por (pool, verificação de SSL). Memorizada: o pool só serve se for reaproveitado."""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    sessao_http = requests.Session()
    sessao_http.verify = verificar_ssl
    if not verificar_ssl:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    politica = Retry(
        total=TENTATIVAS,
        backoff_factor=0.5,
        status_forcelist=list(STATUS_RETENTAVEIS),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adaptador = HTTPAdapter(pool_connections=pool, pool_maxsize=pool, max_retries=politica)
    sessao_http.mount("https://", adaptador)
    sessao_http.mount("http://", adaptador)
    return sessao_http
