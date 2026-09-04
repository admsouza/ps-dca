"""Cenários de integridade de fontes, domínio STN e índice de regras.

Requisitos cobertos: códigos conferidos contra as tabelas oficiais, integridade e
imutabilidade do documento de origem, e índice para localização direta.
"""
from __future__ import annotations

import hashlib
import shutil

import pytest
import yaml

from tests.conftest import CONTAS_STN, RAIZ_REPO, mensagens, regra

# ─── Códigos conferidos contra as tabelas oficiais da STN ────────────────────

def test_codigo_valido_e_aceito(base, validar):
    """Scenario: código válido — `6.2.1.2.0.00.00` existe no PCASP."""
    rel = validar(base())
    assert not [e for e in rel.erros if "6.2.1.2" in (e.mensagem or "")]


def test_codigo_inexistente_leva_a_review_required(base, validar):
    """Requisito: código ausente da tabela leva a regra a `review_required`."""
    filtros = [{"field": "conta_contabil", "operator": "in", "values": [
        {"literal": "9.9.9.9.9.99.99", "pattern": "999999999"}]}]
    rel = validar(base(quadro_principal=[regra(filters=filtros, status="extracted")]))
    assert rel.exit_code == 1
    assert "review_required" in mensagens(rel)


def test_naturezas_intraorcamentarias_sao_excecao_declarada(base, validar):
    """Scenario: naturezas intraorçamentárias ausentes da tabela (categorias 7 e 8).

    Exceção de domínio B2: não vira `review_required`, e o relatório a distingue de
    código inexistente.
    """
    filtros = [{"field": "natureza_receita", "operator": "in", "values": [
        {"literal": "7100.00.00", "pattern": "71"}]}]
    rel = validar(base(quadro_principal=[regra(filters=filtros)]))
    assert rel.exit_code == 0
    assert "71" in str(rel.contagens["excecoes_dominio"])
    assert rel.contagens["por_status"]["review_required"] == 0


def test_naturezas_de_despesa_fora_do_grupo_31_sao_excecao_declarada(base, validar):
    """Scenario: naturezas de despesa fora do grupo 3.1 — exceção de domínio B4."""
    filtros = [{"field": "natureza_despesa", "operator": "in", "values": [
        {"literal": "4.4.00.00.00", "pattern": "44"}]}]
    rel = validar(base(quadro_principal=[regra(filters=filtros)]))
    assert rel.exit_code == 0
    assert rel.contagens["por_status"]["review_required"] == 0


def test_relatorio_distingue_excecao_de_codigo_inexistente(base, validar):
    """Scenario: exceção declarada e código inexistente não se confundem no relatório."""
    intra = {"field": "natureza_receita", "operator": "in",
             "values": [{"literal": "7100.00.00", "pattern": "71"}]}
    inexistente = {"field": "conta_contabil", "operator": "in",
                   "values": [{"literal": "9.9.9.9.9.99.99", "pattern": "999999999"}]}
    rel = validar(base(quadro_principal=[regra(filters=[intra, inexistente])]))
    assert rel.contagens["excecoes_dominio"]
    assert rel.exit_code == 1


@pytest.mark.parametrize("dominio,tabela,esperado", [
    ("conta_contabil", "PCASP.md", 6119),
    ("natureza_receita", "natureza-receita.md", 4504),
    ("natureza_despesa", "natureza_despesa.md", 172),
    ("subfuncao", "funcao-subfuncao.md", 117),
])
def test_tabelas_stn_carregam_os_volumes_medidos(carregar_tabelas_stn, dominio, tabela, esperado):
    """Requisito: os conjuntos de códigos válidos vêm das tabelas oficiais, sem invenção.

    Volumes medidos nas tabelas do repositório em 2026-09-04. Divergir aqui significa que a
    tabela mudou — e nesse caso o hash de `sources/stn/metadata.yaml` também acusa.
    """
    assert (CONTAS_STN / tabela).is_file(), f"tabela ausente: {tabela}"
    conjuntos = carregar_tabelas_stn(CONTAS_STN)
    assert len(conjuntos[dominio]) == esperado


