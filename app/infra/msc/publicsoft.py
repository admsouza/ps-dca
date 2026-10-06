"""Fonte PublicSoft — `base-demonstrativos`, com gate de auditoria.

Implementa `FonteSaldos`. Duas diferenças que o adapter absorve, além do camelCase:

1. **A competência de encerramento é a 13**, não a 12. Nesta API, 12 é dezembro e 13 é a
   competência especial de encerramento do exercício — `?exercicio=2026&mesMsc=13`, ou o alias
   `?anReferencia=2026&meReferencia=13`. No SICONFI é o oposto: o encerramento está na
   competência 12, identificado por `co_tipo_matriz=MSCE`, e pedir 13 devolve zero registros
   (medido nos 4 entes de homologação em 2026-09-18). O domínio continua falando em competência
   1–12 mais a matriz; o número de cada API morre aqui.
2. Antes de buscar saldos, a auditoria do exercício/mês precisa estar `validado` **e**
   `podeGerar`. Reprovado significa **sem dados** — conjunto vazio, não exceção: um
   demonstrativo em auditoria não é uma falha de transporte, e tratá-lo como erro esconderia a
   diferença.
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

from app.domain.bo.modelo import Registro
from app.infra.msc.fonte import Matriz, TipoSaldo
from app.infra.msc.normalizacao import itens, normalizar

# Competência especial de encerramento do exercício nesta API (12 é dezembro).
COMPETENCIA_13 = 13

# Vocabulário do domínio -> o que esta API usa.
ID_TV = {
    TipoSaldo.ABERTURA: "beginning_balance",
    TipoSaldo.ENCERRAMENTO: "ending_balance",
    TipoSaldo.PERIODO: "period_change",
}

URL_SALDOS = os.getenv("PUBLICSOFT_API_URL", "")
URL_AUDITORIA = os.getenv("PUBLICSOFT_AUDIT_URL", "")
TIMEOUT = int(os.getenv("PUBLICSOFT_TIMEOUT", "120"))
SSL_VERIFY = os.getenv("PUBLICSOFT_SSL_VERIFY", "true").lower() not in ("false", "0", "no")
POOL = int(os.getenv("PUBLICSOFT_POOL_MAXSIZE") or 12)   # `or`: variável vazia no .env
# Exigido pela API junto do `x-authorization` (sem ele, 401), como no RREO e no RGF.
RESPONSAVEL = (os.getenv("PUBLICSOFT_RESPONSAVEL_CONTABILIDADE") or "").strip()
CAMINHO_ESTORNO_RECEITA = "/contabilidade-tools/relatorios-gerenciais/estorno-receita-extra"
CAMINHO_ESTORNO_DESPESA = "/contabilidade-tools/relatorios-gerenciais/estorno-despesa-extra"


class EstornoIndisponivel(RuntimeError):
    """O relatório não trouxe `totalGeral`. O bruto da MSC não pode sair como líquido."""


def _http_requests(url: str, params: dict | None = None, headers: dict | None = None,
                   timeout: int = TIMEOUT) -> dict:
    from app.infra.msc.http import sessao

    resposta = sessao(pool=POOL, verificar_ssl=SSL_VERIFY).get(
        url, params=params, headers=headers, timeout=timeout
    )
    resposta.raise_for_status()
    return resposta.json()


class PublicSoftMSC:
    """Adapter da API do ente. `http` é injetável para teste sem rede."""

    def __init__(self, http=_http_requests, token: str = "",
                 url_saldos: str = URL_SALDOS, url_auditoria: str = URL_AUDITORIA,
                 timeout: int = TIMEOUT, responsavel: str = RESPONSAVEL):
        self._http = http
        self._token = token
        self._url_saldos = url_saldos
        self._url_auditoria = url_auditoria
        self._timeout = timeout
        self._responsavel = responsavel

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz: Matriz = Matriz.CONSOLIDADA,
                  tipo_saldo: TipoSaldo = TipoSaldo.ENCERRAMENTO) -> Sequence[Registro]:
        competencia = self._competencia(mes, matriz)
        if not self._auditoria_liberada(ano, competencia):
            return []

        resposta = self._http(
            self._url_saldos,
            params={"anReferencia": ano, "meReferencia": competencia,
                    "classeConta": classe, "idTv": ID_TV[tipo_saldo],
                    "tipoMatriz": str(matriz)},
            headers=self._cabecalhos(),
            timeout=self._timeout,
        ) or {}
        return [normalizar(item) for item in itens(resposta)]

    @staticmethod
    def _competencia(mes: int, matriz: Matriz) -> int:
        """Traduz a competência do domínio para a desta API.

        A matriz de encerramento vive na competência **13**; a consolidada, no próprio mês. É a
        auditoria dessa mesma competência que libera a leitura — auditar dezembro e ler o
        encerramento liberaria uma competência com base na validação de outra.
        """
        return COMPETENCIA_13 if matriz is Matriz.ENCERRAMENTO else mes

    def _auditoria_liberada(self, ano: int, mes: int) -> bool:
        """Uma consulta por competência **por job**: o gate é o mesmo para as seis classes.

        Sem a memória de execução eram seis chamadas idênticas por leitura de matriz — dezoito num
        BF — para a API responder sempre a mesma coisa. Fora de um escopo aberto (CLI, teste), o
        comportamento é o de antes: consulta a cada chamada.
        """
        from app.infra.msc.escopo import obter_ou_buscar

        # ponytail: chave sem o ente — um job apura um ente só. Se um job passar a apurar vários,
        # o ente entra aqui.
        return obter_ou_buscar(f"auditoria:{ano}:{mes}",
                               lambda: self._consultar_auditoria(ano, mes))

    def _consultar_auditoria(self, ano: int, mes: int) -> bool:
        resposta = self._http(
            self._url_auditoria,
            params={"exercicio": ano, "mesMsc": mes},
            headers=self._cabecalhos(),
            timeout=self._timeout,
        ) or {}
        return resposta.get("status") == "validado" and resposta.get("podeGerar") is True

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
