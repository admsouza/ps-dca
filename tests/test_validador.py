"""Cenários estruturais do delta spec `dca/base-canonica-regras` — validador.

Um teste por `#### Scenario:` do delta spec, com o nome do cenário no docstring.
Cobre os requisitos: rastreabilidade, identificador, filtros, referências, override,
bloqueio documental, versionamento, proveniência e contagens.
"""
from __future__ import annotations

import pytest

from tests.conftest import mensagens, regra, regra_composta

# ─── Rastreabilidade obrigatória até a origem documental ─────────────────────

def test_regra_com_origem_completa_e_aceita(base, validar):
    """Scenario: regra com origem completa é aceita."""
    rel = validar(base())
    assert rel.erros == []
    assert rel.exit_code == 0


def test_regra_sem_source_e_rejeitada(base, validar):
    """Scenario: regra sem source é rejeitada."""
    rel = validar(base(quadro_principal=[regra(source=None)]))
    assert rel.exit_code == 1
    texto = mensagens(rel)
    assert "bo.quadro_principal.receitas.l2" in texto
    assert "quadro_principal.yaml" in texto


@pytest.mark.parametrize("pagina", [40, 0, -1])
def test_pagina_fora_do_documento_e_rejeitada(base, validar, pagina):
    """Scenario: página fora do documento é rejeitada (IPC07 tem 17 páginas)."""
    fonte = dict(regra()["source"], page=pagina)
    rel = validar(base(quadro_principal=[regra(source=fonte)], paginas_ipc07=17))
    assert rel.exit_code == 1
    assert "page" in mensagens(rel) or "página" in mensagens(rel).lower()


def test_pagina_ausente_ou_nula_e_rejeitada(base, validar):
    """Scenario: página fora do documento é rejeitada — ausente e nula."""
    for valor in (None, "ausente"):
        fonte = dict(regra()["source"])
        if valor == "ausente":
            fonte.pop("page")
        else:
            fonte["page"] = None
        rel = validar(base(quadro_principal=[regra(source=fonte)]))
        assert rel.exit_code == 1


# ─── Identificador legível e estável ─────────────────────────────────────────

def test_identificador_de_linha_de_receita(base, validar):
    """Scenario: identificador de linha de receita."""
    rel = validar(base())
    assert rel.exit_code == 0
    assert "bo.quadro_principal.receitas.l2" in rel.contagens["rule_ids"]


def test_linhas_homonimas_em_quadros_diferentes(base, validar):
    """Scenario: linhas homônimas em quadros diferentes."""
    rel = validar(
        base(
            quadro_principal=[regra()],
            rp_nao_processados=[regra(rule_id="bo.rp_nao_processados.l1")],
            rp_processados=[regra(rule_id="bo.rp_processados.l1")],
        )
    )
    ids = rel.contagens["rule_ids"]
    assert "bo.rp_nao_processados.l1" in ids and "bo.rp_processados.l1" in ids
    assert len(set(ids)) == len(ids)


def test_identificador_duplicado_e_rejeitado(base, validar):
    """Scenario: identificador duplicado é rejeitado — erro nomeia os dois arquivos."""
    rel = validar(
        base(quadro_principal=[regra()], rp_processados=[regra()])
    )
    assert rel.exit_code == 1
    texto = mensagens(rel)
    assert "quadro_principal.yaml" in texto and "rp_processados.yaml" in texto


# ─── Filtros com campos e operadores de conjunto fechado ─────────────────────

def test_operador_invalido_e_rejeitado(base, validar):
    """Scenario: operador inválido é rejeitado."""
    filtros = [{"field": "natureza_receita", "operator": "starts_with", "values": [
        {"literal": "1100.00.00", "pattern": "11"}]}]
    rel = validar(base(quadro_principal=[regra(filters=filtros)]))
    assert rel.exit_code == 1
    assert "starts_with" in mensagens(rel)


def test_campo_de_filtro_invalido_e_rejeitado(base, validar):
    """Scenario: campo de filtro inválido é rejeitado — `fonte_recurso` não existe no IPC07."""
    filtros = [{"field": "fonte_recurso", "operator": "in", "values": [
        {"literal": "1500", "pattern": "1500"}]}]
    rel = validar(base(quadro_principal=[regra(filters=filtros)]))
    assert rel.exit_code == 1
    assert "fonte_recurso" in mensagens(rel)


@pytest.mark.parametrize("campo,literal,padrao", [
    ("conta_contabil", "6.2.1.2.0.00.00", "6212"),
    ("natureza_receita", "1100.00.00", "11"),
    ("natureza_despesa", "3.1.00.00.00", "31"),
    ("funcao", "28", "28"),
    ("subfuncao", "841", "841"),
])
def test_campos_do_conjunto_fechado_sao_aceitos(base, validar, campo, literal, padrao):
    """Scenario: campo de filtro inválido é rejeitado — o complemento, os cinco válidos.

    Cada campo com um código que existe de fato na sua tabela: o que está sob teste é a
    aceitação do campo, não a do código.
    """
    filtros = [{"field": campo, "operator": "in",
                "values": [{"literal": literal, "pattern": padrao}]}]
    rel = validar(base(quadro_principal=[regra(filters=filtros)]))
    assert rel.erros == []


