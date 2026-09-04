"""Identidade do resultado, invalidação por versão, e o cache único para todos os anexos.

`versao_regras` é o que a DCA tem e os irmãos não: a regra vive em `knowledge/rules/**.yaml`, e
uma correção de conta sem bump de código **tem** de invalidar o cache. Se a invalidação dependesse
só de `versao_api`, o ente receberia número velho depois de a regra ser corrigida.
"""
from __future__ import annotations

import pytest

from tests.pipeline.conftest import (
    ANEXO,
    ENTE,
    EXERCICIO,
    OUTRA_VERSAO_REGRAS,
    VERSAO_API,
    VERSAO_REGRAS,
    RegistroFake,
)


def test_alteracao_real_de_regra_invalida(pedido, repo, fila):
    """Scenario: alteração real de regra invalida."""
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok", resultado={"m": 1}))
    assert pedido(versao_regras=VERSAO_REGRAS).status == 200
    assert pedido(versao_regras=OUTRA_VERSAO_REGRAS).status == 202


def test_versao_de_api_divergente_invalida(pedido, repo):
    """Scenario: versão da API alterada invalida o cache."""
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok",
                             resultado={"m": 1}, versao_api="0.0.1"))
    assert pedido(versao_api=VERSAO_API).status == 202


def test_regra_de_outro_anexo_nao_invalida(pedido, repo, fila):
    """Scenario: regra de outro anexo não invalida.

    `versao_regras` é por anexo. Um hash global faria a correção de uma linha do BO reapurar os
    sete anexos da DCA de todos os entes.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, "BO", status="ok", resultado={"bo": 1}))
    repo.gravar(RegistroFake(ENTE, EXERCICIO, "I-C", status="ok", resultado={"ic": 1},
                             versao_regras=OUTRA_VERSAO_REGRAS))

    assert pedido(anexo="BO", versao_regras=VERSAO_REGRAS).status == 200
    assert fila.enfileirados == []


def test_entes_e_exercicios_nao_colidem(pedido, repo):
    """Scenario: entes e exercícios não colidem."""
    repo.gravar(RegistroFake("2507507", 2025, ANEXO, resultado={"quem": "jp-2025"}))
    repo.gravar(RegistroFake("2507507", 2024, ANEXO, resultado={"quem": "jp-2024"}))
    repo.gravar(RegistroFake("3550308", 2025, ANEXO, resultado={"quem": "sp-2025"}))

    assert pedido(ente="2507507", exercicio=2025).resultado == {"quem": "jp-2025"}
    assert pedido(ente="2507507", exercicio=2024).resultado == {"quem": "jp-2024"}
    assert pedido(ente="3550308", exercicio=2025).resultado == {"quem": "sp-2025"}


def test_identificador_de_regra_e_estavel_a_formatacao(carregar_mapa_de):
    """Scenario: identificador de regra é estável a formatação.

    Reescrever os YAMLs com CRLF, outra indentação e outra ordem de chaves **não** pode mudar
    `versao_regras`: o hash é do conteúdo parseado, nunca dos bytes. Sem isso, um `git checkout`
    num Windows invalidaria o cache de todos os entes.
    """
    original = carregar_mapa_de(reescrever=None).versao_regras
    # As duas direções: o repositório é conferido em CRLF, então `lf` é a variante que um
    # checkout em Linux produz, e `crlf` a que um `core.autocrlf=true` produz.
    assert carregar_mapa_de(reescrever="lf").versao_regras == original
    assert carregar_mapa_de(reescrever="crlf").versao_regras == original
    assert carregar_mapa_de(reescrever="indentacao").versao_regras == original
    assert carregar_mapa_de(reescrever="ordem").versao_regras == original


def test_alteracao_de_conta_muda_o_identificador(carregar_mapa_de):
    """Scenario: alteração real de regra invalida — o lado positivo do hash canônico."""
    original = carregar_mapa_de(reescrever=None).versao_regras
    assert carregar_mapa_de(reescrever="conta").versao_regras != original


# ─── Um único mecanismo de cache para todos os anexos ────────────────────────

def test_anexo_novo_nao_cria_estrutura(pedido, repo):
    """Scenario: anexo novo não cria estrutura de cache.

    Um anexo que ainda não existia grava e lê pelo mesmo repositório, na mesma tabela, sem
    migration nova. É a decisão P-D1 — uma tabela com coluna `anexo`, não sete models idênticos.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, "I-HI", status="ok", resultado={"novo": 1}))
    r = pedido(anexo="I-HI")
    assert r.status == 200 and r.resultado == {"novo": 1}


def test_status_permitido_e_recusa_o_resto():
    """Scenario: status permitido.

    Contra a **persistência real**, não contra o fake: um teste que afirma a validação do próprio
    dublê passa antes de existir implementação, e não testa nada.
    """
    from app.infra.cache.modelo import STATUS_CACHE, StatusInvalido, validar_status

    assert set(STATUS_CACHE) == {"ok", "processando", "erro"}
    for permitido in STATUS_CACHE:
        assert validar_status(permitido) == permitido
    for recusado in ("concluido", "OK", "", "pendente", None):
        with pytest.raises(StatusInvalido):
            validar_status(recusado)


# ─── Anexo é um conjunto fechado ─────────────────────────────────────────────

def test_anexo_desconhecido_e_rejeitado_na_entrada(pedido):
    """Scenario: anexo desconhecido é rejeitado na entrada."""
    from app.services.pipeline.registry import AnexoDesconhecido

    with pytest.raises(AnexoDesconhecido) as erro:
        pedido(anexo="I-ZZ")
    assert "I-ZZ" in str(erro.value)


@pytest.mark.parametrize("grafia", ["bo", "Bo", " BO ", "i-c", "I_C"])
def test_grafia_divergente_nao_fragmenta_o_cache(pedido, repo, grafia):
    """Scenario: grafia divergente não fragmenta o cache.

    `bo` e `BO` são o mesmo anexo. Sem normalizar na entrada, cada grafia criaria a sua própria
    linha de cache e o mesmo ente seria reapurado a cada variação.
    """
    esperado = "BO" if grafia.strip().upper().replace("_", "-") == "BO" else "I-C"
    repo.gravar(RegistroFake(ENTE, EXERCICIO, esperado, status="ok", resultado={"x": 1}))
    assert pedido(anexo=grafia).status == 200


def test_persistencia_recusa_anexo_invalido(repo):
    """Scenario: persistência recusa anexo inválido.

    A recusa vale também na gravação, não só na entrada: o worker grava sem passar pela rota.
    """
    from app.services.pipeline.registry import AnexoDesconhecido, validar_anexo

    with pytest.raises(AnexoDesconhecido):
        validar_anexo("I-ZZ")
    assert validar_anexo("bo") == "BO", "a validação também normaliza"
