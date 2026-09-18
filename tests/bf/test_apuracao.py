"""Apuração do Balanço Financeiro — o que a medição de 2026-09-18 provou.

Cada teste cita a evidência que o originou (`docs/evidencia-bf-medicao-2026-09-18.md`). Os
saldos são sintéticos: o que está sob teste é o motor, não a rede.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bf.conftest import ENTE, EXERCICIO, fonte_com
from tests.bo.conftest import saldo

# ─── carregador por demonstrativo ────────────────────────────────────────────

def test_carrega_as_66_linhas_do_quadro_principal(mapa_bf):
    """Requisito: O carregador deixa de ser fixo em `rules/bo` (task 2.5).

    A base do BF traz os dois quadros: 66 linhas no principal e 14 no anexo.
    """
    principal = [linha for linha in mapa_bf.linhas if linha.quadro == "QUADRO_PRINCIPAL"]
    assert len(principal) == 66
    assert len(mapa_bf.linhas) == 80
    assert mapa_bf.vigencia.documento == "IPC06"
    assert mapa_bf.vigencia.edicao == "2024-06"


def test_bo_continua_carregando_sem_o_parametro(carregar_mapa):
    """Requisito: Regressão: o BO chama `carregar(exercicio)` e não pode quebrar."""
    assert len(carregar_mapa(exercicio=EXERCICIO).linhas) == 69


# ─── G1: fonte de recursos ───────────────────────────────────────────────────

def test_fonte_de_recursos_descarta_o_digito_de_exercicio():
    """Requisito: A MSC traz 4 dígitos, o 1º é o exercício da vinculação; a regra do IPC declara 3.

    Medido: `"1500"` casa a fonte `500`. Sem descartar o 1º dígito nenhuma linha casaria, e as
    22 linhas por fonte sairiam **zeradas sem erro**.
    """
    from app.domain.bo.modelo import Filtro
    from app.domain.bo.saldo import atende
    from tests.bo.conftest import registro

    r = registro("621200000", "C", "100.00", fonte_recursos="1500")
    assert atende(r, [Filtro("fonte_recurso", "in", ("500",))])
    assert not atende(r, [Filtro("fonte_recurso", "in", ("501",))])


def test_fonte_casa_por_igualdade_e_nao_por_prefixo():
    """Requisito: a fonte casa por igualdade dos 3 dígitos, não por prefixo.

    `"1500"` não pode casar um padrão `50`, que pegaria também 501, 502 e 503 — cada uma de uma
    linha diferente do demonstrativo.
    """
    from app.domain.bo.modelo import Filtro
    from app.domain.bo.saldo import atende
    from tests.bo.conftest import registro

    r = registro("621200000", "C", "100.00", fonte_recursos="1500")
    assert not atende(r, [Filtro("fonte_recurso", "in", ("50",))])


def test_registro_sem_fonte_nao_entra_em_nenhuma_linha_por_fonte():
    """Requisito: Medido em Recife: 450.202.814,72 na conta sintética `6.2.1.2.0.00.00` sem fonte.

    Não pode ser rateado nem virar zero silencioso — fica de fora e é declarado como resíduo.
    """
    from app.domain.bo.modelo import Filtro
    from app.domain.bo.saldo import atende
    from tests.bo.conftest import registro

    r = registro("621200000", "C", "450202814.72", fonte_recursos="")
    assert not atende(r, [Filtro("fonte_recurso", "in", ("500", "501", "502", "503"))])


# ─── G7: direção do saldo por conta ──────────────────────────────────────────

def test_direcao_por_conta_usa_a_natureza_de_cada_conta():
    """Requisito: No BF a direção é a da própria conta, não a da coluna (G7, confirmado em 3 entes).

    `6.2.1.2` é credora e `6.2.1.3` é devedora; a regra já traz `(+)` e `(−)`. Com a direção da
    coluna, `L1` de Recife sai 5.872.854.713,27 em vez do publicado.
    """
    from app.domain.bo.modelo import ContaCC
    from app.domain.bo.saldo import saldo_da_celula_por_conta
    from app.infra.pcasp.natureza import do_pcasp

    registros = [saldo("621200000", "1000.00"), saldo("621310100", "150.00")]
    valor, pendencias = saldo_da_celula_por_conta(
        registros, (ContaCC("6212", "+"), ContaCC("6213", "-")), do_pcasp())
    assert pendencias == []
    assert valor == Decimal("850.00")


def test_conta_sem_direcao_no_pcasp_nao_vira_zero():
    """Requisito: Célula inteira não apurada — `None`, nunca `0` (regra já vigente do BO)."""
    from app.domain.bo.modelo import ContaCC
    from app.domain.bo.saldo import saldo_da_celula_por_conta
    from tests.bo.conftest import DirecaoFake, registro

    registros = [registro("999999999", "C", "10.00")]
    valor, pendencias = saldo_da_celula_por_conta(
        registros, (ContaCC("999", "+"),), DirecaoFake())
    assert valor is None
    assert pendencias


# ─── N1: a origem do saldo é por linha ───────────────────────────────────────

def test_inscricao_de_restos_a_pagar_vem_do_encerramento(apurar_bf):
    """Scenario: inscrição de restos a pagar vem do encerramento

    As contas `5.3.1.7` e `5.3.2.7` **não existem** no saldo de abertura.

    Medido em Recife: no encerramento valem 74.205.408,29 e 106.062.740,96, iguais ao publicado
    e ao RREO. Ler tudo da abertura devolveria zero sem erro nenhum.
    """
    fonte = fonte_com(
        a2025={5: [], 6: []},
        e2025={5: [saldo("531700000", "74205408.29"), saldo("532700000", "106062740.96")]},
        a2024={},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    por_codigo = {linha.codigo: linha.id for linha in resultado.mapa.linhas}
    assert resultado.matriz[por_codigo["L25"]]["exercicio_atual"] == Decimal("74205408.29")
    assert resultado.matriz[por_codigo["L26"]]["exercicio_atual"] == Decimal("106062740.96")


def test_saldo_do_exercicio_anterior_le_o_ano_anterior(apurar_bf):
    """Requisito: `L29`–`L32` são o exercício anterior, não outro tipo de saldo (G2).

    Medido em Recife: `1.1.1` de 2024 = 802.570.332,31 e `1.1.3.5.1` = 717.721,98 somam
    803.288.054,29, o publicado. A abertura de 2025 traz a posição **final**, que é `L62`.
    """
    fonte = fonte_com(
        a2025={1: [saldo("111110100", "1308763064.41")]},
        e2025={},
        a2024={1: [saldo("111110100", "802570332.31")]},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    por_codigo = {linha.codigo: linha.id for linha in resultado.mapa.linhas}
    assert resultado.matriz[por_codigo["L30"]]["exercicio_atual"] == Decimal("802570332.31")
    assert resultado.matriz[por_codigo["L63"]]["exercicio_atual"] == Decimal("1308763064.41")


def test_procedencia_declara_a_origem_de_cada_linha(apurar_bf):
    """Requisito: Sem isso, duas apurações incomparáveis passam por iguais."""
    resultado = apurar_bf(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={}))
    p = resultado.procedencia
    assert p.documento == "IPC06"
    assert "encerramento" in p.matriz.lower()
    assert "encerramento" in p.origens_por_linha["L25"].lower().split("/")[1]
    assert "L29" in p.origens_por_linha and "anterior" in p.origens_por_linha["L29"]


# ─── G5/G8: linhas sem mapeamento de contas ──────────────────────────────────

SEM_MAPEAMENTO = ("L22", "L23", "L28", "L55", "L56", "L61")


@pytest.mark.parametrize("codigo", SEM_MAPEAMENTO)
def test_linha_sem_conta_no_ipc_nao_e_apurada(apurar_bf, codigo):
    """Scenario: linha sem conta sai não apurada

    G8-(b): o valor que os entes publicam nessas linhas **não existe na MSC**.

    Busca reversa em 7 combinações de matriz e tipo de saldo, todos os prefixos de conta, como
    saldo, crédito e débito — nada. Célula `None` com motivo, nunca zero.
    """
    resultado = apurar_bf(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={}))
    por_codigo = {linha.codigo: linha.id for linha in resultado.mapa.linhas}
    rule_id = por_codigo[codigo]
    assert resultado.matriz[rule_id]["exercicio_atual"] is None
    assert any(n.rule_id == rule_id for n in resultado.diagnostico.nao_apuradas)


def test_linha_sem_mapeamento_contribui_como_parcela_inexistente(apurar_bf):
    """Scenario: o total soma as parcelas que existem

    G5-(a): `L21` = `L22` + `L23`, ambas não apuráveis, sai **0,00** e não `None`.

    Com a opção (b) o BF inteiro ficaria em branco por causa de 6 linhas, mesmo com 42 corretas.
    """
    fonte = fonte_com(a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500")]},
                      e2025={}, a2024={})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    por_codigo = {linha.codigo: linha.id for linha in resultado.mapa.linhas}
    assert resultado.matriz[por_codigo["L21"]]["exercicio_atual"] == Decimal("0.00")
    assert resultado.matriz[por_codigo["L33"]]["exercicio_atual"] is not None


# ─── coluna do exercício anterior: duas origens ──────────────────────────────

def test_coluna_anterior_vem_da_msce_do_exercicio_anterior(apurar_bf):
    """Scenario: coluna anterior apurada da MSCE do exercício anterior

    Cobre `as duas colunas saem da mesma regra`: as duas colunas da linha declaram as mesmas
    contas e os mesmos filtros; muda o exercício de onde os saldos vêm.
    """
    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500")]},
        a2024={6: [saldo("621200000", "800.00", fonte_recursos="1500")]},
        e2025={}, e2024={}, a2023={},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    por_codigo = {linha.codigo: linha.id for linha in resultado.mapa.linhas}
    celulas = resultado.matriz[por_codigo["L2"]]
    assert celulas["exercicio_atual"] == Decimal("1000.00")
    assert celulas["exercicio_anterior"] == Decimal("800.00")


def test_coluna_anterior_manual_usa_o_informado(apurar_bf):
    """Scenario: coluna anterior preenchida manualmente"""
    from app.services.bf.quadro_principal import Anterior

    fonte = fonte_com(a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500")]},
                      e2025={}, a2024={})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte, anterior=Anterior.MANUAL,
                          valores_anteriores={"L2": Decimal("777.00")})
    por_codigo = {linha.codigo: linha.id for linha in resultado.mapa.linhas}
    assert resultado.matriz[por_codigo["L2"]]["exercicio_anterior"] == Decimal("777.00")
    assert resultado.procedencia.origem_exercicio_anterior == "manual"


def test_coluna_anterior_manual_sem_a_linha_nao_vira_zero(apurar_bf):
    """Requisito: valor não informado é `None` + motivo, nunca zero.

    Zero seria uma afirmação que o usuário não fez.
    """
    from app.services.bf.quadro_principal import Anterior

    fonte = fonte_com(a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500")]},
                      e2025={}, a2024={})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte, anterior=Anterior.MANUAL,
                          valores_anteriores={"L2": Decimal("777.00")})
    por_codigo = {linha.codigo: linha.id for linha in resultado.mapa.linhas}
    assert resultado.matriz[por_codigo["L4"]]["exercicio_anterior"] is None


def test_coluna_anterior_manual_recusa_linha_fora_do_ipc(apurar_bf):
    """Scenario: linha informada fora do IPC 06"""
    from app.services.bf.quadro_principal import Anterior, LinhaDesconhecida

    fonte = fonte_com(a2025={}, e2025={}, a2024={})
    with pytest.raises(LinhaDesconhecida, match="L99"):
        apurar_bf(ENTE, EXERCICIO, fonte, anterior=Anterior.MANUAL,
                  valores_anteriores={"L99": Decimal("1.00")})


# ─── identidades do IPC 06, que valem sem depender de ente ───────────────────

def test_identidades_do_demonstrativo_fecham_sobre_o_apurado(apurar_bf):
    """Requisito: `L1 = L2 + L3 + L11` e `L33 = L1 + L15 + L21 + L24 + L29`.

    Conferem em 24 de 24, nos 5 entes de homologação. É a garantia de fidelidade ao IPC 06 que
    não depende do que o ente publicou.
    """
    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500"),
                   saldo("621200000", "300.00", fonte_recursos="1540")]},
        e2025={}, a2024={},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    m = {linha.codigo: resultado.matriz[linha.id].get("exercicio_atual")
         for linha in resultado.mapa.linhas}
    assert m["L1"] == (m["L2"] or 0) + (m["L3"] or 0) + (m["L11"] or 0)
    assert m["L3"] == sum(m[c] or 0 for c in ("L4", "L5", "L6", "L7", "L8", "L9", "L10"))
    assert m["L33"] == sum(m[c] or 0 for c in ("L1", "L15", "L21", "L24", "L29"))


# ─── item 38: declarado e não aplicado (G11-a) ───────────────────────────────

def test_item_38_nao_e_aplicado_e_o_diagnostico_declara(apurar_bf):
    """Scenario: o item 38 não altera o valor apurado

    Medido: aplicar por categoria 7/8 e modalidade 91 quebra `L1` e `L34` em BH e JP.

    A policy fica declarada e não executada, com o motivo no diagnóstico.
    """
    fonte = fonte_com(
        a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500"),
                   saldo("621200000", "100.00", fonte_recursos="1500",
                         natureza_receita="72110101")]},
        e2025={}, a2024={},
    )
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    por_codigo = {linha.codigo: linha.id for linha in resultado.mapa.linhas}
    assert resultado.matriz[por_codigo["L2"]]["exercicio_atual"] == Decimal("1100.00")
    assert any("item 38" in p for p in resultado.diagnostico.policies_nao_aplicadas)
