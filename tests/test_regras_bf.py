"""Cenários normativos do IPC 06 — o conteúdo real das 80 regras do Balanço Financeiro.

Parte A assere sobre a base transcrita em `knowledge/rules/bf/`; parte B exercita o validador
com regras sintéticas do BF. Cada teste cita a página do IPC 06 de onde a regra vem.
"""
from __future__ import annotations

import functools

import pytest
import yaml

from tests.conftest import KNOWLEDGE, mensagens, regra, regra_bf

QUADROS = ("quadro_principal", "quadro_anexo")

COLUNAS_PRINCIPAL = {"exercicio_atual", "exercicio_anterior"}
COLUNAS_ANEXO = {
    "receita_orcamentaria_atual", "deducoes_atual", "saldo_atual",
    "receita_orcamentaria_anterior", "deducoes_anterior", "saldo_anterior",
}

# Item 39, pp. 10–13: subgrupo → faixa de fonte do Anexo I da Portaria STN 710/2021.
FONTES_POR_LINHA = {
    "ingressos.l2": ["500", "501", "502", "503"],
    "ingressos.l4": ["540", "541", "542", "543", "544", "545", "546", "550", "551", "552",
                     "553", "569", "570", "571", "572", "573", "574", "575", "576", "599"],
    "ingressos.l7": ["803", "804"],
    "ingressos.l12": ["800"],
    "ingressos.l13": ["801"],
    "ingressos.l14": ["802"],
    "dispendios.l35": ["500", "501", "502", "503"],
    "dispendios.l40": ["803", "804"],
    "dispendios.l45": ["800"],
    "dispendios.l46": ["801"],
    "dispendios.l47": ["802"],
}

BLOQUEADAS = (
    "bf.quadro_principal.ingressos.l22",
    "bf.quadro_principal.ingressos.l23",
    "bf.quadro_principal.ingressos.l28",
    "bf.quadro_principal.dispendios.l55",
    "bf.quadro_principal.dispendios.l56",
    "bf.quadro_principal.dispendios.l61",
)


@functools.lru_cache(maxsize=1)
def _base() -> dict[str, dict]:
    diretorio = KNOWLEDGE / "rules" / "bf"
    assert diretorio.is_dir(), f"base canônica do BF ausente: {diretorio}"
    regras: dict[str, dict] = {}
    for quadro in QUADROS:
        arquivo = diretorio / f"{quadro}.yaml"
        assert arquivo.is_file(), f"quadro ausente: {arquivo}"
        dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
        for r in dados.get("rules", []):
            regras[r["rule_id"]] = r
    return regras


def rule(rule_id: str) -> dict:
    base = _base()
    assert rule_id in base, f"regra ausente na base: {rule_id}"
    return base[rule_id]


def contas(regra_: dict, coluna: str) -> list[str]:
    return [c["pattern"] for c in regra_["columns"][coluna]["accounts"]]


def sinais(regra_: dict, coluna: str) -> dict[str, str]:
    return {c["pattern"]: c["sign"] for c in regra_["columns"][coluna]["accounts"]}


def fontes(regra_: dict) -> list[str]:
    achados = [f for f in regra_.get("filters", []) if f["field"] == "fonte_recurso"]
    assert achados, f"{regra_['rule_id']} não filtra por fonte_recurso"
    return [v["pattern"] for v in achados[0]["values"]]


def referencias(regra_: dict) -> list[tuple[str, str]]:
    return [(r["rule"], r["sign"]) for r in regra_["calculation"]["references"]]


# ═══ A. Base transcrita ══════════════════════════════════════════════════════

# ─── Cobertura completa dos dois quadros do IPC 06 ───────────────────────────

def test_contagem_por_quadro():
    """Scenario: contagem por quadro."""
    base = _base()
    principal = [r for r in base if r.startswith("bf.quadro_principal.")]
    anexo = [r for r in base if r.startswith("bf.quadro_anexo.")]
    assert (len(principal), len(anexo)) == (66, 14)
    assert len(base) == 80


def test_os_dois_blocos_do_quadro_principal_sao_distinguidos():
    """Scenario: os dois blocos do Quadro Principal são distinguidos."""
    for numero in range(1, 34):
        assert rule(f"bf.quadro_principal.ingressos.l{numero}")["grupo"]["codigo"] == "INGRESSOS"
    for numero in range(34, 67):
        assert rule(f"bf.quadro_principal.dispendios.l{numero}")["grupo"]["codigo"] == "DISPENDIOS"
    for rule_id, r in _base().items():
        if rule_id.startswith("bf.quadro_anexo."):
            assert "grupo" not in r