def test_valor_sem_pattern_exige_review_required(base, validar):
    """Requisito: `pattern: null` obriga a regra a ficar `review_required`."""
    filtros = [{"field": "natureza_receita", "operator": "in", "values": [
        {"literal": "1100.00.00", "pattern": None}]}]
    rel = validar(base(quadro_principal=[regra(filters=filtros, status="extracted")]))
    assert rel.exit_code == 1
    assert "review_required" in mensagens(rel)


# ─── Cálculo por referência a outras regras ──────────────────────────────────

def test_soma_de_linhas_nao_declara_contas_proprias(base, validar):
    """Scenario: soma de linhas — L1 = L2..L9, sem contas nem filtros próprios."""
    filhas = [regra(rule_id=f"bo.quadro_principal.receitas.l{n}") for n in range(2, 10)]
    l1 = regra_composta(
        "bo.quadro_principal.receitas.l1",
        [(f"bo.quadro_principal.receitas.l{n}", "+") for n in range(2, 10)],
    )
    rel = validar(base(quadro_principal=[l1, *filhas]))
    assert rel.exit_code == 0
    assert "columns" not in l1 and "filters" not in l1


def test_referencia_entre_grupos_e_aceita_sem_ciclo(base, validar):
    """Scenario: referência do bloco de receitas para o de despesas — L25 = L48 - L24."""
    l24 = regra(rule_id="bo.quadro_principal.receitas.l24")
    l48 = regra(rule_id="bo.quadro_principal.despesas.l48")
    l25 = regra_composta(
        "bo.quadro_principal.receitas.l25",
        [("bo.quadro_principal.despesas.l48", "+"), ("bo.quadro_principal.receitas.l24", "-")],
    )
    rel = validar(base(quadro_principal=[l24, l48, l25]))
    assert rel.exit_code == 0
    assert "ciclo" not in mensagens(rel).lower()


def test_referencia_inexistente_e_rejeitada(base, validar):
    """Scenario: referência inexistente é rejeitada — nomeia órfão, origem e arquivo:linha."""
    orfa = regra_composta(
        "bo.quadro_principal.receitas.l1", [("bo.quadro_principal.receitas.l99", "+")]
    )
    rel = validar(base(quadro_principal=[orfa]))
    assert rel.exit_code == 1
    texto = mensagens(rel)
    assert "bo.quadro_principal.receitas.l99" in texto
    assert "bo.quadro_principal.receitas.l1" in texto
    assert "quadro_principal.yaml" in texto


def test_ciclo_de_dependencia_e_rejeitado(base, validar):
    """Scenario: ciclo de dependência é rejeitado — erro imprime o caminho completo."""
    ida = [("bo.quadro_principal.receitas.l2", "+")]
    volta = [("bo.quadro_principal.receitas.l1", "+")]
    a = regra_composta("bo.quadro_principal.receitas.l1", ida)
    b = regra_composta("bo.quadro_principal.receitas.l2", volta)
    rel = validar(base(quadro_principal=[a, b]))
    assert rel.exit_code == 1
    texto = mensagens(rel)
    assert "bo.quadro_principal.receitas.l1" in texto and "bo.quadro_principal.receitas.l2" in texto


# ─── Guarda condicional ──────────────────────────────────────────────────────

@pytest.mark.parametrize("condicao", ["result_positive", "result_negative"])
def test_condicao_do_conjunto_fechado_e_aceita(base, validar, condicao):
    """Requisito: `calculation.condition.when` só aceita os dois valores do IPC07."""
    outra = regra(rule_id="bo.quadro_principal.despesas.l48")
    r = regra_composta(
        "bo.quadro_principal.receitas.l25", [("bo.quadro_principal.despesas.l48", "+")]
    )
    r["calculation"]["condition"] = {"when": condicao}
    rel = validar(base(quadro_principal=[r, outra]))
    assert rel.exit_code == 0


def test_condicao_fora_do_conjunto_e_rejeitada(base, validar):
    """Requisito: condição legível por máquina, não texto livre."""
    outra = regra(rule_id="bo.quadro_principal.despesas.l48")
    r = regra_composta(
        "bo.quadro_principal.receitas.l25", [("bo.quadro_principal.despesas.l48", "+")]
    )
    r["calculation"]["condition"] = {"when": "somente quando o resultado for deficitário"}
    rel = validar(base(quadro_principal=[r, outra]))
    assert rel.exit_code == 1


# ─── Override de conta restrito a L29 e L30 ──────────────────────────────────

