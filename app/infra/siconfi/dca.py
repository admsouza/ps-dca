"""DCA publicada no SICONFI — `tt/dca`, API pública do Tesouro.

Lê o que o ente **declarou** (`DCA-Anexo I-AB` do exercício anterior), sempre do SICONFI, qualquer
que seja a fonte da MSC (change `bp-anterior-publicado-siconfi`, D4). Mesmo padrão da MSC: paginação
ORDS por `hasMore`, timeout explícito e retry com backoff. Indisponibilidade levanta
`ConnectionError`: o chamador nunca troca a DCA publicada pela MSC por omissão.
"""
from __future__ import annotations

import time

from app.infra.msc.normalizacao import itens as _itens
from app.infra.msc.siconfi import (
    ESPERA_BASE,
    LIMITE,
    TENTATIVAS,
    TIMEOUT,
    URL_PADRAO,
    _http_requests,
)

ANEXO_BP = "DCA-Anexo I-AB"


class SiconfiDCA:
    """Adapter do `tt/dca`. `http` e `espera` são injetáveis para teste sem rede."""

    def __init__(self, http=_http_requests, url: str = URL_PADRAO, timeout: int = TIMEOUT,
                 espera=time.sleep):
        self._http = http
        self._url = url.rstrip("/")
        self._timeout = timeout
        self._espera = espera

    def itens(self, ente: int, ano: int, anexo: str = ANEXO_BP) -> list[dict]:
        """Todos os itens do anexo declarado; lista vazia = o ente não publicou."""
        coletados: list[dict] = []
        offset = 0
        while True:
            resposta = self._pedir(ente, ano, anexo, offset) or {}
            pagina = _itens(resposta)
            coletados.extend(pagina)
            if not resposta.get("hasMore") or not pagina:
                return coletados
            offset += LIMITE

    def _pedir(self, ente: int, ano: int, anexo: str, offset: int) -> dict:
        params = {"an_exercicio": ano, "no_anexo": anexo, "id_ente": ente,
                  "offset": offset, "limit": LIMITE}
        ultima: Exception | None = None
        for tentativa in range(TENTATIVAS):
            try:
                return self._http(f"{self._url}/tt/dca", params=params, timeout=self._timeout)
            except (ConnectionError, TimeoutError, OSError) as falha:
                ultima = falha
                self._espera(ESPERA_BASE * (tentativa + 1))
        raise ConnectionError(
            f"DCA publicada indisponível após {TENTATIVAS} tentativas — {anexo}, offset {offset}, "
            f"ente {ente}, {ano}"
        ) from ultima
