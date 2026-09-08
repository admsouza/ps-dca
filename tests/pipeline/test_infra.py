"""Convivência no banco compartilhado, núcleo isolado e falha de infraestrutura.

Bloco 4 da fase TEST. Três assuntos que só se parecem: o que a migration da DCA pode tocar num
schema que já é de RREO e RGF, o que o núcleo pode importar, e o que a plataforma faz quando a
infraestrutura cai.

As migrations são verificadas **sem Postgres**: o que erra na prática é o alvo de um `op.*` e a
tabela de versão, e as duas coisas estão no código. Um teste que exigisse banco de produção para
provar que a migration não toca `rreo_*` não rodaria em CI, e é justo o que precisa rodar antes de
o deploy tocar o schema dos irmãos.

Contrato que a F3 tem de satisfazer, e que só existe aqui até ser implementado:

    app.core.migrations.TABELA_DE_VERSAO = "alembic_version_dca" · PREFIXO_TABELAS = "dca_"
    app.core.migrations.LOCK = (43812, 1001)
    app.core.migrations.verificar_tabela_de_versao(inspetor)   -> HistoricoForaDaTabela
    app.core.migrations.migrar(conexao, aplicar, timeout=None) -> bool (aplicou?)
    app.services.pipeline.startup.verificar_dependencias(redis=..., banco=...)
    app.services.pipeline.startup.DependenciaIndisponivel
"""
from __future__ import annotations

import logging
import re
import socket
from pathlib import Path

import pytest

from tests.bo.conftest import DirecaoFake, FonteFake, saldo
from tests.conftest import RAIZ_REPO
from tests.pipeline.conftest import (
    ANEXO,
    ENTE,
    EXERCICIO,
    VERSAO_API,
    VERSAO_REGRAS,
)
from tests.test_fronteira_camadas import _fecho_de, _importados

ENTE_NUM = int(ENTE)
CONTA_RECEITA = "521110000"
CONTA_DESPESA = "621200000"
NR = "1100.00.00"

# Tabelas dos irmãos, levantadas por inspeção read-only em 2026-09-04 (design.md § 4).
DOS_IRMAOS = ("rreo_anexo01_cache", "rgf_anexo01_cache", "rgf_anexo02_mapeamento",
              "alembic_version_rreo", "alembic_version_rgf")

# `op.<nome>(` cujo primeiro argumento é o objeto tocado.
OPERACOES_COM_ALVO = re.compile(
    r"op\.(create_table|drop_table|add_column|drop_column|alter_column|rename_table|"
    r"create_index|drop_index|execute)\(\s*[\"']([^\"']+)[\"']"
)

# Objeto da DCA: tabela `dca_*`, ou índice/constraint pela convenção de nome (`ix_dca_*`,
# `chk_dca_*`). O prefixo de tipo vem antes do domínio, e checar só `startswith("dca_")`
# acusaria os próprios índices da DCA.
DA_DCA = re.compile(r"^(ix_|uq_|chk_|fk_|pk_)?dca_")


class InspetorFake:
    """Dublê do inspetor do SQLAlchemy: só a lista de tabelas e o marcador de cada versão."""

    def __init__(self, tabelas: dict[str, str | None]):
        self.tabelas = dict(tabelas)

    def tem_tabela(self, nome: str) -> bool:
        return nome in self.tabelas

    def versao_em(self, nome: str) -> str | None:
        return self.tabelas.get(nome)


class ConexaoFake:
    """Serializa como o advisory lock do Postgres: um dono por chave, os demais esperam."""

    tomados: dict[tuple[int, int], str] = {}

    def __init__(self, nome: str):
        self.nome = nome
        self.esperas: list[tuple[int, int]] = []
        self.locks: list[tuple[int, int]] = []

    def adquirir_lock(self, classe: int, chave: int, timeout: int | None = None) -> bool:
        alvo = (classe, chave)
        if ConexaoFake.tomados.get(alvo) not in (None, self.nome):
            self.esperas.append(alvo)
            return False
        ConexaoFake.tomados[alvo] = self.nome
        self.locks.append(alvo)
        return True

    def liberar_lock(self, classe: int, chave: int) -> None:
        ConexaoFake.tomados.pop((classe, chave), None)


@pytest.fixture(autouse=True)
def _lock_limpo():
    ConexaoFake.tomados.clear()
    yield
    ConexaoFake.tomados.clear()


@pytest.fixture
def fonte():
    return FonteFake({
        5: [saldo(CONTA_RECEITA, "100000.00", natureza_receita=NR)],
        6: [saldo(CONTA_DESPESA, "80000.00", natureza_receita=NR)],
    })


