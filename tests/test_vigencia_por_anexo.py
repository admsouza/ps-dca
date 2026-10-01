"""A semente de vigência cobre todos os anexos implementados, não só o BO.

Origem: log do worker em 2026-09-18 — `sem vigência publicada para BF/2025`, duas vezes por
apuração. O fallback ao YAML está correto; o que faltava era a semente.
"""
from __future__ import annotations

import pytest


class RepoVigenciasFake:
    """Implementa `RepoVigencias`. `INSERT-only`, como a tabela real."""

    def __init__(self):
        self.publicadas: list[dict] = []

    def inserir(self, registro: dict) -> dict:
        chave = (registro["anexo"], registro["ano_vigencia"], registro["mes_vigencia"])
        if any((r["anexo"], r["ano_vigencia"], r["mes_vigencia"]) == chave
               for r in self.publicadas):
            raise KeyError(chave)   # PK duplicada: o mesmo que o banco recusa
        self.publicadas.append(registro)
        return registro

    def listar(self, anexo: str) -> list[dict]:
        return [r for r in self.publicadas if r["anexo"] == anexo]


@pytest.fixture
def semear():
    from app.infra.regras.vigencias import semear as funcao
    return funcao


def test_semente_publica_bo_e_bf(semear):
    """Scenario: BO e BF semeados no boot"""
    repo = RepoVigenciasFake()
    publicadas = semear(repo)

    anexos = {r["anexo"] for r in repo.publicadas}
    assert {"BO", "BF"} <= anexos, f"semeados: {anexos}"
    assert publicadas >= 2

    por_anexo = {r["anexo"]: r for r in repo.publicadas}
    assert por_anexo["BO"]["ano_vigencia"] == 2020, "edição 2020-01 do IPC 07"
    assert por_anexo["BF"]["ano_vigencia"] == 2024, "edição 2024-06 do IPC 06"
    assert all(r["origem"] == "seed-yaml" for r in repo.publicadas)


def test_semente_e_idempotente(semear):
    """Scenario: segundo boot não reescreve"""
    repo = RepoVigenciasFake()
    semear(repo)
    quantas = len(repo.publicadas)

    assert semear(repo) == 0
    assert len(repo.publicadas) == quantas


def test_bf_carregado_do_banco_confere_com_o_yaml(semear):
    """Scenario: apuração do BF deixa de cair no YAML

    O mapa vindo do banco tem de ser o mesmo que o YAML produz — mesmas linhas, mesmos códigos.
    """
    from app.infra.regras.carregador import carregar as do_yaml
    from app.infra.regras.vigencias import carregar as do_banco

    repo = RepoVigenciasFake()
    semear(repo)

    banco = do_banco(repo, "BF", 2025)
    yaml = do_yaml(2025, demonstrativo="bf")
    assert len(banco.linhas) == len(yaml.linhas) == 80
    assert ({linha.codigo for linha in banco.linhas}
            == {linha.codigo for linha in yaml.linhas})
    assert banco.vigencia.documento == yaml.vigencia.documento
    natureza = {linha.codigo: linha.apenas_natureza for linha in banco.linhas}
    assert natureza["L28"] == "C"
    assert natureza["L61"] == "D"


def test_completacao_usa_a_transcricao_do_proprio_anexo(semear):
    """Scenario: BF completado pela transcrição do IPC 06"""
    repo = RepoVigenciasFake()
    semear(repo)

    from app.infra.regras.vigencias import carregar as do_banco

    mapa = do_banco(repo, "BF", 2025)
    principal = [linha for linha in mapa.linhas if linha.quadro == "QUADRO_PRINCIPAL"]
    assert all(linha.nivel and linha.ordem for linha in principal), \
        "nível e ordem vêm da transcrição do IPC 06"


def _linha_sem_conta(rule_id: str, codigo: str) -> dict:
    return {
        "id": rule_id,
        "codigo": codigo,
        "rotulo": codigo,
        "quadro": "QUADRO_PRINCIPAL",
        "grupo": "INGRESSOS",
        "colunas": [
            {"id": "exercicio_atual", "rotulo": "Atual", "contas": [], "derivada": []},
            {"id": "exercicio_anterior", "rotulo": "Anterior", "contas": [], "derivada": []},
        ],
        "referencias": [],
    }


def test_semente_antiga_de_l28_l61_herda_contas_e_natureza():
    """Requisito: vigência 2024-01 sem conta em L28/L61 passa a calcular com o YAML."""
    from app.infra.regras.vigencias import carregar as do_banco

    repo = RepoVigenciasFake()
    repo.inserir({
        "anexo": "BF",
        "ano_vigencia": 2024,
        "mes_vigencia": 1,
        "versao": "2024-01",
        "linhas": [
            _linha_sem_conta("bf.quadro_principal.ingressos.l28", "L28"),
            _linha_sem_conta("bf.quadro_principal.dispendios.l61", "L61"),
        ],
        "origem": "seed-yaml",
    })

    por_codigo = {linha.codigo: linha for linha in do_banco(repo, "BF", 2025).linhas}
    l28 = por_codigo["L28"]
    l61 = por_codigo["L61"]
    assert l28.apenas_natureza == "C"
    assert l61.apenas_natureza == "D"
    assert next(f.valores for f in l28.filtros if f.campo == "fonte_recurso") == (
        "860", "861", "862", "863", "869",
    )
    assert next(f.valores for f in l61.filtros if f.campo == "fonte_recurso") == (
        "860", "861", "862", "863", "869",
    )
    assert any(c.contas for c in l28.colunas)
    assert any(c.contas for c in l61.colunas)
