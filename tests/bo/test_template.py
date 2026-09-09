"""O template de apresentação acompanha o resultado apurado.

Change `bo-template-no-resultado`. O que está sob teste é o **rastro de apresentação**: rótulo,
quadro, grupo, nível e ordem de cada linha, publicados junto dos valores.

Sem isto, quem renderiza declara as 69 linhas por fora e cria uma segunda fonte da verdade para a
transcrição normativa. Foi exatamente o que aconteceu ao escrever a spec da UI: o nível foi derivado
da árvore de composição e saiu errado em duas de três amostras — a norma põe `Reserva do RPPS` no
nível 2 e `Mobiliária` no 3, a composição sugeriria 1 e 2.
"""
from __future__ import annotations

import pytest

from tests.bo.conftest import FonteFake, saldo

ENTE = 2507507
EXERCICIO = 2025
CONTA_RECEITA = "521110000"
CONTA_DESPESA = "621200000"
NR = "1100.00.00"

# Ordem de apresentação da norma: quadro principal (IPC 07 p. 8–11), b) Não Processados (p. 12),
# c) Processados (p. 13). A ordem alfabética e a de inserção das chaves são a inversa entre os dois
# quadros de Restos a Pagar.
QUADROS_NA_ORDEM = ("QUADRO_PRINCIPAL", "RP_NAO_PROCESSADOS", "RP_PROCESSADOS")


@pytest.fixture
def resultado():
    """Apuração real das 69 regras, com uma fonte mínima — o template não depende dos valores."""
    from app.services.bo.quadro_principal import apurar

    fonte = FonteFake({
        5: [saldo(CONTA_RECEITA, "100000.00", natureza_receita=NR)],
        6: [saldo(CONTA_DESPESA, "80000.00", natureza_receita=NR)],
    })
    return apurar(ENTE, EXERCICIO, fonte=fonte)


@pytest.fixture
def dados(resultado):
    from app.services.pipeline.resultado import para_dados

    return para_dados(resultado)


def test_template_acompanha_os_valores(dados):
    """Scenario: template acompanha os valores."""
    linhas = dados["linhas"]
    assert len(linhas) == 69

    ids_template = [linha["rule_id"] for linha in linhas]
    assert len(set(ids_template)) == 69, "rule_id repetido no template"
    assert set(ids_template) == set(dados["matriz"]), "template e matriz divergem"

    exigidos = {"rule_id", "codigo", "rotulo", "quadro", "grupo", "nivel", "ordem", "totalizadora"}
    for linha in linhas:
        assert exigidos <= set(linha), f"{linha['rule_id']} sem {exigidos - set(linha)}"
        assert linha["rotulo"], f"{linha['rule_id']} sem rótulo"


def test_nivel_e_ordem_sao_os_da_norma(dados):
    """Scenario: nível e ordem são os da norma.

    Os dois valores conferidos aqui são justamente onde a árvore de composição erra: por
    composição, `Reserva do RPPS` cairia no nível 1 e `Mobiliária` no 2.
    """
    por_id = {linha["rule_id"]: linha for linha in dados["linhas"]}

    assert por_id["bo.quadro_principal.despesas.l51"]["nivel"] == 2
    assert por_id["bo.quadro_principal.receitas.l19"]["nivel"] == 3
    assert por_id["bo.quadro_principal.receitas.l18"]["nivel"] == 1
    assert por_id["bo.quadro_principal.receitas.l1"]["nivel"] == 1
    assert por_id["bo.quadro_principal.receitas.l2"]["nivel"] == 2

    assert {linha["nivel"] for linha in dados["linhas"]} == {1, 2, 3}
    assert all(linha["ordem"] >= 1 for linha in dados["linhas"]), "ordem é 1-based na norma"


def test_linhas_saem_na_ordem_de_apresentacao_da_norma(dados):
    """Scenario: linhas saem na ordem de apresentação da norma."""
    linhas = dados["linhas"]

    quadros = list(dict.fromkeys(linha["quadro"] for linha in linhas))
    assert tuple(quadros) == QUADROS_NA_ORDEM

    principal = [linha for linha in linhas if linha["quadro"] == "QUADRO_PRINCIPAL"]
    grupos = list(dict.fromkeys(linha["grupo"] for linha in principal))
    assert grupos == ["RECEITAS", "DESPESAS"]

    for quadro in QUADROS_NA_ORDEM:
        for grupo in {linha["grupo"] for linha in linhas if linha["quadro"] == quadro}:
            ordens = [linha["ordem"] for linha in linhas
                      if linha["quadro"] == quadro and linha["grupo"] == grupo]
            assert ordens == sorted(ordens), f"{quadro}/{grupo} fora de ordem: {ordens}"