# ─── Requirement: Convivência com os demais pipelines no banco compartilhado ─

def test_migracao_em_banco_que_ja_tem_os_irmaos():
    """Scenario: migração em banco que já tem os irmãos.

    Toda operação de toda revisão aponta para objeto `dca_*`. Varredura do código, não do banco: é
    o que roda em CI antes de o deploy tocar um schema com 44 tabelas de três projetos.
    """
    from app.core import migrations

    assert migrations.TABELA_DE_VERSAO == "alembic_version_dca"
    assert migrations.PREFIXO_TABELAS == "dca_"

    versoes = Path(RAIZ_REPO / "alembic" / "versions")
    assert versoes.is_dir(), "alembic/versions/ não existe (F3 não implementada)"

    revisoes = sorted(versoes.glob("*.py"))
    assert revisoes, "nenhuma revisão a verificar"

    alheias = [
        f"{arquivo.name}: {operacao} em {alvo}"
        for arquivo in revisoes
        for operacao, alvo in OPERACOES_COM_ALVO.findall(arquivo.read_text(encoding="utf-8"))
        if not DA_DCA.match(alvo)
    ]
    assert not alheias, "migration toca objeto que não é da DCA:\n  " + "\n  ".join(alheias)

    fontes = " ".join(a.read_text(encoding="utf-8") for a in revisoes)
    tocadas = [t for t in DOS_IRMAOS if t in fontes]
    assert not tocadas, f"migration menciona tabela dos irmãos: {tocadas}"


def test_historico_registrado_na_tabela_errada():
    """Scenario: histórico registrado na tabela errada.

    Marcador da DCA em `alembic_version` genérica: aborta nomeando a tabela que reflete o histórico
    real, e nenhuma revisão é aplicada. É o sintoma de um `alembic upgrade` rodado com config sem
    `version_table` — e seguir adiante sobrescreveria o histórico do projeto errado.
    """
    from app.core.migrations import HistoricoForaDaTabela, verificar_tabela_de_versao

    with pytest.raises(HistoricoForaDaTabela) as erro:
        verificar_tabela_de_versao(InspetorFake({"alembic_version": "001_dca_anexo_cache",
                                                 "dca_anexo_cache": None}))

    assert "alembic_version_dca" in str(erro.value), str(erro.value)

    # Cenário são: histórico na tabela própria, com as dos irmãos presentes e intactas.
    verificar_tabela_de_versao(InspetorFake({
        "alembic_version_dca": "001_dca_anexo_cache",
        "alembic_version_rreo": "032",
        "alembic_version_rgf": "060_token_ps_validacao_status",
    }))


def test_migrations_simultaneas_de_projetos_diferentes():
    """Scenario: migrations simultâneas de projetos diferentes.

    A chave do advisory lock é a **mesma** dos irmãos (`43812/1001`), de propósito: os três dividem
    o schema, então o lock serializa entre projetos, não só entre réplicas. Nenhuma das duas falha
    por concorrência.
    """
    from app.core.migrations import LOCK, migrar

    assert LOCK == (43812, 1001)

    aplicadas = []
    dca, irmao = ConexaoFake("dca"), ConexaoFake("rgf")

    assert migrar(dca, lambda: aplicadas.append("dca")) is True
    assert ConexaoFake.tomados == {}, "lock não liberado ao fim da migração"

    assert migrar(irmao, lambda: aplicadas.append("rgf")) is True
    assert aplicadas == ["dca", "rgf"]


def test_replicas_subindo_juntas():
    """Scenario: réplicas subindo juntas.

    A segunda réplica não aplica as revisões: espera e observa o resultado. Duas aplicando ao mesmo
    tempo é como se produz `DuplicateTable` no boot.
    """
    from app.core.migrations import migrar

    aplicadas = []
    primeira, segunda = ConexaoFake("replica-1"), ConexaoFake("replica-2")

    def aplicar():
        aplicadas.append("revisoes")
        # A segunda réplica tenta enquanto a primeira ainda tem o lock.
        assert migrar(segunda, lambda: aplicadas.append("revisoes-again")) is False

    assert migrar(primeira, aplicar) is True
    assert aplicadas == ["revisoes"], "as duas réplicas aplicaram"
    assert segunda.esperas == [(43812, 1001)]


# ─── Requirement: Núcleo de apuração isolado de infraestrutura ──────────────

