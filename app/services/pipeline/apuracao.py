"""Monta o apurador de um anexo: mapa vigente + fonte de dados + direção do saldo.

Um lugar só, chamado por rota (para descobrir a versão vigente), worker (para apurar) e CLI. O
apurador que sai daqui é uma função de `(ente, exercicio)` — o worker não sabe de onde vieram o
mapa nem a fonte, e é isso que torna a apuração testável sem infraestrutura.

A versão de regras vem daqui, não de constante: é a chave de invalidação do cache, e uma correção
de conta em `knowledge/rules/**.yaml` tem de invalidar sozinha.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.core.config import config

logger = logging.getLogger(__name__)

# Versão da apuração da DCA. Muda quando o **código** de apuração muda; a mudança de regra é
# capturada por `versao_regras`, que é hash do conteúdo.
VERSAO_API = "0.1.0"


def fonte(nome: str | None = None, token: str | None = None, cache=None):
    """Adapter de MSC pelo nome. `cache` compartilha o espaço `msc_cache:` com RREO e RGF."""
    escolhido = (nome or config().fonte_padrao).strip().lower()
    if escolhido == "publicsoft":
        from app.infra.msc.publicsoft import PublicSoftMSC

        bruta = PublicSoftMSC(token=token or "")
    else:
        from app.infra.msc.siconfi import SiconfiMSC

        bruta = SiconfiMSC()

    return _ComCache(bruta, cache) if cache is not None else bruta


class _ComCache:
    """Envolve a fonte no cache de dados comum, sem que a fonte saiba disso."""

    def __init__(self, bruta, cache) -> None:
        self._bruta = bruta
        self._cache = cache

    def registros(self, ente: int, ano: int, mes: int, classe: int):
        from app.infra.msc.cache import ler_ou_baixar

        return ler_ou_baixar(fonte=self._bruta, cache=self._cache,
                             ente=ente, ano=ano, mes=mes, classe=classe)


def mapa_vigente(exercicio: int, anexo: str = "BO", repo_vigencias=None):
    """Mapa do anexo para o exercício. Do banco quando houver repositório; do YAML na semente.

    O YAML continua servindo de semente e de fallback de boot: um banco recém-criado ainda não tem
    vigência, e recusar a apuração nesse instante deixaria a DCA sem responder até alguém rodar o
    seed à mão.
    """
    if repo_vigencias is not None:
        from app.infra.regras.carregador import SemVigencia
        from app.infra.regras.vigencias import carregar as carregar_do_banco

        try:
            return carregar_do_banco(repo_vigencias, anexo, exercicio)
        except SemVigencia:
            logger.warning(
                "sem vigência publicada para %s/%s — caindo no YAML versionado (semente)",
                anexo, exercicio,
            )

    from app.infra.regras.carregador import carregar

    return carregar(exercicio)


def apurador(anexo: str = "BO", *, fonte_nome: str | None = None, token: str | None = None,
             cache=None, repo_vigencias=None) -> Callable[[int, int], Any]:
    """A função `(ente, exercicio) -> Resultado` que o worker executa.

    A versão de regras **não** sai daqui: ela depende do exercício, e quem precisa dela antes de
    apurar (a rota, para decidir invalidação) chama `versao_regras(exercicio)`.
    """
    from app.services.pipeline.registry import anexo as descrever

    descricao = descrever(anexo)
    if descricao.servico is None:
        raise NotImplementedError(f"anexo {descricao.codigo} ainda não tem serviço de apuração")

    dados = fonte(fonte_nome, token, cache)

    def _apurar(ente: int, exercicio: int):
        from app.services.bo.quadro_principal import apurar

        return apurar(ente, exercicio, fonte=dados,
                      mapa=mapa_vigente(exercicio, descricao.codigo, repo_vigencias))

    return _apurar


def versao_regras(exercicio: int, anexo: str = "BO", repo_vigencias=None) -> str:
    """A versão vigente, para a rota decidir invalidação sem apurar nada."""
    return mapa_vigente(exercicio, anexo, repo_vigencias).versao_regras