def test_ordem_e_relativa_ao_grupo(dados):
    """Scenario: ordem é relativa ao grupo."""
    principal = [linha for linha in dados["linhas"] if linha["quadro"] == "QUADRO_PRINCIPAL"]

    primeiras = [linha for linha in principal if linha["ordem"] == 1]
    assert len(primeiras) == 2, "receitas e despesas começam ambas em 1"
    assert {linha["grupo"] for linha in primeiras} == {"RECEITAS", "DESPESAS"}

    receitas = [linha for linha in principal if linha["grupo"] == "RECEITAS"]
    despesas = [linha for linha in principal if linha["grupo"] == "DESPESAS"]
    assert len(receitas) == 30 and len(despesas) == 21


def test_linha_totalizadora_e_identificavel(dados):
    """Scenario: linha totalizadora é identificável sem reimplementar a regra."""
    por_id = {linha["rule_id"]: linha for linha in dados["linhas"]}

    assert por_id["bo.quadro_principal.receitas.l16"]["totalizadora"] is True   # SUBTOTAL
    assert por_id["bo.quadro_principal.receitas.l1"]["totalizadora"] is True    # grupo
    assert por_id["bo.quadro_principal.receitas.l2"]["totalizadora"] is False   # folha
    assert por_id["bo.quadro_principal.despesas.l51"]["totalizadora"] is False  # rótulo

    assert sum(1 for linha in dados["linhas"] if linha["totalizadora"]) > 0


def test_adicao_nao_quebra_consumidor_existente(dados):
    """Scenario: adição não quebra consumidor existente."""
    assert set(dados) == {"matriz", "procedencia", "diagnostico", "linhas"}

    assert set(dados["procedencia"]) == {
        "documento", "edicao", "exercicio", "versao_regras", "regras_aplicadas", "tabelas_stn",
    }
    assert set(dados["diagnostico"]) == {"nao_apuradas", "residuos", "duracao_ms", "sem_dados"}

    celula = dados["matriz"]["bo.quadro_principal.receitas.l2"]["previsao_atualizada"]
    assert isinstance(celula, str), "valor continua string decimal"


def test_vigencia_antiga_sem_nivel_nem_ordem_e_completada(caplog):
    """Scenario: vigência antiga não tem nível nem ordem.

    Vigência publicada antes desta change não carrega os metadados de apresentação, e a tabela é
    INSERT-only: não há como corrigi-la no lugar. O carregador completa pela transcrição versionada.
    """
    import logging

    from app.infra.regras.carregador import carregar
    from app.infra.regras.vigencias import carregar as carregar_do_banco
    from app.infra.regras.vigencias import publicar
    from tests.pipeline.conftest import RepoVigenciasFake

    do_yaml = carregar(EXERCICIO)
    achatadas = []
    for linha in do_yaml.linhas:
        from app.infra.regras.vigencias import _achatar

        bruta = _achatar(linha)
        bruta.pop("nivel", None)                 # simula a vigência publicada em 2026-09-08
        bruta.pop("ordem", None)
        achatadas.append(bruta)

    repo = RepoVigenciasFake()
    publicar(repo, anexo="BO", ano=2020, mes=1, linhas=achatadas, origem="seed-yaml")

    with caplog.at_level(logging.INFO):
        mapa = carregar_do_banco(repo, "BO", EXERCICIO)

    por_id = {linha.id: linha for linha in mapa.linhas}
    assert por_id["bo.quadro_principal.despesas.l51"].nivel == 2
    assert por_id["bo.quadro_principal.receitas.l19"].nivel == 3
    assert all(linha.ordem >= 1 for linha in mapa.linhas)
    assert any("apresenta" in m.lower() or "nivel" in m.lower() or "nível" in m.lower()
               for m in caplog.messages), "completar metadados não foi registrado em log"


def test_linha_do_banco_sem_correspondente_na_transcricao(caplog):
    """Scenario: linha do banco sem correspondente na transcrição."""
    from app.infra.regras.vigencias import carregar as carregar_do_banco
    from app.infra.regras.vigencias import publicar
    from tests.pipeline.conftest import RepoVigenciasFake

    inventada = {
        "id": "bo.quadro_principal.receitas.l99",
        "codigo": "L99",
        "rotulo": "Linha publicada por via administrativa",
        "quadro": "QUADRO_PRINCIPAL",
        "grupo": "RECEITAS",
        "condicao": None,
        "condicao_coluna": None,
        "filtros": [],
        "exclusoes": [],
        "colunas": [],
        "referencias": [],
    }
    repo = RepoVigenciasFake()
    publicar(repo, anexo="BO", ano=2020, mes=1, linhas=[inventada], origem="api-admin",
             usuario_id=1)

    mapa = carregar_do_banco(repo, "BO", EXERCICIO)
    assert [linha.id for linha in mapa.linhas] == ["bo.quadro_principal.receitas.l99"]
    assert mapa.linhas[0].ordem >= 1, "linha sem correspondente mantém posição de aparição"
