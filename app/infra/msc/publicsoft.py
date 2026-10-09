"""Fonte PublicSoft — `base-demonstrativos`; o gate de auditoria é do servidor.

Implementa `FonteSaldos`. Duas diferenças que o adapter absorve, além do camelCase:

1. **A competência de encerramento é a 13**, não a 12. Nesta API, 12 é dezembro e 13 é a
   competência especial de encerramento do exercício — `?exercicio=2026&mesMsc=13`, ou o alias
   `?anReferencia=2026&meReferencia=13`. No SICONFI é o oposto: o encerramento está na
   competência 12, identificado por `co_tipo_matriz=MSCE`, e pedir 13 devolve zero registros
   (medido nos 4 entes de homologação em 2026-09-18). O domínio continua falando em competência
   1–12 mais a matriz; o número de cada API morre aqui.
2. A auditoria da competência é verificada pelo próprio `base-demonstrativos`, que responde
   **409** quando ela não está liberada. 409 significa **sem dados** — conjunto vazio, não
   exceção: um demonstrativo em auditoria não é uma falha de transporte. Não há pré-check em
   `/matriz-saldo/auditorias`: aquele endpoint exige o JWT do usuário, que o worker não tem — com
   o `token_ps` responde 401 (produção, 2026-10-06). RREO e RGF fazem o mesmo.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from decimal import Decimal
from http import HTTPStatus
from urllib.parse import urlsplit, urlunsplit

from app.domain.bo.modelo import Registro
from app.infra.msc.fonte import Matriz, TipoSaldo
from app.infra.msc.normalizacao import itens, normalizar

logger = logging.getLogger(__name__)

# Competência especial de encerramento do exercício nesta API (12 é dezembro).
COMPETENCIA_13 = 13

# Vocabulário do domínio -> o que esta API usa.
ID_TV = {
    TipoSaldo.ABERTURA: "beginning_balance",
    TipoSaldo.ENCERRAMENTO: "ending_balance",
    TipoSaldo.PERIODO: "period_change",
}

URL_SALDOS = os.getenv("PUBLICSOFT_API_URL", "")
TIMEOUT = int(os.getenv("PUBLICSOFT_TIMEOUT", "120"))
SSL_VERIFY = os.getenv("PUBLICSOFT_SSL_VERIFY", "true").lower() not in ("false", "0", "no")
POOL = int(os.getenv("PUBLICSOFT_POOL_MAXSIZE") or 12)   # `or`: variável vazia no .env
# Exigido pela API junto do `x-authorization` (sem ele, 401), como no RREO e no RGF.
RESPONSAVEL = (os.getenv("PUBLICSOFT_RESPONSAVEL_CONTABILIDADE") or "").strip()
CAMINHO_ESTORNO_RECEITA = "/contabilidade-tools/relatorios-gerenciais/estorno-receita-extra"
CAMINHO_ESTORNO_DESPESA = "/contabilidade-tools/relatorios-gerenciais/estorno-despesa-extra"


class EstornoIndisponivel(RuntimeError):
    """O relatório não trouxe `totalGeral`. O bruto da MSC não pode sair como líquido."""


def _impressoes(headers: dict | None) -> dict[str, str]:
    import hashlib

    return {nome: f"len={len(str(valor))} sha={hashlib.sha256(str(valor).encode()).hexdigest()[:8]}"
            for nome, valor in sorted((headers or {}).items())}


def _http_requests(url: str, params: dict | None = None, headers: dict | None = None,
                   timeout: int = TIMEOUT) -> dict:
    from app.infra.msc.http import sessao

    resposta = sessao(pool=POOL, verificar_ssl=SSL_VERIFY).get(
        url, params=params, headers=headers, timeout=timeout
    )
    if resposta.status_code == 401:
        # Nome + sha256[:8] de cada header: compara com o valor esperado sem expor segredo.
        logger.error("PublicSoft 401 | url=%s cabecalhos=%s", url, _impressoes(headers))
    resposta.raise_for_status()
    return resposta.json()


class PublicSoftMSC:
    """Adapter da API do ente. `http` é injetável para teste sem rede."""

    def __init__(self, http=_http_requests, token: str = "",
                 url_saldos: str = URL_SALDOS,
                 timeout: int = TIMEOUT, responsavel: str = RESPONSAVEL):
        self._http = http
        self._token = token
        self._url_saldos = url_saldos
        self._timeout = timeout
        self._responsavel = responsavel
        # A base por UG responde 422 a ente sem UG (MSC importada por CSV). Uma tentativa por
        # instância — uma por job —, depois a base oficial direto: o recorte desse ente é por PO.
        self._sem_ug = False

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz: Matriz = Matriz.CONSOLIDADA,
                  tipo_saldo: TipoSaldo = TipoSaldo.ENCERRAMENTO) -> Sequence[Registro]:
        import requests

        competencia = self._competencia(mes, matriz)
        # Só o que o DTO aceita: o pipe usa `forbidNonWhitelisted` (campo extra = 400).
        # A matriz já está na competência (13 = encerramento).
        params = {"anReferencia": ano, "meReferencia": competencia,
                  "classeConta": classe, "idTv": ID_TV[tipo_saldo]}
        try:
            resposta = self._saldos(params)
        except requests.HTTPError as erro:
            if erro.response is not None and erro.response.status_code == HTTPStatus.CONFLICT:
                logger.warning("PublicSoft 409 auditoria não liberada | ente=%s ano=%s "
                               "competencia=%s classe=%s", ente, ano, competencia, classe)
                return []
            raise
        return [normalizar(item) for item in itens(resposta)]

    def _saldos(self, params: dict) -> dict:
        """Base por UG (`/unidades-gestoras`, sem filtro); a oficial se o ente não tem UG."""
        import requests

        if not self._sem_ug:
            try:
                return self._http(f"{self._url_saldos}/unidades-gestoras", params=params,
                                  headers=self._cabecalhos(), timeout=self._timeout) or {}
            except requests.HTTPError as erro:
                resposta = erro.response
                if resposta is None or resposta.status_code != HTTPStatus.UNPROCESSABLE_ENTITY:
                    raise
                logger.warning("PublicSoft sem base por UG (422) | recorte por poder/órgão")
                self._sem_ug = True
        return self._http(self._url_saldos, params=params, headers=self._cabecalhos(),
                          timeout=self._timeout) or {}

    @staticmethod
    def _competencia(mes: int, matriz: Matriz) -> int:
        """Traduz a competência do domínio para a desta API.

        A matriz de encerramento vive na competência **13**; a consolidada, no próprio mês.
        """
        return COMPETENCIA_13 if matriz is Matriz.ENCERRAMENTO else mes

    def estorno_receita_extra(self, exercicio: int) -> Decimal:
        """`totalGeral` do estorno de receita. SICONFI não tem este método."""
        return self._total_geral(CAMINHO_ESTORNO_RECEITA, exercicio, "estorno de receita extra")

    def estorno_despesa_extra(self, exercicio: int) -> Decimal:
        """`totalGeral` do estorno de despesa. Sai só de L60, junto com o de receita."""
        return self._total_geral(CAMINHO_ESTORNO_DESPESA, exercicio, "estorno de despesa extra")

    def _total_geral(self, caminho: str, exercicio: int, nome: str) -> Decimal:
        resposta = self._http(
            self._url_relatorio(caminho),
            params={"exercicio": exercicio, "tipo": "sintetico"},
            headers=self._cabecalhos(),
            timeout=self._timeout,
        ) or {}
        bruto = (resposta.get("data") or {}).get("totalGeral")
        if bruto is None:
            raise EstornoIndisponivel(f"{nome} sem totalGeral no exercício {exercicio}")
        return Decimal(str(bruto))

    def _url_relatorio(self, caminho: str) -> str:
        marca = "/contabilidade-tools/"
        if marca in self._url_saldos:
            return self._url_saldos.split(marca)[0] + caminho
        partes = urlsplit(self._url_saldos)
        return urlunsplit((partes.scheme, partes.netloc, caminho, "", ""))

    def _cabecalhos(self) -> dict:
        cabecalhos = {"x-authorization": self._token} if self._token else {}
        if self._responsavel:
            cabecalhos["x-responsavel-contabilidade"] = self._responsavel
        return cabecalhos
