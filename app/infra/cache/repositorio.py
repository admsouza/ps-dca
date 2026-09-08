"""Adapter Postgres da porta de cache. Implementa o mesmo contrato do `RepoFake` dos testes.

`obter`, `gravar` e `listar` — três operações, e o service não sabe se atrás delas há SQLAlchemy ou
um dicionário. É o que permite testar a decisão de servir ou reapurar sem container.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.infra.cache.modelo import AnexoCache, validar_status


@dataclass
class Registro:
    """Linha de `dca_anexo_cache` como dado puro — o service não recebe entidade do ORM."""

    id_ente: str
    an_referencia: int
    anexo: str
    status: str = "ok"
    resultado: dict | None = None
    versao_api: str | None = None
    versao_regras: str | None = None
    erro_detalhe: str | None = None
    solicitado_por: int | None = None
    procedencia: dict | None = None
    diagnostico: dict | None = None
    calculado_em: datetime | None = None
    duracao_ms: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def identidade(self) -> tuple[str, int, str]:
        return (self.id_ente, self.an_referencia, self.anexo)


def _para_dado(linha: AnexoCache) -> Registro:
    return Registro(
        id_ente=linha.id_ente,
        an_referencia=linha.an_referencia,
        anexo=linha.anexo,
        status=linha.status,
        resultado=linha.resultado or None,
        versao_api=linha.versao_api,
        versao_regras=linha.versao_regras,
        erro_detalhe=linha.erro_detalhe,
        solicitado_por=linha.solicitado_por,
        procedencia=linha.procedencia,
        diagnostico=linha.diagnostico,
        calculado_em=linha.calculado_em,
        duracao_ms=linha.duracao_ms,
    )


class RepositorioCache:
    """Porta de persistência do cache, sobre uma sessão do SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def obter(self, ente: str, exercicio: int, anexo: str) -> Registro | None:
        linha = self._db.get(AnexoCache, (ente, exercicio, anexo))
        return _para_dado(linha) if linha else None

    def gravar(self, registro: Registro) -> None:
        """`INSERT` ou `UPDATE` da identidade. Status é validado antes de tocar o banco."""
        validar_status(registro.status)
        linha = self._db.get(AnexoCache, registro.identidade)
        if linha is None:
            linha = AnexoCache(
                id_ente=registro.id_ente,
                an_referencia=registro.an_referencia,
                anexo=registro.anexo,
            )
            self._db.add(linha)

        linha.status = registro.status
        linha.resultado = registro.resultado or {}
        linha.versao_api = registro.versao_api
        linha.versao_regras = registro.versao_regras
        linha.erro_detalhe = registro.erro_detalhe
        linha.procedencia = registro.procedencia
        linha.diagnostico = registro.diagnostico
        linha.duracao_ms = registro.duracao_ms
        linha.calculado_em = registro.calculado_em or datetime.now(UTC)
        if registro.solicitado_por is not None:
            linha.solicitado_por = registro.solicitado_por
        self._db.commit()

    def listar(self, ente: str, exercicio: int) -> list[Registro]:
        """Uma consulta por (ente, exercício) — é o que o resumo agregado precisa."""
        linhas = (
            self._db.query(AnexoCache)
            .filter(AnexoCache.id_ente == ente, AnexoCache.an_referencia == exercicio)
            .all()
        )
        return [_para_dado(linha) for linha in linhas]