def test_estrutura_de_publicacao_nao_gera_regra():
    """Scenario: estrutura de publicação não gera regra."""
    for r in _base().values():
        assert r["source"]["page"] <= 15, r["rule_id"]
        assert r["source"]["section"] == "REGRAS DE PREENCHIMENTO DO BALANÇO FINANCEIRO"


# ─── Identificador do Balanço Financeiro ─────────────────────────────────────

def test_identificador_de_linha_de_ingresso():
    """Scenario: identificador de linha de ingresso."""
    r = rule("bf.quadro_principal.ingressos.l2")
    assert r["linha"]["descricao"] == "Recursos Não Vinculados"


def test_linha_do_quadro_anexo_nao_colide():
    """Scenario: linha do Quadro Anexo não colide com a do Quadro Principal."""
    assert rule("bf.quadro_anexo.l1")["quadro"]["codigo"] == "QUADRO_ANEXO"
    assert rule("bf.quadro_principal.ingressos.l1")["quadro"]["codigo"] == "QUADRO_PRINCIPAL"
    assert "bo.quadro_principal.receitas.l1" not in _base()


# ─── Colunas de valor do Balanço Financeiro ──────────────────────────────────

def test_linha_de_ingresso_com_duas_colunas():
    """Scenario: linha de ingresso com duas colunas (IPC 06 p. 10, L2)."""
    r = rule("bf.quadro_principal.ingressos.l2")
    assert set(r["columns"]) == COLUNAS_PRINCIPAL
    for coluna in COLUNAS_PRINCIPAL:
        assert sinais(r, coluna) == {"6212": "+", "6213": "-"}


def test_saldo_do_quadro_anexo_e_calculado():
    """Scenario: saldo do Quadro Anexo é calculado, não somado de contas."""
    r = rule("bf.quadro_anexo.l1")
    assert set(r["columns"]) == COLUNAS_ANEXO
    assert r["columns"]["saldo_atual"]["calculation"]["references"] == [
        {"column": "receita_orcamentaria_atual", "sign": "+"},
        {"column": "deducoes_atual", "sign": "-"},
    ]
    assert "accounts" not in r["columns"]["saldo_atual"]
    assert r["columns"]["saldo_anterior"]["calculation"]["references"] == [
        {"column": "receita_orcamentaria_anterior", "sign": "+"},
        {"column": "deducoes_anterior", "sign": "-"},
    ]


def test_nenhuma_regra_do_bf_declara_coluna_fora_do_quadro():
    """Requisito: colunas de valor do BF — nenhuma regra declara coluna fora do seu quadro."""
    for rule_id, r in _base().items():
        colunas = set(r.get("columns") or {})
        if not colunas:
            continue
        esperadas = COLUNAS_ANEXO if rule_id.startswith("bf.quadro_anexo.") else COLUNAS_PRINCIPAL
        assert colunas <= esperadas, rule_id


# ─── Filtro por fonte ou destinação de recursos ──────────────────────────────

@pytest.mark.parametrize("sufixo,esperadas", FONTES_POR_LINHA.items())
def test_fonte_por_subgrupo(sufixo, esperadas):
    """Scenario: linhas de mesmo mapeamento contábil separadas por fonte."""
    assert fontes(rule(f"bf.quadro_principal.{sufixo}")) == esperadas


def test_linhas_de_receita_compartilham_o_par_de_contas():
    """Scenario: linhas de mesmo mapeamento contábil separadas por fonte (contas)."""
    ids = [2, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14]
    vistos = set()
    for numero in ids:
        r = rule(f"bf.quadro_principal.ingressos.l{numero}")
        assert sinais(r, "exercicio_atual") == {"6212": "+", "6213": "-"}
        chave = tuple(fontes(r))
        assert chave not in vistos, f"L{numero} repete o conjunto de fontes"
        vistos.add(chave)
        assert r["status"] == "extracted"


def test_rpps_separado_em_tres_linhas_por_fonte_unica():
    """Scenario: RPPS separado em três linhas por fonte única."""
    assert referencias(rule("bf.quadro_principal.ingressos.l11")) == [
        ("bf.quadro_principal.ingressos.l12", "+"),
        ("bf.quadro_principal.ingressos.l13", "+"),
        ("bf.quadro_principal.ingressos.l14", "+"),
    ]
    assert "filters" not in rule("bf.quadro_principal.ingressos.l11")


