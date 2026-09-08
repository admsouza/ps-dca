"""Convivência das migrations da DCA num schema que já é de RREO e RGF.

Três garantias, todas exigidas pelo requisito "Convivência com os demais pipelines no banco
compartilhado":

1. **Tabela de versão própria** (`alembic_version_dca`), e aborto se o histórico da DCA aparecer na
   genérica — sintoma de `alembic upgrade` rodado com config sem `version_table`, e seguir adiante
   sobrescreveria o histórico do projeto errado.
2. **Advisory lock com as mesmas chaves dos irmãos** (`43812/1001`). Compartilhar a chave é
   deliberado: como os três dividem o schema, o lock serializa migrations **entre projetos**, não
   só entre réplicas do mesmo serviço.
3. **Só objetos `dca_*`.** Verificado em teste sobre o código das revisões — o que erra na prática
   é o alvo de um `op.*`, e ele está no arquivo.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

logger = logging.getLogger(__name__)

TABELA_DE_VERSAO = "alembic_version_dca"
PREFIXO_TABELAS = "dca_"
LOCK = (43812, 1001)

# Tabelas de versão dos irmãos: nunca tocadas, e a genérica não pode conter marcador da DCA.
TABELA_GENERICA = "alembic_version"
DOS_IRMAOS = ("alembic_version_rreo", "alembic_version_rgf")


class HistoricoForaDaTabela(RuntimeError):
    """O marcador da DCA está fora de `alembic_version_dca`. Nenhuma revisão é aplicada."""


class Inspetor(Protocol):
    """O que a verificação precisa saber do banco. Implementado pelo inspetor do SQLAlchemy."""

    def tem_tabela(self, nome: str) -> bool: ...
    def versao_em(self, nome: str) -> str | None: ...


class Conexao(Protocol):
    """Porta do advisory lock. `adquirir_lock` é `pg_try_advisory_lock` com espera."""

    def adquirir_lock(self, classe: int, chave: int, timeout: int | None = None) -> bool: ...
    def liberar_lock(self, classe: int, chave: int) -> None: ...


def verificar_tabela_de_versao(inspetor: Inspetor) -> None:
    """Aborta se o histórico da DCA foi registrado fora da sua tabela de versão."""
    if not inspetor.tem_tabela(TABELA_GENERICA):
        return

    marcador = inspetor.versao_em(TABELA_GENERICA)
    if marcador and PREFIXO_TABELAS.rstrip("_") in marcador.lower():
        raise HistoricoForaDaTabela(
            f"marcador da DCA ({marcador!r}) está em {TABELA_GENERICA!r}, e o histórico real da "
            f"DCA é {TABELA_DE_VERSAO!r}. Rodar migration agora sobrescreveria o histórico de "
            f"outro projeto. Mova o marcador para {TABELA_DE_VERSAO!r} e apague-o da genérica."
        )


def migrar(conexao: Conexao, aplicar: Callable[[], None], timeout: int | None = None) -> bool:
    """Aplica as revisões sob o advisory lock. `False` = outro processo está migrando.

    Quem não pega o lock **não aplica** e não falha: observa o resultado de quem pegou. Duas
    réplicas aplicando ao mesmo tempo é como se produz `DuplicateTable` no boot.
    """
    classe, chave = LOCK
    if not conexao.adquirir_lock(classe, chave, timeout):
        logger.info("Migration em curso por outro processo (lock %s/%s) — nada a aplicar.",
                    classe, chave)
        return False
    try:
        aplicar()
        return True
    finally:
        conexao.liberar_lock(classe, chave)
