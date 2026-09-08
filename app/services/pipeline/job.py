"""O que o worker executa. Wrapper fino: delega ao apurador e registra o desfecho.

Nada de cálculo, consulta a fonte ou composição de demonstrativo aqui — é o requisito "rota e
worker apenas orquestram". O RGF paga a dívida oposta: `worker.py` com 1.760 linhas.

Cinco garantias no caminho de erro, e cada uma existe porque a ausência dela custa caro:

1. cache fica `erro` com o detalhe — **nunca** `ok` com matriz incompleta;
2. o estado do job fica `error` com o mesmo motivo, para o cliente que faz polling;
3. o lock é liberado, senão a identidade fica bloqueada até alguém apagar a chave;
4. a notificação sai igual — silêncio não pode significar duas coisas;
5. falha de notificação é logada e ignorada: job concluído não vira job perdido por webhook fora
   do ar.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from app.infra.fila import job_manager
from app.services.pipeline import notificacao
from app.services.pipeline.registry import validar_anexo
from app.services.pipeline.resultado import para_dados

logger = logging.getLogger(__name__)


def executar(*, ente: str, exercicio: int, anexo: str, repo, lock,
             apurador: Callable[[int, int], Any], versao_api: str, versao_regras: str,
             jobs=None, job_id: str | None = None, notificador=None,
             solicitado_por: int | None = None) -> dict | None:
    """Apura, grava e libera o lock. Devolve o resultado serializado, ou `None` em erro."""
    anexo = validar_anexo(anexo)
    inicio = time.monotonic()
    dados: dict | None = None
    erro: str | None = None

    try:
        resultado = apurador(int(ente), exercicio)
        dados = para_dados(resultado)
    except Exception as falha:
        erro = f"{type(falha).__name__}: {falha}"
        logger.exception("apuração falhou | anexo=%s ente=%s exercicio=%s", anexo, ente, exercicio)

    duracao_ms = int((time.monotonic() - inicio) * 1000)

    try:
        if erro is None:
            _gravar_ok(repo, ente, exercicio, anexo, dados, duracao_ms,
                       versao_api, versao_regras, solicitado_por)
            if jobs is not None and job_id:
                job_manager.concluir(jobs, job_id, dados)
        else:
            _gravar_erro(repo, ente, exercicio, anexo, erro, versao_api, versao_regras)
            if jobs is not None and job_id:
                job_manager.falhar(jobs, job_id, erro)
    finally:
        # Sempre. Lock retido por job que terminou é o órfão que trava a identidade.
        lock.liberar(ente, exercicio, anexo)

    notificacao.notificar_fim(
        notificador,
        ente=ente, exercicio=exercicio, anexo=anexo, duracao_ms=duracao_ms,
        desfecho="sucesso" if erro is None else "erro", erro=erro,
    )
    return dados


def _registro(repo, ente: str, exercicio: int, anexo: str):
    existente = repo.obter(ente, exercicio, anexo)
    if existente is not None:
        return existente

    from app.infra.cache.repositorio import Registro

    return Registro(id_ente=ente, an_referencia=exercicio, anexo=anexo, status="processando")


def _gravar_ok(repo, ente, exercicio, anexo, dados, duracao_ms,
               versao_api, versao_regras, solicitado_por) -> None:
    registro = _registro(repo, ente, exercicio, anexo)
    registro.status = "ok"
    registro.resultado = dados
    registro.erro_detalhe = None
    registro.versao_api = versao_api
    # A coluna guarda a versão **vigente** — é ela que a próxima requisição compara para decidir
    # servir ou reapurar. A procedência guarda a que a apuração de fato usou. Em produção são a
    # mesma; divergirem significa que a regra mudou entre o enfileiramento e a execução.
    registro.versao_regras = versao_regras
    apurada = dados["procedencia"]["versao_regras"]
    if apurada and apurada != versao_regras:
        logger.warning(
            "versao_regras mudou entre enfileirar e apurar | anexo=%s ente=%s vigente=%s "
            "apurada=%s — o cache será invalidado na próxima leitura",
            anexo, ente, versao_regras[:12], apurada[:12],
        )
    registro.procedencia = dados["procedencia"]
    registro.diagnostico = {**dados["diagnostico"], "duracao_ms": duracao_ms}
    if hasattr(registro, "duracao_ms"):
        registro.duracao_ms = duracao_ms
    if solicitado_por is not None:
        registro.solicitado_por = solicitado_por
    repo.gravar(registro)


def _gravar_erro(repo, ente, exercicio, anexo, erro, versao_api, versao_regras) -> None:
    registro = _registro(repo, ente, exercicio, anexo)
    registro.status = "erro"
    registro.resultado = None          # `ok` com zeros entraria no demonstrativo sem ninguém ver
    registro.erro_detalhe = erro
    registro.versao_api = versao_api
    registro.versao_regras = versao_regras
    repo.gravar(registro)
