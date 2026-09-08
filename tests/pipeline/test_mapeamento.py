"""Mapeamento vigente, resolução por exercício e procedência do valor apurado.

Bloco 2 da fase TEST. O que está sob teste é o **repositório de vigências** — INSERT-only, uma
tabela para todos os anexos — e o rastro que o resultado carrega para explicar divergência sem
reapurar.

O YAML de `knowledge/` não deixa de existir: ele é a **semente** do repositório. Quem apura em
produção lê do banco; a F1 e estes testes leem do fake, e o domínio não sabe de qual dos dois veio.

Contrato que a F3 tem de satisfazer, e que só existe aqui até ser implementado:

    app.infra.regras.vigencias.publicar(repo, anexo, ano, mes, linhas, origem,
                                        usuario_id=None)  -> dict da vigência publicada
    app.infra.regras.vigencias.resolver(repo, anexo, exercicio)   -> dict da vigente
    app.infra.regras.vigencias.semear(repo, base=None)            -> nº de vigências semeadas
    app.infra.regras.vigencias.carregar(repo, anexo, exercicio)   -> MapaBO (mesma porta do YAML)
    app.infra.regras.vigencias.ORIGENS · PublicacaoDestrutiva
    app.services.pipeline.resultado.para_dados / app.services.pipeline.job.executar

`SemVigencia` é reusada de `app.infra.regras.carregador`: a regra "não aproxima a mais próxima" é a
mesma, venha do YAML ou do banco, e duplicar a exceção deixaria uma das duas metades sem teste.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tests.bo.conftest import FonteFake, saldo
from tests.conftest import KNOWLEDGE
from tests.pipeline.conftest import (
    ANEXO,
    ENTE,
    EXERCICIO,
    VERSAO_API,
    VERSAO_REGRAS,
    RegistroFake,
)

ENTE_NUM = int(ENTE)
OUTRO_ANEXO = "I-C"
CONTA_RECEITA = "521110000"
CONTA_DESPESA = "621200000"
NR = "1100.00.00"

# Uma linha achatada mínima, no shape que `design.md` § 4bis fixa para `linhas` (jsonb).
LINHA = {
    "id": "bo.quadro_principal.receitas.l1",
    "codigo": "L1",
    "rotulo": "RECEITAS CORRENTES",
    "quadro": "QUADRO_PRINCIPAL",
    "grupo": "RECEITAS",
    "condicao": None,
    "filtros": [],
    "exclusoes": [],
    "colunas": [{"id": "previsao_atualizada", "rotulo": "PREVISÃO ATUALIZADA (b)",
                 "contas": [{"cc": CONTA_RECEITA, "operacao": "+", "natureza_saldo": None}],
                 "derivada": []}],
    "referencias": [],
}


@pytest.fixture
def fonte():
    return FonteFake({
        5: [saldo(CONTA_RECEITA, "100000.00", natureza_receita=NR)],
        6: [saldo(CONTA_DESPESA, "80000.00", natureza_receita=NR)],
    })


@pytest.fixture
def publicar():
    def _publicar(repo, anexo=ANEXO, ano=2020, mes=1, linhas=(LINHA,),
                  origem="api-admin", usuario_id=7):
        from app.infra.regras.vigencias import publicar as f
        return f(repo, anexo=anexo, ano=ano, mes=mes, linhas=list(linhas),
                 origem=origem, usuario_id=usuario_id)
    return _publicar


@pytest.fixture
def base_com_tabelas_alteradas(tmp_path):
    """Cópia de `knowledge/` com o sha256 de uma tabela STN trocado.

    Serve ao cenário de mudança de tabela de referência: o resultado tem de ficar distinguível
    mesmo que nenhuma regra tenha mudado.
    """
    def _copiar(nome: str, sha: str) -> Path:
        base = tmp_path / nome / "knowledge"
        shutil.copytree(KNOWLEDGE, base)
        meta = base / "sources" / "stn" / "metadata.yaml"
        dados = yaml.safe_load(meta.read_text(encoding="utf-8"))
        assert dados.get("tables"), "metadata.yaml sem tabelas STN"
        dados["tables"][0]["sha256"] = sha
        meta.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
        return base
    return _copiar


# ─── Requirement: Regra vigente é resolvida pelo exercício apurado ──────────

def test_exercicio_e_parametro_da_carga_de_regras(repo_vigencias, publicar):
    """Scenario: exercício é parâmetro da carga de regras.

    Duas edições publicadas: a de 2020 e uma de 2027. Cada exercício recebe a sua, e o resolvedor
    é a maior vigência `<=` à competência — não "a única publicada".
    """
    from app.infra.regras.vigencias import resolver

    publicar(repo_vigencias, ano=2020)
    publicar(repo_vigencias, ano=2027)

    assert resolver(repo_vigencias, ANEXO, 2025)["ano_vigencia"] == 2020
    assert resolver(repo_vigencias, ANEXO, 2027)["ano_vigencia"] == 2027
    assert resolver(repo_vigencias, ANEXO, 2030)["ano_vigencia"] == 2027, \
        "resolução presumiu edição única"


def test_exercicio_sem_regra_vigente(repo_vigencias, publicar):
    """Scenario: exercício sem regra vigente.

    Falha nomeando o exercício pedido e as vigências disponíveis. Nenhuma regra por aproximação —
    aproximar a mais próxima publicaria número com regra de outra edição normativa.
    """
    from app.infra.regras.carregador import SemVigencia
    from app.infra.regras.vigencias import resolver

    publicar(repo_vigencias, ano=2020)

    with pytest.raises(SemVigencia) as erro:
        resolver(repo_vigencias, ANEXO, 2019)

    mensagem = str(erro.value)
    assert "2019" in mensagem and "2020" in mensagem, mensagem


# ─── Requirement: Mapeamento vigente é publicado sem sobrescrever o anterior ─

def test_correcao_publica_nova_vigencia(repo_vigencias, publicar):
    """Scenario: correção publica nova vigência.

    A anterior permanece legível, com data e origem. Reescrever a publicada tornaria inexplicável
    todo resultado já apurado com ela.
    """
    primeira = publicar(repo_vigencias, ano=2020, origem="seed-yaml", usuario_id=None)
    corrigida = dict(LINHA, rotulo="RECEITAS CORRENTES (corrigido)")
    segunda = publicar(repo_vigencias, ano=2026, linhas=(corrigida,))

    vigencias = repo_vigencias.listar(ANEXO)
    assert len(vigencias) == 2
    assert vigencias[0]["linhas"] == primeira["linhas"]
    assert vigencias[0]["criado_em"] and vigencias[0]["origem"] == "seed-yaml"
    assert vigencias[-1]["linhas"] == segunda["linhas"] != vigencias[0]["linhas"]


def test_alteracao_destrutiva_e_recusada(repo_vigencias, publicar):
    """Scenario: alteração destrutiva é recusada.

    Publicar sobre `(anexo, ano, mes)` existente é recusado, e o repositório não expõe caminho de
    alteração ou remoção — o que o `PRIMARY KEY` garante no banco, o módulo garante na API.
    """
    from app.infra.regras import vigencias
    from app.infra.regras.vigencias import PublicacaoDestrutiva

    publicar(repo_vigencias, ano=2020)

    with pytest.raises(PublicacaoDestrutiva):
        publicar(repo_vigencias, ano=2020, linhas=(dict(LINHA, rotulo="outro"),))

    assert len(repo_vigencias) == 1
    assert repo_vigencias.listar(ANEXO)[0]["linhas"] == [LINHA]
    proibidos = [n for n in ("atualizar", "remover", "apagar", "excluir", "sobrescrever")
                 if hasattr(vigencias, n)]
    assert not proibidos, f"o módulo expõe operação destrutiva: {proibidos}"


def test_origem_e_autoria_registradas(repo_vigencias, publicar):
    """Scenario: origem e autoria registradas.

    Publicação administrativa registra `api-admin` e quem publicou; semente registra `seed-yaml` e
    não tem autor. Origem fora do conjunto é recusada — sem isso, "quem mudou a regra" fica sem
    resposta na primeira divergência.
    """
    from app.infra.regras.vigencias import ORIGENS
    from app.infra.regras.vigencias import publicar as publicar_direto

    administrativa = publicar(repo_vigencias, ano=2020, origem="api-admin", usuario_id=42)
    assert administrativa["origem"] == "api-admin"
    assert administrativa["criado_por_usuario_id"] == 42

    semente = publicar(repo_vigencias, ano=2026, origem="seed-yaml", usuario_id=None)
    assert semente["origem"] == "seed-yaml"
    assert semente["criado_por_usuario_id"] is None

    assert set(ORIGENS) == {"seed-yaml", "api-admin"}
    with pytest.raises(ValueError):
        publicar_direto(repo_vigencias, anexo=ANEXO, ano=2027, mes=1, linhas=[LINHA],
                        origem="manual", usuario_id=1)


def test_semente_a_partir_da_transcricao_normativa(repo_vigencias, fonte):
    """Scenario: semente a partir da transcrição normativa.

    Repositório vazio, semente aplicada a partir dos YAMLs versionados: nasce vigência utilizável
    marcada `seed-yaml`, e a apuração passa a ler dali. As 69 regras do YAML e as do banco têm de
    produzir a **mesma** matriz — se divergirem, a semente perdeu conteúdo no caminho.
    """
    from app.infra.regras import vigencias
    from app.infra.regras.carregador import carregar as carregar_do_yaml
    from app.services.bo.quadro_principal import apurar

    assert len(repo_vigencias) == 0
    assert vigencias.semear(repo_vigencias) >= 1

    publicadas = repo_vigencias.listar(ANEXO)
    assert publicadas and all(v["origem"] == "seed-yaml" for v in publicadas)
    assert all(v["criado_por_usuario_id"] is None for v in publicadas)

    do_banco = vigencias.carregar(repo_vigencias, ANEXO, EXERCICIO)
    do_yaml = carregar_do_yaml(EXERCICIO)
    assert {linha.id for linha in do_banco.linhas} == {linha.id for linha in do_yaml.linhas}

    assert apurar(ENTE_NUM, EXERCICIO, fonte=fonte, mapa=do_banco).matriz == \
        apurar(ENTE_NUM, EXERCICIO, fonte=fonte, mapa=do_yaml).matriz


def test_um_repositorio_para_todos_os_anexos(repo_vigencias, publicar):
    """Scenario: um repositório para todos os anexos.

    Anexo novo entra na mesma tabela, discriminado pela coluna `anexo`. Nenhuma estrutura por
    anexo é criada — é a decisão P-D1, e o que o RGF não fez (`rgf_anexo01..06_cache`).
    """
    from app.infra.regras import vigencias

    publicar(repo_vigencias, anexo=ANEXO, ano=2020)
    publicar(repo_vigencias, anexo=OUTRO_ANEXO, ano=2020)

    assert len(repo_vigencias) == 2
    assert [v["anexo"] for v in repo_vigencias.listar(OUTRO_ANEXO)] == [OUTRO_ANEXO]
    assert vigencias.TABELA == "dca_regra_mapeamento"

    # Nome de função ou tabela **terminado** no código do anexo é o sintoma de estrutura por
    # anexo (`publicar_bo`, `dca_regra_mapeamento_i_c`). Substring solta não serve: "BO" casa
    # dentro de "MapaBO", que é o modelo do domínio.
    from app.services.pipeline.registry import ANEXOS

    sufixos = tuple(f"_{a.lower().replace('-', '_')}" for a in ANEXOS)
    por_anexo = [n for n in dir(vigencias) if n.lower().endswith(sufixos)]
    assert not por_anexo, f"estrutura de vigência por anexo: {por_anexo}"


def test_publicar_mapeamento_de_um_anexo_nao_afeta_outro(pedido, repo, repo_vigencias, publicar):
    """Scenario: publicar mapeamento de um anexo não afeta outro.

    `versao_regras` é por anexo: publicar vigência de `I-C` não pode invalidar o cache do `BO`, ou
    uma correção de uma linha reapuraria os oito anexos de todos os entes.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok", resultado={"bo": 1}))
    publicar(repo_vigencias, anexo=ANEXO, ano=2020)
    antes = pedido(anexo=ANEXO)
    assert antes.status == 200

    publicar(repo_vigencias, anexo=OUTRO_ANEXO, ano=2026)

    depois = pedido(anexo=ANEXO, versao_regras=VERSAO_REGRAS)
    assert depois.status == 200, "cache do BO invalidado por vigência de outro anexo"
    assert depois.resultado == {"bo": 1}


