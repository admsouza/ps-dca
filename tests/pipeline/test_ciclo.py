"""Ciclo único de requisição, cache e job — os quatro caminhos da leitura de um anexo.

Nenhum destes testes toca HTTP: o que a spec fixa é a **decisão**, e a rota só a transporta. É o
que permite trocar FastAPI sem reescrever o teste, e é o mesmo motivo pelo qual a apuração é
alcançável sem rota e sem worker.
"""
from __future__ import annotations

import pytest

from tests.pipeline.conftest import (
    ANEXO,
    ENTE,
    EXERCICIO,
    OUTRA_VERSAO_REGRAS,
    RegistroFake,
)


def test_cache_valido_serve_sem_enfileirar(pedido, registro_ok, fila):
    """Scenario: cache válido."""
    r = pedido()
    assert r.status == 200
    assert r.resultado == registro_ok.resultado
    assert fila.enfileirados == [], "cache válido não pode disparar job"


def test_cache_ausente_cria_job(pedido, repo, fila):
    """Scenario: cache ausente.

    `202` com as três chaves de acompanhamento, e o registro já em `processando` **antes** de a
    resposta sair — senão um segundo cliente no mesmo instante criaria um segundo job.
    """
    r = pedido()
    assert r.status == 202
    assert r.job_id and r.poll_url and r.sse_url
    assert r.job_id in r.poll_url and r.job_id in r.sse_url
    assert len(fila.enfileirados) == 1

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert gravado is not None and gravado.status == "processando"


def test_processamento_em_voo_nao_cria_segundo_job(pedido, repo, fila, lock):
    """Scenario: processamento já em voo.

    `202` **sem** `job_id`: não há job novo a acompanhar, e devolver o `job_id` alheio faria o
    cliente acreditar que o job é dele.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="processando", resultado=None))
    lock.adquirir(ENTE, EXERCICIO, ANEXO, "job-em-voo")

    r = pedido()
    assert r.status == 202
    assert r.job_id is None
    assert fila.enfileirados == []


def test_apuracao_que_falhou_reprocessa_e_substitui_o_erro(pedido, repo, fila):
    """Scenario: apuração falhou.

    `erro` é estado terminal do job anterior, não do anexo: a próxima leitura tenta de novo. O
    detalhe antigo é **substituído**, nunca acumulado — histórico de erro em coluna vira log.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="erro",
                             erro_detalhe="timeout na fonte", resultado=None))
    r = pedido()
    assert r.status == 202
    assert r.job_id
    assert len(fila.enfileirados) == 1

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert gravado.status == "processando"
    assert "timeout na fonte" not in (gravado.erro_detalhe or "")


def test_falha_ao_criar_job_e_erro_explicito(pedido, fila, repo):
    """Requisito: falha na criação do job devolve erro explícito.

    A fila fora do ar não pode virar `202` mentiroso: o cliente ficaria esperando um job que
    ninguém vai executar.
    """
    fila.falhar = True
    # `RuntimeError`, não `Exception`: `ModuleNotFoundError` também é `Exception`, e o teste
    # ficaria verde por acidente de import enquanto a F2 não existe.
    with pytest.raises(RuntimeError) as erro:
        pedido()
    assert "fila" in str(erro.value).lower()

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert gravado is None or gravado.status != "processando", (
        "registro não pode ficar preso em processando se o job não foi enfileirado"
    )


def test_rota_nunca_devolve_resultado_parcial(pedido, repo):
    """Requisito: a rota NÃO DEVE devolver resultado parcial.

    Registro `processando` costuma ter `resultado` da apuração anterior ainda gravado; servi-lo
    seria devolver dado velho como se fosse o novo.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="processando",
                             resultado={"matriz": {"L1": {"a": "1.00"}}}))
    r = pedido()
    assert r.status == 202
    assert r.resultado is None


def test_versao_de_regras_divergente_nao_serve(pedido, repo, fila):
    """Scenario: regra alterada invalida o cache."""
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok",
                             resultado={"matriz": {}}, versao_regras=OUTRA_VERSAO_REGRAS))
    r = pedido()
    assert r.status == 202
    assert r.resultado is None
    assert len(fila.enfileirados) == 1
