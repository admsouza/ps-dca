"""Adapter Postgres do repositório de vigências. Mesma porta do fake dos testes.

Duas operações: `inserir` e `listar`. **Não há** `atualizar` nem `remover` — a ausência é o
contrato, e o `PRIMARY KEY` de `dca_regra_mapeamento` recusa a segunda publicação da mesma
competência, que é o que `publicar()` traduz em `PublicacaoDestrutiva`.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.infra.cache.modelo import RegraMapeamento


def _para_dado(linha: RegraMapeamento) -> dict:
    criado = linha.criado_em
    return {
        "anexo": linha.anexo,
        "ano_vigencia": linha.ano_vigencia,
        "mes_vigencia": linha.mes_vigencia,
        "versao": linha.versao,
        "linhas": linha.linhas or [],
        "origem": linha.origem,
        "criado_em": criado.isoformat() if isinstance(criado, datetime) else criado,
        "criado_por_usuario_id": linha.criado_por_usuario_id,
    }


class RepositorioVigencias:
    def __init__(self, db: Session) -> None:
        self._db = db

    def inserir(self, registro: dict) -> dict:
        """`INSERT`. Deixa o `IntegrityError` subir — quem chama o traduz."""
        linha = RegraMapeamento(
            anexo=registro["anexo"],
            ano_vigencia=registro["ano_vigencia"],
            mes_vigencia=registro["mes_vigencia"],
            versao=registro["versao"],
            linhas=registro["linhas"],
            origem=registro["origem"],
            criado_por_usuario_id=registro.get("criado_por_usuario_id"),
        )
        self._db.add(linha)
        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(linha)
        return _para_dado(linha)

    def listar(self, anexo: str) -> list[dict]:
        linhas = (
            self._db.query(RegraMapeamento)
            .filter(RegraMapeamento.anexo == anexo)
            .order_by(RegraMapeamento.ano_vigencia, RegraMapeamento.mes_vigencia)
            .all()
        )
        return [_para_dado(linha) for linha in linhas]