# ─── Requirement: Procedência do valor apurado ──────────────────────────────

def test_divergencia_e_explicavel_pelo_resultado_gravado(repo, lock, fonte, monkeypatch):
    """Scenario: divergência é explicável pelo resultado gravado.

    Depois de gravado, a procedência é lida do registro com a apuração sabotada: se explicar a
    divergência exigisse reapurar, o teste quebra em vez de passar.
    """
    import app.services.bo.quadro_principal as qp
    from app.services.pipeline.job import executar

    def apurador(ente: int, exercicio: int):
        return qp.apurar(ente, exercicio, fonte=fonte)

    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS)

    monkeypatch.setattr(qp, "apurar", lambda *a, **k: pytest.fail("procedência exigiu reapurar"))

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    procedencia = gravado.procedencia
    assert procedencia["regras_aplicadas"] > 0
    assert procedencia["documento"] and procedencia["edicao"]
    assert procedencia["exercicio"] == EXERCICIO
    assert procedencia["tabelas_stn"], "sem versão das tabelas de referência da STN"

    # A procedência declara a versão que a **apuração** usou — a do mapa realmente carregado, não
    # a que o chamador supôs vigente. A coluna `versao_regras` do cache guarda a vigente, que é a
    # chave de invalidação; quando as duas divergem, o produto loga.
    from app.infra.regras.carregador import carregar

    assert procedencia["versao_regras"] == carregar(EXERCICIO).versao_regras