@pytest.mark.parametrize("rule_id", [
    "bo.quadro_principal.receitas.l29", "bo.quadro_principal.receitas.l30",
])
def test_override_permitido_em_l29_e_l30(base, validar, rule_id):
    """Scenario: conta da linha substitui contas das colunas em L29 e L30."""
    rel = validar(base(quadro_principal=[regra(rule_id=rule_id, line_account_override=True)]))
    assert rel.exit_code == 0


@pytest.mark.parametrize("rule_id", [
    "bo.quadro_principal.receitas.l28", "bo.quadro_principal.despesas.l32",
])
def test_override_fora_de_l29_e_l30_e_rejeitado(base, validar, rule_id):
    """Scenario: override de conta fora de L29 e L30 é rejeitado."""
    rel = validar(base(quadro_principal=[regra(rule_id=rule_id, line_account_override=True)]))
    assert rel.exit_code == 1
    texto = mensagens(rel)
    assert rule_id in texto
    assert "l29" in texto and "l30" in texto


# ─── Bloqueio documental é declarado, nunca interpretado ─────────────────────

def test_regra_sob_revisao_marcada_como_validada_e_inconsistente(base, validar):
    """Scenario: regra sob revisão marcada como validada."""
    rel = validar(base(quadro_principal=[
        regra(status="validated", review={"required": True})
    ]))
    assert rel.exit_code == 1


def test_blocker_documental_remanescente_e_reportado(base, validar):
    """Scenario: nenhum bloqueio documental permanece no IPC07."""
    r = regra(status="review_required", review={"required": True, "blocker": "B7"})
    rel = validar(base(quadro_principal=[r]))
    assert rel.exit_code == 1
    assert "blocker" in mensagens(rel).lower()


def test_candidato_de_revisao_nao_e_aplicado(base, validar):
    """Requisito: `review.candidate` não pode aparecer em `filters` nem em `columns`."""
    r = regra(
        status="review_required",
        review={"required": True, "reason": "x", "candidate": {"field": "natureza_receita",
                                                               "values": ["9999.99.99"]}},
    )
    rel = validar(base(quadro_principal=[r]))
    aplicado = "9999.99.99" in str(r.get("filters")) or "9999.99.99" in str(r.get("columns"))
    assert not aplicado
    assert rel.exit_code == 0


# ─── Versionamento e proveniência ────────────────────────────────────────────

def test_fim_de_vigencia_nao_declarado(base, validar):
    """Scenario: fim de vigência não declarado — `valid_until` é null."""
    rel = validar(base())
    assert rel.exit_code == 0
    assert all(v is None for v in rel.contagens["valid_until"])


def test_valid_until_preenchido_e_rejeitado(base, validar):
    """Scenario: fim de vigência não declarado — data inferida não é aceita."""
    versao = dict(regra()["version"], valid_until="2025-12-31")
    rel = validar(base(quadro_principal=[regra(version=versao)]))
    assert rel.exit_code == 1


@pytest.mark.parametrize("metodo", ["automated", "assisted"])
def test_extracao_automatica_nao_nasce_validada(base, validar, metodo):
    """Scenario: extração automática não é validada."""
    proveniencia = dict(regra()["provenance"], extraction_method=metodo)
    rel = validar(base(quadro_principal=[
        regra(provenance=proveniencia, status="validated", review={"required": False})
    ]))
    assert rel.exit_code == 1


def test_revisor_ausente_e_aceito(base, validar):
    """Scenario: revisor ausente — validação não exige revisor."""
    rel = validar(base(quadro_principal=[regra(review={"required": True})]))
    assert rel.exit_code == 0
    assert "revisor" not in mensagens(rel).lower()


# ─── Contagens ───────────────────────────────────────────────────────────────

def test_contagem_por_quadro_soma_o_total(base, validar):
    """Scenario: contagem por quadro — o relatório informa por quadro e o total."""
    rel = validar(
        base(
            quadro_principal=[
                regra(rule_id=f"bo.quadro_principal.receitas.l{n}") for n in range(1, 4)
            ],
            rp_nao_processados=[regra(rule_id="bo.rp_nao_processados.l1")],
            rp_processados=[regra(rule_id="bo.rp_processados.l1")],
        )
    )
    por_quadro = rel.contagens["por_quadro"]
    assert por_quadro == {"quadro_principal": 3, "rp_nao_processados": 1, "rp_processados": 1}
    assert rel.contagens["total"] == 5


def test_contagem_por_status(base, validar):
    """Scenario: contagem por status."""
    rel = validar(base(quadro_principal=[
        regra(rule_id="bo.quadro_principal.receitas.l2"),
        regra(rule_id="bo.quadro_principal.receitas.l3"),
    ]))
    assert rel.contagens["por_status"]["extracted"] == 2
    assert rel.contagens["por_status"]["review_required"] == 0