def test_previdencia_exceto_rpps_exclui_as_fontes_do_rpps():
    """Scenario: previdência exceto RPPS exclui as três fontes do RPPS."""
    for sufixo in ("ingressos.l7", "dispendios.l40"):
        assert fontes(rule(f"bf.quadro_principal.{sufixo}")) == ["803", "804"]


def test_prefixo_de_exercicio_nao_entra_no_valor_da_fonte():
    """Scenario: prefixo de exercício não entra no valor da fonte."""
    for r in _base().values():
        for filtro in r.get("filters") or []:
            if filtro["field"] != "fonte_recurso":
                continue
            for valor in filtro["values"]:
                assert len(valor["pattern"]) == 3, (r["rule_id"], valor)
                assert 500 <= int(valor["pattern"]) <= 999, (r["rule_id"], valor)


def test_linha_sem_fonte_nao_declara_o_filtro():
    """Scenario: linha sem fonte não declara o filtro (IPC 06 p. 11, L16)."""
    r = rule("bf.quadro_principal.ingressos.l16")
    assert contas(r, "exercicio_atual") == ["4511"]
    assert not [f for f in r.get("filters") or [] if f["field"] == "fonte_recurso"]


# ─── Saldo de conta patrimonial ──────────────────────────────────────────────

def test_caixa_exceto_rpps_no_saldo_inicial():
    """Scenario: caixa e equivalentes exceto RPPS, no saldo inicial (p. 11, L30)."""
    r = rule("bf.quadro_principal.ingressos.l30")
    assert sinais(r, "exercicio_atual") == {"111": "+", "1111106": "-", "1113": "-"}
    for coluna in COLUNAS_PRINCIPAL:
        assert {c["saldo"] for c in r["columns"][coluna]["accounts"]} == {"inicial"}


def test_linha_homologa_dos_dispendios_usa_o_saldo_final():
    """Scenario: a linha homóloga dos dispêndios usa o saldo final (p. 13, L63)."""
    r = rule("bf.quadro_principal.dispendios.l63")
    assert sinais(r, "exercicio_atual") == {"111": "+", "1111106": "-", "1113": "-"}
    for coluna in COLUNAS_PRINCIPAL:
        assert {c["saldo"] for c in r["columns"][coluna]["accounts"]} == {"final"}


def test_todas_as_linhas_de_saldo_declaram_o_momento():
    """Requisito: conta patrimonial apurada por saldo em data — L30-L32 e L63-L65."""
    inicial = [f"bf.quadro_principal.ingressos.l{n}" for n in (30, 31, 32)]
    final = [f"bf.quadro_principal.dispendios.l{n}" for n in (63, 64, 65)]
    for rule_id, momento in [(r, "inicial") for r in inicial] + [(r, "final") for r in final]:
        r = rule(rule_id)
        for coluna in COLUNAS_PRINCIPAL:
            assert {c["saldo"] for c in r["columns"][coluna]["accounts"]} == {momento}


def test_linha_de_execucao_nao_declara_saldo():
    """Requisito: conta patrimonial apurada por saldo em data — nenhuma outra linha declara."""
    for rule_id, r in _base().items():
        if rule_id in {f"bf.quadro_principal.ingressos.l{n}" for n in (30, 31, 32)}:
            continue
        if rule_id in {f"bf.quadro_principal.dispendios.l{n}" for n in (63, 64, 65)}:
            continue
        for coluna in (r.get("columns") or {}).values():
            for conta in coluna.get("accounts") or []:
                assert "saldo" not in conta, rule_id


# ─── Movimento nas linhas de depósitos restituíveis ──────────────────────────

def test_as_duas_linhas_se_distinguem_pelo_movimento():
    """Scenario: as duas linhas se distinguem pelo movimento (pp. 11 e 13)."""
    ingresso = rule("bf.quadro_principal.ingressos.l27")
    dispendio = rule("bf.quadro_principal.dispendios.l60")
    for r, movimento in ((ingresso, "credor"), (dispendio, "devedor")):
        for coluna in COLUNAS_PRINCIPAL:
            assert sinais(r, coluna) == {"2188": "+", "2288": "+"}
            assert r["columns"][coluna]["movimento"] == movimento
        assert fontes(r) == ["860", "861", "862", "863", "869"]