def test_mudanca_de_tabela_de_referencia_e_distinguivel(fonte, base_com_tabelas_alteradas):
    """Scenario: mudança de tabela de referência é distinguível.

    Mesmo anexo, mesmo exercício, mesmas regras: só o sha256 de uma tabela da STN muda. A
    procedência gravada distingue os dois resultados — sem isso, o cache serviria número velho
    depois de a STN corrigir uma tabela.
    """
    from app.infra.regras.carregador import carregar
    from app.services.bo.quadro_principal import apurar
    from app.services.pipeline.resultado import para_dados

    antes = carregar(EXERCICIO, base=base_com_tabelas_alteradas("antes", "a" * 64))
    depois = carregar(EXERCICIO, base=base_com_tabelas_alteradas("depois", "b" * 64))

    um = para_dados(apurar(ENTE_NUM, EXERCICIO, fonte=fonte, mapa=antes))
    outro = para_dados(apurar(ENTE_NUM, EXERCICIO, fonte=fonte, mapa=depois))

    assert um["matriz"] == outro["matriz"], "a mudança alterou o cálculo; o cenário é só de rastro"
    assert um["procedencia"]["tabelas_stn"] != outro["procedencia"]["tabelas_stn"]
    assert um["procedencia"]["versao_regras"] != outro["procedencia"]["versao_regras"]