def test_tabela_da_stn_alterada_e_detectada(base, verificar_fontes, tmp_path):
    """Scenario: tabela da STN alterada — reporta tabela, hash esperado e obtido."""
    raiz = base()
    copia = tmp_path / "contas-stn"
    shutil.copytree(CONTAS_STN, copia)
    alvo = copia / "PCASP.md"
    conteudo = alvo.read_text(encoding="utf-8")
    esperado = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    meta = raiz / "sources" / "stn" / "metadata.yaml"
    with meta.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(
            {"tables": [{"file": str(alvo), "sha256": esperado}]},
            fh, allow_unicode=True, sort_keys=False,
        )
    alvo.write_text(conteudo + "\nlinha adulterada\n", encoding="utf-8")

    rel = verificar_fontes(raiz)
    assert rel.exit_code == 1
    texto = mensagens(rel)
    assert "PCASP.md" in texto and esperado[:12] in texto


# ─── Integridade e imutabilidade do documento de origem ──────────────────────

def test_hash_do_pdf_confere(base, verificar_fontes):
    """Scenario: hash confere — exit 0."""
    raiz = base()
    pdf = RAIZ_REPO / "docs" / "referencia" / "ipc" / "IPC07 - BO atualizacoes - 20200117.pdf"
    assert pdf.is_file(), "PDF do IPC07 ausente do repositório"
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()

    meta = raiz / "sources" / "ipc07" / "metadata.yaml"
    dados = yaml.safe_load(meta.read_text(encoding="utf-8"))
    dados.update({"sha256": digest, "path": str(pdf)})
    with meta.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(dados, fh, allow_unicode=True, sort_keys=False)

    rel = verificar_fontes(raiz)
    assert rel.exit_code == 0


def test_pdf_substituido_por_outra_edicao_e_detectado(base, verificar_fontes):
    """Scenario: PDF substituído por outra edição — nomeia documento, esperado e obtido."""
    raiz = base()  # metadata nasce com sha256 = 000...0, que não confere
    pdf = RAIZ_REPO / "docs" / "referencia" / "ipc" / "IPC07 - BO atualizacoes - 20200117.pdf"
    meta = raiz / "sources" / "ipc07" / "metadata.yaml"
    dados = yaml.safe_load(meta.read_text(encoding="utf-8"))
    dados["path"] = str(pdf)
    with meta.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(dados, fh, allow_unicode=True, sort_keys=False)

    rel = verificar_fontes(raiz)
    assert rel.exit_code == 1
    texto = mensagens(rel)
    assert "IPC07" in texto and "0" * 12 in texto


def test_pdf_nao_e_duplicado_dentro_de_knowledge():
    """Requisito: o PDF não é alterado nem duplicado dentro de `knowledge/`."""
    knowledge = RAIZ_REPO / "knowledge"
    encontrados = list(knowledge.rglob("*.pdf")) if knowledge.is_dir() else []
    assert encontrados == []


# ─── Índice de regras ────────────────────────────────────────────────────────

def test_localizar_regra_pelo_indice(base, construir_indice):
    """Scenario: localizar regra pelo índice."""
    indice = construir_indice(base())
    entrada = indice["bo.quadro_principal.receitas.l2"]
    assert entrada["demonstrativo"] == "BO"
    assert entrada["quadro"] == "QUADRO_PRINCIPAL"
    assert entrada["document"] == "IPC07"
    assert entrada["page"] == 8
    assert entrada["file"].endswith("quadro_principal.yaml")


def test_indice_e_deterministico(base, construir_indice):
    """Requisito: o índice é gerado a partir dos YAMLs, nunca editado à mão."""
    raiz = base()
    assert construir_indice(raiz) == construir_indice(raiz)


def test_indice_desatualizado_e_detectado(base, validar, construir_indice):
    """Scenario: índice desatualizado é detectado."""
    raiz = base(quadro_principal=[
        regra(rule_id="bo.quadro_principal.receitas.l2"),
        regra(rule_id="bo.quadro_principal.receitas.l3"),
    ])
    indice = construir_indice(raiz)
    indice.pop("bo.quadro_principal.receitas.l3")
    destino = raiz / "indexes" / "rules_index.json"
    destino.write_text(__import__("json").dumps(indice, ensure_ascii=False, indent=2),
                       encoding="utf-8", newline="\n")

    rel = validar(raiz)
    assert rel.exit_code == 1
    assert "l3" in mensagens(rel)