# ─── Mapeamento não determinado pelo IPC 06 ──────────────────────────────────

def test_conta_de_controle_sem_decisao():
    """Scenario: conta de controle sem decisão (p. 11, L22)."""
    r = rule("bf.quadro_principal.ingressos.l22")
    assert r["status"] == "review_required"
    assert "32" in r["review"]["blocker"] and "9" in r["review"]["blocker"]
    for coluna in r["columns"].values():
        assert not coluna.get("accounts")
    assert r["review"]["candidate"]
    assert "conta de controle" in r["evidence"]["text"]


def test_exatamente_seis_linhas_bloqueadas():
    """Requisito: mapeamento não determinado é declarado — F1 e F2, 6 linhas e nenhuma outra."""
    bloqueadas = {rid for rid, r in _base().items() if r["status"] == "review_required"}
    assert bloqueadas == set(BLOQUEADAS)
    for rule_id in BLOQUEADAS:
        r = rule(rule_id)
        assert r["review"]["required"] is True
        assert r["review"]["blocker"]
        assert "provenance" in r and "decision" not in r["provenance"]


# ─── Equilíbrio estrutural ───────────────────────────────────────────────────

def test_totais_so_agregam_linhas():
    """Scenario: totais só agregam linhas."""
    esperado = {
        "bf.quadro_principal.ingressos.l33": [1, 15, 21, 24, 29],
        "bf.quadro_principal.dispendios.l66": [34, 48, 54, 57, 62],
    }
    for rule_id, numeros in esperado.items():
        r = rule(rule_id)
        grupo = "ingressos" if "ingressos" in rule_id else "dispendios"
        assert referencias(r) == [
            (f"bf.quadro_principal.{grupo}.l{n}", "+") for n in numeros
        ]
        assert "columns" not in r


def test_l33_e_linha_de_ingresso_apesar_da_posicao_no_pdf():
    """Scenario: L33 é linha de ingresso, apesar da posição no PDF."""
    r = rule("bf.quadro_principal.ingressos.l33")
    assert r["grupo"]["codigo"] == "INGRESSOS"
    assert r["linha"]["ordem"] == 33
    assert r["source"]["page"] == 12
    assert "p. 12" in r["evidence"]["text"]


def test_total_do_quadro_anexo_fecha_nas_seis_colunas():
    """Requisito: equilíbrio estrutural — TOTAL do Quadro Anexo agrega L1, L2 e L10."""
    r = rule("bf.quadro_anexo.l14")
    assert referencias(r) == [
        ("bf.quadro_anexo.l1", "+"),
        ("bf.quadro_anexo.l2", "+"),
        ("bf.quadro_anexo.l10", "+"),
    ]


# ─── Policies e versionamento ────────────────────────────────────────────────

def test_policies_do_ipc06():
    """Scenario: exclusão de intraorçamentárias vale para as linhas de execução."""
    dados = yaml.safe_load(
        (KNOWLEDGE / "policies" / "ipc06.yaml").read_text(encoding="utf-8")
    )
    ids = {p["policy_id"] for p in dados["policies"]}
    assert ids == {
        "ipc06.receita_liquida_de_deducoes",
        "ipc06.regime_de_caixa_classes_3_e_4",
        "ipc06.apenas_valor_principal_investido",
        "ipc06.aberturas_de_saldo_nao_exaustivas",
        "ipc06.exclusao_de_intraorcamentarias",
    }
    for policy in dados["policies"]:
        assert policy["source"]["page"] >= 1
        assert policy["evidence"]["text"]

    intra = "ipc06.exclusao_de_intraorcamentarias"
    execucao = [f"bf.quadro_principal.ingressos.l{n}" for n in range(2, 15)]
    execucao += [f"bf.quadro_principal.dispendios.l{n}" for n in range(35, 48)]
    for rule_id in execucao:
        assert intra in rule(rule_id).get("policies", []), rule_id


def test_fim_de_vigencia_nao_declarado():
    """Scenario: fim de vigência não declarado."""
    for r in _base().values():
        assert r["version"] == {
            "source_document": "IPC06",
            "edition": "2024-06",
            "valid_from": "2024-06-30",
            "valid_until": None,
        }


# ═══ B. Validador ════════════════════════════════════════════════════════════

