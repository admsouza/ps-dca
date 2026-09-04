"""Fonte SICONFI — `tt/msc_orcamentaria`, API pública do Tesouro.

Implementa `FonteSaldos`. Duas coisas que a medição obrigou:

1. **Paginação ORDS é obrigatória.** Blocos de 5.000, seguindo `hasMore`. Um município grande
   excede uma página, e parar na primeira devolve matriz incompleta sem erro nenhum.
2. **`id_tv` é sempre `ending_balance`.** A DCA é anual e todas as colunas do BO são posição
   acumulada; `period_change` não é consultado.
"""
from __future__ import annotations

import os
from collections.abc import Sequence

from app.domain.bo.modelo import Registro
from app.infra.msc.normalizacao import itens, normalizar

URL_PADRAO = os.getenv("SICONFI_API_URL", "https://apidatalake.tesouro.gov.br/ords/siconfi")
TIMEOUT = int(os.getenv("SICONFI_TIMEOUT", "30"))

ENDPOINT_POR_CLASSE = {
    1: "msc_patrimonial", 2: "msc_patrimonial", 3: "msc_patrimonial", 4: "msc_patrimonial",
    5: "msc_orcamentaria", 6: "msc_orcamentaria",
    7: "msc_controle", 8: "msc_controle",
}
LIMITE = 5000


def _http_requests(url: str, params: dict, timeout: int) -> dict:
    import requests  # importado aqui: o domínio nunca alcança a dependência de rede

    resposta = requests.get(url, params=params, timeout=timeout)
    resposta.raise_for_status()
    return resposta.json()


class SiconfiMSC:
    """Adapter da API pública. `http` é injetável para teste sem rede."""

    def __init__(self, http=_http_requests, url: str = URL_PADRAO, timeout: int = TIMEOUT):
        self._http = http
        self._url = url.rstrip("/")
        self._timeout = timeout

    def registros(self, ente: int, ano: int, mes: int, classe: int) -> Sequence[Registro]:
        endpoint = ENDPOINT_POR_CLASSE[classe]
        url = f"{self._url}/tt/{endpoint}"
        coletados: list[Registro] = []
        offset = 0

        while True:
            resposta = self._http(
                url,
                params={
                    "id_ente": ente,
                    "an_referencia": ano,
                    "me_referencia": mes,
                    "co_tipo_matriz": "MSCC",
                    "classe_conta": classe,
                    "id_tv": "ending_balance",
                    "offset": offset,
                    "limit": LIMITE,
                },
                timeout=self._timeout,
            ) or {}
            pagina = itens(resposta)
            coletados.extend(normalizar(item) for item in pagina)
            if not resposta.get("hasMore") or not pagina:
                return coletados
            offset += LIMITE
