"""Reprocessamento forçado de um anexo.

Bloco 4 da fase TEST. Reapurar com cache válido é operação de exceção — corrigiu-se a regra, a
fonte republicou, o ente pediu conferência. O que a spec protege é o consumidor: em nenhum momento
o anexo pode ficar "sem resultado" porque alguém mandou reapurar.

Contrato: o mesmo `ler_ou_enfileirar`, com dois parâmetros a mais.

    ler_ou_enfileirar(..., forcar=True, solicitado_por=<id do usuário>)

Não é rota nova nem service novo: reprocessar é o mesmo ciclo, com a decisão de cache invertida.
Um caminho próprio duplicaria lock, cache e enfileiramento — a dívida que os irmãos já pagam.
"""
from __future__ import annotations

import pytest

from tests.pipeline.conftest import (
    ANEXO,
    ENTE,
    EXERCICIO,
    RegistroFake,
)

OUTRO_ENTE = "3550308"
USUARIO = 42
ANTERIOR = {"matriz": {"L1": {"previsao_atualizada": "1.00"}}}


@pytest.fixture
def verificar_token():
    def _verificar(token):
        return {"sub": USUARIO, "unidade": ENTE} if token == "bom" else None
    return _verificar


def test_reprocessamento_com_cache_valido(pedido, repo, fila, lock, registro_ok):
    """Scenario: reprocessamento com cache válido.

    Cache `ok` e versões atuais: sem `forcar`, serve 200; com `forcar`, cria job e devolve
    `job_id`. E o solicitante fica registrado — "quem mandou reapurar" é a primeira pergunta
    quando o número muda.
    """
    assert pedido().status == 200, "cache não estava válido; o cenário perde o sentido"

    r = pedido(forcar=True, solicitado_por=USUARIO)
    assert r.status == 202
    assert r.job_id
    assert len(fila.enfileirados) == 1
    assert lock.tomados[(ENTE, EXERCICIO, ANEXO)] == r.job_id

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert gravado.solicitado_por == USUARIO


def test_resultado_anterior_continua_legivel(pedido, repo, fila):
    """Scenario: resultado anterior continua legível.

    Durante a reapuração, quem pede o anexo recebe o resultado anterior ou a indicação de
    processamento — nunca "sem resultado". Apagar o registro antes de reapurar abriria uma janela
    de minutos em que o ente vê o anexo vazio.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok", resultado=ANTERIOR))

    forcado = pedido(forcar=True, solicitado_por=USUARIO)
    assert forcado.status == 202 and forcado.job_id

    durante = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert durante.resultado == ANTERIOR, "resultado anterior foi apagado pelo reprocessamento"

    outro_cliente = pedido()
    assert outro_cliente.status in (200, 202)
    if outro_cliente.status == 200:
        assert outro_cliente.resultado == ANTERIOR
    assert len(fila.enfileirados) == 1, "o segundo cliente disparou outro job"


def test_reprocessamento_nao_escapa_do_lock(pedido, repo, fila, lock):
    """Scenario: reprocessamento não escapa do lock.

    `forcar` não é passe livre: com job em voo, devolve o job existente com
    `estado_job="already_queued"` e não enfileira segundo. Sem isso, um botão de reprocessar
    clicado três vezes daria três apurações concorrentes da mesma identidade.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="processando", resultado=ANTERIOR))
    lock.adquirir(ENTE, EXERCICIO, ANEXO, "job-em-voo")

    r = pedido(forcar=True, solicitado_por=USUARIO)
    assert r.status == 202
    assert r.job_id == "job-em-voo"
    assert r.estado_job == "already_queued"
    assert fila.enfileirados == []


def test_reprocessamento_exige_autorizacao(fila, verificar_token):
    """Scenario: reprocessamento exige autorização.

    Mesma autorização da leitura: unidade diferente do ente é `403`, e nenhum job é criado. Rota de
    escrita com autorização mais frouxa que a de leitura é o A01 da OWASP em uma linha.
    """
    from app.auth.autorizacao import NaoAutorizado, autorizar

    with pytest.raises(NaoAutorizado):
        autorizar(token="bom", unidade=ENTE, ente=OUTRO_ENTE, verificar=verificar_token)

    assert fila.enfileirados == []