def test_campo_do_bo_e_rejeitado_no_bf(base, validar):
    """Scenario: campo do BO é rejeitado no BF."""
    ruim = regra_bf(filters=[{
        "field": "natureza_despesa", "operator": "in",
        "values": [{"literal": "3.1.00.00.00", "pattern": "31"}],
    }])
    rel = validar(base(bf_quadro_principal=[ruim]))
    assert rel.exit_code == 1
    assert "IPC06" in mensagens(rel) and "natureza_despesa" in mensagens(rel)


def test_campo_do_bf_e_rejeitado_no_bo(base, validar):
    """Scenario: campo do BF é rejeitado no BO."""
    ruim = regra(filters=[{
        "field": "fonte_recurso", "operator": "in",
        "values": [{"literal": "500", "pattern": "500"}],
    }])
    rel = validar(base(quadro_principal=[ruim]))
    assert rel.exit_code == 1
    assert "IPC07" in mensagens(rel) and "fonte_recurso" in mensagens(rel)


def test_coluna_inexistente_e_rejeitada(base, validar):
    """Scenario: coluna inexistente é rejeitada."""
    colunas = dict(regra_bf()["columns"])
    colunas["previsao_inicial"] = colunas.pop("exercicio_atual")
    rel = validar(base(bf_quadro_principal=[regra_bf(columns=colunas)]))
    assert rel.exit_code == 1
    assert "previsao_inicial" in mensagens(rel)


def test_fonte_da_uniao_e_rejeitada(base, validar):
    """Scenario: fonte da União é rejeitada."""
    ruim = regra_bf(filters=[{
        "field": "fonte_recurso", "operator": "in",
        "values": [{"literal": "100", "pattern": "100"}],
    }])
    rel = validar(base(bf_quadro_principal=[ruim]))
    assert rel.exit_code == 1
    assert "500" in mensagens(rel)


def test_saldo_omitido_em_conta_patrimonial_e_rejeitado(base, validar):
    """Scenario: saldo omitido em conta patrimonial é rejeitado."""
    ruim = regra_bf(
        rule_id="bf.quadro_principal.ingressos.l31",
        linha={"codigo": "L31", "descricao": "Caixa e Equivalentes de Caixa RPPS",
               "nivel": 2, "ordem": 31},
        filters=None,
        columns={
            nome: {"label": nome,
                   "accounts": [{"literal": "1.1.1.1.1.06.00", "pattern": "1111106",
                                 "sign": "+"}]}
            for nome in COLUNAS_PRINCIPAL
        },
    )
    rel = validar(base(bf_quadro_principal=[ruim]))
    assert rel.exit_code == 1
    assert "saldo" in mensagens(rel)


def test_saldo_declarado_em_linha_de_execucao_e_rejeitado(base, validar):
    """Scenario: saldo declarado em linha de execução é rejeitado."""
    ruim = regra_bf(
        rule_id="bf.quadro_principal.ingressos.l25",
        linha={"codigo": "L25", "descricao": "Inscrição de Restos a Pagar Não Processados",
               "nivel": 2, "ordem": 25},
        filters=None,
        columns={
            nome: {"label": nome,
                   "accounts": [{"literal": "5.3.1.7.0.00.00", "pattern": "5317",
                                 "sign": "+", "saldo": "inicial"}]}
            for nome in COLUNAS_PRINCIPAL
        },
    )
    rel = validar(base(bf_quadro_principal=[ruim]))
    assert rel.exit_code == 1
    assert "saldo" in mensagens(rel)


def test_total_com_conta_propria_e_rejeitado(base, validar):
    """Scenario: total com conta própria é rejeitado."""
    ruim = regra_bf(
        rule_id="bf.quadro_principal.dispendios.l66",
        grupo={"codigo": "DISPENDIOS", "descricao": "Dispêndios"},
        linha={"codigo": "L66", "descricao": "TOTAL (XII) = (VII+VIII+IX+X+XI)",
               "nivel": 1, "ordem": 66},
        filters=None,
        columns={
            nome: {"label": nome,
                   "accounts": [{"literal": "1.1.1.0.0.00.00", "pattern": "1110", "sign": "+"}]}
            for nome in COLUNAS_PRINCIPAL
        },
    )
    rel = validar(base(bf_quadro_principal=[ruim]))
    assert rel.exit_code == 1
    assert "total" in mensagens(rel).lower()