def test_apuracao_testavel_sem_infraestrutura(fonte, monkeypatch):
    """Scenario: apuração testável sem infraestrutura.

    Rede bloqueada no nível do socket: se qualquer coisa no caminho da apuração tentar Redis,
    Postgres ou HTTP, o teste quebra. Um assert de "não importou `requests`" não pegaria uma
    conexão aberta por dependência transitiva.

    **Passa contra a F1**, como os testes do hash canônico (task 2.8.1): a propriedade já existe e
    o teste a trava. Verificado por injeção — um `socket.create_connection` no caminho da apuração
    derruba o teste.
    """
    from app.services.bo.quadro_principal import apurar

    def sem_rede(*_a, **_k):
        raise AssertionError("a apuração abriu socket — dependeu de infraestrutura")

    monkeypatch.setattr(socket, "socket", sem_rede)
    monkeypatch.setattr(socket, "create_connection", sem_rede)

    resultado = apurar(ENTE_NUM, EXERCICIO, fonte=fonte)
    assert resultado.matriz
    assert resultado.procedencia.regras_aplicadas > 0


def test_troca_de_fonte_nao_altera_o_dominio(fonte):
    """Scenario: troca de fonte não altera o domínio.

    Duas fontes distintas, a mesma matriz — e nenhum módulo do domínio **importa** adapter de
    fonte. A verificação é por import, não por texto: `domain/bo/portas.py` cita SICONFI e
    PublicSoft no docstring para explicar a inversão, e um grep de palavras acusaria isso como
    dependência.
    """
    from app.services.bo.quadro_principal import apurar

    outra = FonteFake({5: [saldo(CONTA_RECEITA, "100000.00", natureza_receita=NR)],
                       6: [saldo(CONTA_DESPESA, "80000.00", natureza_receita=NR)]},
                      rotulo="publicsoft")
    assert apurar(ENTE_NUM, EXERCICIO, fonte=fonte).matriz == \
        apurar(ENTE_NUM, EXERCICIO, fonte=outra).matriz

    dependencias = [
        f"{modulo} importa {nome}"
        for modulo, caminho in sorted(_fecho_de(RAIZ_REPO / "app" / "domain").items())
        for nome in sorted(_importados(caminho))
        if nome.startswith("app.infra") or nome.split(".")[0] in ("requests", "redis", "psycopg2")
    ]
    assert not dependencias, "o domínio conhece a fonte:\n  " + "\n  ".join(dependencias)


# ─── Requirement: Falha de infraestrutura é reportada, não mascarada ────────

def test_fonte_msc_indisponivel(repo, lock, jobs):
    """Scenario: fonte MSC indisponível.

    Job em `error` com a causa e cache em `erro` — **nunca** `ok` com matriz incompleta. Gravar
    `ok` com zeros é o pior desfecho possível: o número entra no demonstrativo e ninguém percebe.
    """
    from app.infra.fila.job_manager import criar, estado
    from app.services.pipeline.job import executar

    class FonteMorta:
        def registros(self, ente, ano, mes, classe):
            raise ConnectionError("timeout ao ler a MSC do SICONFI")

    def apurador(ente, exercicio):
        from app.services.bo.quadro_principal import apurar
        return apurar(ente, exercicio, fonte=FonteMorta(), direcao=DirecaoFake())

    criar(jobs, "job-1", ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO)
    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS,
             jobs=jobs, job_id="job-1")

    falho = estado(jobs, "job-1")
    assert falho["status"] == "error"
    assert "MSC" in falho["erro"] or "timeout" in falho["erro"].lower()

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert gravado.status == "erro", "cache gravado como ok com apuração que não ocorreu"
    assert gravado.resultado is None
    assert all(g.status != "ok" for g in repo.gravacoes)


def test_verificacao_de_dependencias_no_startup_do_worker(caplog):
    """Scenario: verificação de dependências no startup do worker.

    Redis e Postgres verificados no boot, com o resultado em log. Dependência fora do ar não pode
    virar worker de pé consumindo fila que não sabe gravar.
    """
    from app.services.pipeline.startup import (
        DependenciaIndisponivel,
        verificar_dependencias,
    )

    ok = lambda: True                                    # noqa: E731 - dublê de ping
    morto = lambda: (_ for _ in ()).throw(ConnectionError("connection refused"))  # noqa: E731

    with caplog.at_level(logging.INFO):
        estado = verificar_dependencias(redis=ok, banco=ok)
    assert estado == {"redis": "ok", "banco": "ok"}
    assert any("redis" in m.lower() for m in caplog.messages), "verificação não foi registrada"

    caplog.clear()
    with caplog.at_level(logging.ERROR), pytest.raises(DependenciaIndisponivel) as erro:
        verificar_dependencias(redis=morto, banco=ok)

    assert "redis" in str(erro.value).lower()
    assert any("refused" in m.lower() for m in caplog.messages), \
        "falha de dependência ficou silenciosa"
