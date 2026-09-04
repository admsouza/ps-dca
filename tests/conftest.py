"""Fixtures da base canônica (task 2.2 da change `ipc07-bo-regras-canonicas`).

Contrato exercitado pelos testes — ainda não implementado:

    scripts/validate_rules.py   validar(base: Path) -> Relatorio
    scripts/check_sources.py    verificar(base: Path) -> Relatorio
    scripts/build_index.py      construir(base: Path) -> dict
    scripts/load_stn_tables.py  carregar(raiz_docs: Path) -> dict[str, set[str]]

`base` é o diretório `knowledge/`: `rules/`, `policies/`, `sources/`, `schemas/`, `indexes/`.

`Relatorio` expõe `erros: list[Erro]`, `exit_code: int` e `contagens: dict`.
`Erro` expõe `rule_id`, `mensagem`, `arquivo`, `linha`.

Os imports são feitos dentro de fixture de propósito: enquanto o código não existe, o
`ImportError` aparece como falha do teste, não como erro de coleta que impede rodar a suíte.
"""
from __future__ import annotations

import copy
import itertools
import shutil
from pathlib import Path

import pytest
import yaml

RAIZ_REPO = Path(__file__).resolve().parent.parent
KNOWLEDGE = RAIZ_REPO / "knowledge"
CONTAS_STN = RAIZ_REPO / "docs" / "contas-stn"


# ─── funções sob teste, importadas tarde ─────────────────────────────────────

@pytest.fixture
def validar():
    from scripts.validate_rules import validar as f
    return f


@pytest.fixture
def verificar_fontes():
    from scripts.check_sources import verificar as f
    return f


@pytest.fixture
def construir_indice():
    from scripts.build_index import construir as f
    return f


@pytest.fixture
def carregar_tabelas_stn():
    from scripts.load_stn_tables import carregar as f
    return f


# ─── regra mínima válida, e mutações a partir dela ───────────────────────────

REGRA_VALIDA: dict = {
    "rule_id": "bo.quadro_principal.receitas.l2",
    "demonstrativo": {"codigo": "BO", "descricao": "Balanço Orçamentário"},
    "quadro": {"codigo": "QUADRO_PRINCIPAL", "descricao": "Quadro Principal"},
    "grupo": {"codigo": "RECEITAS", "descricao": "Receitas Orçamentárias"},
    "linha": {
        "codigo": "L2",
        "descricao": "Impostos, Taxas e Contribuições de Melhoria",
        "nivel": 2,
        "ordem": 2,
    },
    "filters": [
        {
            "field": "natureza_receita",
            "operator": "in",
            "values": [
                {"literal": "1100.00.00", "pattern": "11"},
                {"literal": "7100.00.00", "pattern": "71"},
            ],
        }
    ],
    "columns": {
        "previsao_inicial": {
            "label": "Previsão Inicial (a)",
            "accounts": [{"literal": "5.2.1.1.0.00.00", "pattern": "5211", "sign": "+"}],
        },
        "previsao_atualizada": {
            "label": "Previsão Atualizada (b)",
            "accounts": [
                {"literal": "5.2.1.1.0.00.00", "pattern": "5211", "sign": "+"},
                {"literal": "5.2.1.2.0.00.00", "pattern": "5212", "sign": "+"},
            ],
        },
        "receitas_realizadas": {
            "label": "Receitas Realizadas (c)",
            "accounts": [
                {"literal": "6.2.1.2.0.00.00", "pattern": "6212", "sign": "+"},
                {"literal": "6.2.1.3.0.00.00", "pattern": "6213", "sign": "+"},
            ],
        },
        "saldo": {
            "label": "SALDO (d) = (c-b)",
            "calculation": {
                "references": [
                    {"column": "receitas_realizadas", "sign": "+"},
                    {"column": "previsao_atualizada", "sign": "-"},
                ]
            },
        },
    },
    "source": {
        "document": "IPC07",
        "document_version": "2020-01",
        "page": 8,
        "section": "REGRAS DE PREENCHIMENTO DO BALANÇO ORÇAMENTÁRIO",
        "item": "23",
        "table": "Quadro Principal",
        "row": "L2",
    },
    "evidence": {
        "page": 8,
        "text": "L2 | Impostos, Taxas e Contribuições de Melhoria | 1100.00.00; 7100.00.00",
    },
    "version": {
        "source_document": "IPC07",
        "edition": "2020-01",
        "valid_from": "2020-01-20",
        "valid_until": None,
    },
    "provenance": {
        "extraction_method": "assisted",
        "extractor_version": "1.0",
        "extracted_at": "2026-08-27",
    },
    "status": "extracted",
    "review": {"required": True},
}