def test_bloqueio_documental_do_ipc06_nao_e_erro(base, validar):
    """Requisito: mapeamento não determinado é declarado — blocker do BF não é erro (F1/F2)."""
    bloqueada = regra_bf(
        rule_id="bf.quadro_principal.ingressos.l22",
        linha={"codigo": "L22", "descricao": "Resgates de Investimentos e Aplicações Financeiras",
               "nivel": 2, "ordem": 22},
        filters=None,
        columns={nome: {"label": nome} for nome in COLUNAS_PRINCIPAL},
        status="review_required",
        review={"required": True, "blocker": "IPC 06 item 32, p. 9: <conta de controle>",
                "candidate": {"classes": ["7", "8"]}},
    )
    rel = validar(base(bf_quadro_principal=[bloqueada]))
    assert rel.exit_code == 0, mensagens(rel)


def test_indice_cobre_o_bf(base, construir_indice):
    """Scenario: localizar regra pelo índice — agora também no BF."""
    raiz = base(bf_quadro_principal=[regra_bf()])
    indice = construir_indice(raiz)
    assert indice["bf.quadro_principal.ingressos.l2"] == {
        "file": "rules/bf/quadro_principal.yaml",
        "demonstrativo": "BF",
        "quadro": "QUADRO_PRINCIPAL",
        "document": "IPC06",
        "page": 10,
    }


def test_linhas_homonimas_em_demonstrativos_diferentes(base, validar, construir_indice):
    """Scenario: linhas homônimas em demonstrativos diferentes."""
    raiz = base(
        quadro_principal=[regra(rule_id="bo.quadro_principal.receitas.l1", calculation=None)],
        bf_quadro_principal=[regra_bf(rule_id="bf.quadro_principal.ingressos.l1")],
    )
    indice = construir_indice(raiz)
    assert set(indice) == {
        "bo.quadro_principal.receitas.l1", "bf.quadro_principal.ingressos.l1"
    }
    assert validar(raiz).exit_code == 0


def test_decisao_do_po_fecha_o_bloqueio(base, validar):
    """Scenario: decisão do PO fecha o bloqueio."""
    decidida = regra_bf(
        rule_id="bf.quadro_principal.ingressos.l22",
        linha={"codigo": "L22", "descricao": "Resgates de Investimentos e Aplicações Financeiras",
               "nivel": 2, "ordem": 22},
        filters=None,
        columns={
            nome: {"label": nome,
                   "accounts": [{"literal": "7.1.1.0.0.00.00", "pattern": "711", "sign": "+"}]}
            for nome in COLUNAS_PRINCIPAL
        },
        provenance={"extraction_method": "assisted", "extracted_at": "2026-09-14",
                    "decision": "F3"},
        status="extracted",
        review={"required": True},
        evidence={"page": 11, "text": "L22 Resgates ... <conta de controle>"},
    )
    rel = validar(base(bf_quadro_principal=[decidida]))
    assert rel.exit_code == 0, mensagens(rel)


def test_policy_sem_origem_e_rejeitada(base, validar):
    """Scenario: policy sem origem é rejeitada."""
    policy = {
        "policy_id": "ipc06.exclusao_de_intraorcamentarias",
        "descricao": "Exclui as transferências intraorçamentárias já acompanhadas de execução.",
        "aplica_a": {"demonstrativo": "BF"},
        "evidence": {"page": 10, "text": "devem excluir as transferências financeiras"},
        "status": "extracted",
    }
    rel = validar(base(policies=[policy]))
    assert rel.exit_code == 1
    assert "source" in mensagens(rel)


def test_dois_documentos_integros(verificar_fontes):
    """Scenario: dois documentos íntegros."""
    rel = verificar_fontes(KNOWLEDGE)
    assert rel.exit_code == 0, mensagens(rel)
    assert rel.contagens["documentos"] == 2


def test_anexo_i_substituido_por_edicao_posterior(base, verificar_fontes, tmp_path):
    """Scenario: Anexo I substituído por edição posterior."""
    import yaml as _yaml

    raiz = base()
    copia = tmp_path / "fontes-recursos-stn-2026.xlsx"
    copia.write_bytes(b"conteudo de outra edicao")
    meta = raiz / "sources" / "stn" / "metadata.yaml"
    with meta.open("w", encoding="utf-8", newline="\n") as fh:
        _yaml.safe_dump({"tables": [{"file": str(copia), "sha256": "a" * 64}]}, fh)

    rel = verificar_fontes(raiz)
    assert rel.exit_code == 1
    assert "fontes-recursos-stn-2026.xlsx" in mensagens(rel)
