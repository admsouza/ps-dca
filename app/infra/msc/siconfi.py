"""Fonte SICONFI — `tt/msc_*`, API pública do Tesouro.

Implementa `FonteSaldos`. Quatro coisas que a medição obrigou:

1. **Paginação ORDS é obrigatória.** Blocos de 5.000, seguindo `hasMore`. Um município grande
   excede uma página, e parar na primeira devolve matriz incompleta sem erro nenhum.
2. **O par (matriz, tipo de saldo) vem do demonstrativo**, não daqui — `app/infra/msc/fonte.py`.
   Este módulo só traduz o vocabulário do domínio para o da API.
3. **A matriz de encerramento só existe na competência 12.** Pedi-la em outro mês devolveria
   vazio, e vazio numa apuração vira demonstrativo zerado, não erro: por isso é recusa explícita.
   Qual par cada demonstrativo usa é decidido em `fonte.py`, não aqui.
4. **Retry com backoff.** Na medição de 2026-09-14, 2 de ~40 chamadas caíram por reset de
   conexão. Numa coleta paginada, falha silenciosa vira matriz incompleta — resultado errado com
   aparência de certo.
"""
from __future__ import annotations

import os
import time
from collections.abc import Sequence

from app.domain.bo.modelo import Registro
from app.infra.msc.fonte import COMPETENCIA_DE_ENCERRAMENTO, Matriz, TipoSaldo
from app.infra.msc.normalizacao import itens, normalizar

URL_PADRAO = os.getenv("SICONFI_API_URL", "https://apidatalake.tesouro.gov.br/ords/siconfi")
TIMEOUT = int(os.getenv("SICONFI_TIMEOUT", "30"))
POOL = int(os.getenv("SICONFI_POOL_MAXSIZE") or 12)      # `or`: variável vazia no .env

ENDPOINT_POR_CLASSE = {
    1: "msc_patrimonial", 2: "msc_patrimonial", 3: "msc_patrimonial", 4: "msc_patrimonial",
    5: "msc_orcamentaria", 6: "msc_orcamentaria",
    7: "msc_controle", 8: "msc_controle",
}
LIMITE = 5000
TENTATIVAS = 5
ESPERA_BASE = 3.0

# Vocabulário do domínio -> vocabulário da API. O núcleo não conhece estes nomes.
CO_TIPO_MATRIZ = {Matriz.CONSOLIDADA: "MSCC", Matriz.ENCERRAMENTO: "MSCE"}
ID_TV = {
    TipoSaldo.ABERTURA: "beginning_balance",
    TipoSaldo.ENCERRAMENTO: "ending_balance",
    TipoSaldo.PERIODO: "period_change",
}


def _http_requests(url: str, params: dict, timeout: int) -> dict:
    # Sessão compartilhada: pool de conexões entre as páginas e retry de 429/5xx, que o retry
    # por exceção abaixo não enxerga. Importada aqui — o domínio nunca alcança a rede.
    from app.infra.msc.http import sessao

    resposta = sessao(pool=POOL).get(url, params=params, timeout=timeout)
    resposta.raise_for_status()
    return resposta.json()


class SiconfiMSC:
    """Adapter da API pública. `http` e `espera` são injetáveis para teste sem rede."""

    def __init__(self, http=_http_requests, url: str = URL_PADRAO, timeout: int = TIMEOUT,
                 espera=time.sleep):
        self._http = http
        self._url = url.rstrip("/")
        self._timeout = timeout
        self._espera = espera

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz: Matriz = Matriz.CONSOLIDADA,
                  tipo_saldo: TipoSaldo = TipoSaldo.ENCERRAMENTO) -> Sequence[Registro]:
        _conferir_par(matriz, tipo_saldo, mes)

        url = f"{self._url}/tt/{ENDPOINT_POR_CLASSE[classe]}"
        coletados: list[Registro] = []
        offset = 0

        while True:
            resposta = self._pedir(url, ente, ano, mes, classe, matriz, tipo_saldo, offset) or {}
            pagina = itens(resposta)
            coletados.extend(normalizar(item) for item in pagina)
            if not resposta.get("hasMore") or not pagina:
                return coletados
            offset += LIMITE

    def _pedir(self, url, ente, ano, mes, classe, matriz, tipo_saldo, offset) -> dict:
        params = {
            "id_ente": ente,
            "an_referencia": ano,
            "me_referencia": mes,
            "co_tipo_matriz": CO_TIPO_MATRIZ[matriz],
            "classe_conta": classe,
            "id_tv": ID_TV[tipo_saldo],
            "offset": offset,
            "limit": LIMITE,
        }
        ultima: Exception | None = None
        for tentativa in range(TENTATIVAS):
            try:
                return self._http(url, params=params, timeout=self._timeout)
            except (ConnectionError, TimeoutError, OSError) as falha:
                ultima = falha
                self._espera(ESPERA_BASE * (tentativa + 1))
        raise ConnectionError(
            f"MSC indisponível após {TENTATIVAS} tentativas — classe {classe}, offset {offset}, "
            f"ente {ente}, {ano}/{mes:02d}"
        ) from ultima


def _conferir_par(matriz: Matriz, tipo_saldo: TipoSaldo, mes: int) -> None:
    """Recusa o que a API não tem.

    A combinação `encerramento` + saldo de encerramento é legítima para o Balanço Patrimonial e
    errada para os demais — mas isso é **norma por demonstrativo**, e a barreira vive em
    `fonte.fonte_de`, que nunca a produz fora do BP. Aqui só se recusa o que não existe.
    """
    if matriz is Matriz.ENCERRAMENTO and mes != COMPETENCIA_DE_ENCERRAMENTO:
        raise ValueError(
            f"a matriz de encerramento só existe na competência {COMPETENCIA_DE_ENCERRAMENTO}; "
            f"pedida para {mes:02d}"
        )
