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


def fonte(nome: str | None = None, token: str | None = None):
    """Adapter de MSC pelo nome, com a memória da execução por cima."""
    escolhido = (nome or config().fonte_padrao).strip().lower()
    if escolhido == "publicsoft":
        from app.infra.msc.publicsoft import PublicSoftMSC

        bruta = PublicSoftMSC(token=token or "")
    else:
        from app.infra.msc.siconfi import SiconfiMSC

        bruta = SiconfiMSC()

    return _NoEscopo(bruta, escolhido)


class _NoEscopo:
    """Envolve a fonte na memória da execução, sem que a fonte saiba disso.

    Nada é persistido: o recorte lido vale para o job que o leu e some com ele — o ente retifica
    declaração já publicada, e dado guardado entre execuções serviria o número anterior à
    retificação (`app/infra/msc/cache.py`).
    """

    def __init__(self, bruta, nome: str = "") -> None:
        self._bruta = bruta
        self._nome = nome

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz=None, tipo_saldo=None):
        """Repassa o par de leitura **como recebido**.

        Omiti-lo é falha silenciosa: um demonstrativo que lê três origens — o BF lê a abertura do
        exercício, o encerramento e a abertura do exercício anterior — receberia três vezes a
        mesma, e `L25`, `L26` e `L29`–`L32` sairiam com números plausíveis e errados, sem exceção
        e sem célula não apurada. `ler_ou_baixar` já inclui o par na chave; faltava chegar até ele.
        """
        from app.infra.msc.cache import ler_ou_baixar

        return ler_ou_baixar(fonte=self._bruta, ente=ente, ano=ano, mes=mes, classe=classe,
                             matriz=matriz, tipo_saldo=tipo_saldo, fonte_nome=self._nome)

    def __getattr__(self, nome: str):
        """O que a fonte bruta sabe fazer além de `registros` — o estorno, na PublicSoft."""
        return getattr(self._bruta, nome)


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
    from app.services.pipeline.registry import anexo as descrever

    return carregar(exercicio, demonstrativo=descrever(anexo).base_canonica)


def apurador(anexo: str = "BO", *, fonte_nome: str | None = None, token: str | None = None,
             repo_vigencias=None, parametros: dict | None = None) -> Callable[[int, int], Any]:
    """A função `(ente, exercicio) -> Resultado` que o worker executa.

    A versão de regras **não** sai daqui: ela depende do exercício, e quem precisa dela antes de
    apurar (a rota, para decidir invalidação) chama `versao_regras(exercicio)`.
    """
    from app.services.pipeline.registry import anexo as descrever

    descricao = descrever(anexo)
    if descricao.servico is None:
        raise NotImplementedError(f"anexo {descricao.codigo} ainda não tem serviço de apuração")

    dados = fonte(fonte_nome, token)

    apurar = _servico_de(descricao.codigo)
    extras = _aceitos_por(apurar, parametros or {})

    def _apurar(ente: int, exercicio: int):
        return apurar(ente, exercicio, fonte=dados,
                      mapa=mapa_vigente(exercicio, descricao.codigo, repo_vigencias),
                      **extras)

    return _apurar


def _aceitos_por(servico: Callable, parametros: dict) -> dict:
    """Só os parâmetros que a assinatura do serviço declara.

    Um job para todos os anexos significa um payload que serve a todos: o BF aceita a origem da
    coluna do exercício anterior e o BO não. Repassar cegamente levantaria `TypeError` dentro do
    worker, e o anexo ficaria preso em `processando` até o lock expirar.
    """
    from inspect import signature

    aceitos = signature(servico).parameters
    return {nome: valor for nome, valor in parametros.items() if nome in aceitos}


def _servico_de(anexo: str):
    """A função de apuração que o registry declara para o anexo.

    Era o serviço do BO, importado de forma fixa: o BF seria apurado pelas regras do IPC 07 sobre
    as classes do BO — número errado, sem erro nenhum.
    """
    from importlib import import_module

    from app.services.pipeline.registry import anexo as descrever

    servico = descrever(anexo).servico
    if servico is None:
        raise NotImplementedError(f"anexo {anexo} ainda não tem serviço de apuração")
    modulo, funcao = servico.split(":")
    return getattr(import_module(modulo), funcao)


def versao_regras(exercicio: int, anexo: str = "BO", repo_vigencias=None) -> str:
    """A versão vigente, para a rota decidir invalidação sem apurar nada."""
    return mapa_vigente(exercicio, anexo, repo_vigencias).versao_regras