def regra(**alteracoes) -> dict:
    """Cópia da regra válida com sobrescritas de primeiro nível.

    `regra(rule_id="x")` troca o id; `regra(source=None)` remove o bloco.
    """
    nova = copy.deepcopy(REGRA_VALIDA)
    for chave, valor in alteracoes.items():
        if valor is None:
            nova.pop(chave, None)
        else:
            nova[chave] = valor
    return nova


def regra_composta(rule_id: str, referencias: list[tuple[str, str]], **alteracoes) -> dict:
    """Linha sem colunas próprias, calculada por referência a outras regras."""
    nova = regra(rule_id=rule_id, columns=None, filters=None, **alteracoes)
    nova["calculation"] = {
        "references": [{"rule": alvo, "sign": sinal} for alvo, sinal in referencias]
    }
    return nova


POLICY_VALIDA: dict = {
    "policy_id": "ipc07.receita_liquida_de_deducoes",
    "descricao": "Receitas informadas pelos valores líquidos das respectivas deduções.",
    "aplica_a": {"demonstrativo": "BO", "quadro": "QUADRO_PRINCIPAL", "grupo": "RECEITAS"},
    "source": {
        "document": "IPC07",
        "document_version": "2020-01",
        "page": 6,
        "section": "INSTRUÇÕES PARA PREENCHIMENTO DO BALANÇO ORÇAMENTÁRIO",
        "item": "19",
    },
    "evidence": {"page": 6, "text": "as receitas são informadas pelos valores líquidos"},
    "status": "validated",
}


# ─── montagem de uma base temporária ─────────────────────────────────────────

@pytest.fixture
def base(tmp_path: Path):
    """Constrói uma árvore `knowledge/` mínima e devolve o caminho dela.

    Uso: `base(quadro_principal=[regra(), ...])`. Os schemas reais do repositório são
    copiados quando existirem — enquanto não existirem, a validação de schema falha, que é
    o comportamento esperado nesta fase.
    """

    contador = itertools.count()

    def _montar(
        quadro_principal: list[dict] | None = None,
        rp_nao_processados: list[dict] | None = None,
        rp_processados: list[dict] | None = None,
        policies: list[dict] | None = None,
        paginas_ipc07: int = 17,
    ) -> Path:
        raiz = tmp_path / f"base{next(contador)}" / "knowledge"
        (raiz / "rules" / "bo").mkdir(parents=True)
        (raiz / "policies").mkdir()
        (raiz / "sources" / "ipc07").mkdir(parents=True)
        (raiz / "sources" / "stn").mkdir(parents=True)
        (raiz / "indexes").mkdir()

        if (KNOWLEDGE / "schemas").is_dir():
            shutil.copytree(KNOWLEDGE / "schemas", raiz / "schemas")
        else:
            (raiz / "schemas").mkdir()

        arquivos = {
            "quadro_principal": quadro_principal if quadro_principal is not None else [regra()],
            "rp_nao_processados": rp_nao_processados or [],
            "rp_processados": rp_processados or [],
        }
        for nome, regras in arquivos.items():
            destino = raiz / "rules" / "bo" / f"{nome}.yaml"
            _escrever(destino, {"rules": regras})

        _escrever(
            raiz / "policies" / "ipc07.yaml",
            {"policies": policies if policies is not None else [POLICY_VALIDA]},
        )
        _escrever(
            raiz / "sources" / "ipc07" / "metadata.yaml",
            {
                "document": "IPC07",
                "file": "IPC07 - BO atualizacoes - 20200117.pdf",
                "pages": paginas_ipc07,
                "edition": "2020-01",
                "sha256": "0" * 64,
            },
        )
        _escrever(raiz / "sources" / "stn" / "metadata.yaml", {"tables": []})
        return raiz

    return _montar


def _escrever(caminho: Path, conteudo: dict) -> None:
    with caminho.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(conteudo, fh, allow_unicode=True, sort_keys=False)


def mensagens(relatorio) -> str:
    """Todo o texto de erro concatenado — para asserções sobre o que foi reportado."""
    return "\n".join(
        f"{e.rule_id or ''} {e.mensagem} {e.arquivo or ''}:{e.linha or ''}"
        for e in relatorio.erros
    )
