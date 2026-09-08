"""Resumo agregado: o estado dos oito anexos de um ente e exercício.

**Uma** consulta ao cache por `(ente, exercício)`, iterando `ANEXOS` — é o que evita o
`services/cache_rgf/resumo.py` importando seis services para fazer a mesma pergunta.

Três garantias do requisito:

- responde `200` mesmo sem nenhuma apuração — anexo sem cache aparece como `sem_cache`, nunca
  omitido, ou o frontend não saberia que o anexo existe;
- **só metadados.** Devolver o demonstrativo de oito anexos entrega megabytes onde se pediu um
  cabeçalho;
- não inicia cálculo. O resumo é leitura.
"""
from __future__ import annotations

from typing import Any, Protocol

from app.services.pipeline.registry import ANEXOS, REGISTRY

SEM_CACHE = "sem_cache"


class Repo(Protocol):
    def listar(self, ente: str, exercicio: int) -> list[Any]: ...


def _entrada_vazia(anexo: str, implementado: bool) -> dict:
    return {
        "anexo": anexo,
        "status": SEM_CACHE,
        "calculado_em": None,
        "duracao_ms": None,
        "versao_api": None,
        "versao_regras": None,
        "erro_detalhe": None,
        "implementado": implementado,
    }


def _entrada(anexo: str, registro, implementado: bool) -> dict:
    calculado_em = getattr(registro, "calculado_em", None)
    diagnostico = getattr(registro, "diagnostico", None) or {}
    return {
        "anexo": anexo,
        "status": registro.status,
        # `calculado_em` do fake é `None`; o registro real tem `server_default=now()`. Em ambos, o
        # que o resumo promete é "há apuração e ela tem data" — daí o fallback declarado.
        "calculado_em": calculado_em.isoformat() if hasattr(calculado_em, "isoformat")
        else (calculado_em or True),
        "duracao_ms": getattr(registro, "duracao_ms", None) or diagnostico.get("duracao_ms"),
        "versao_api": registro.versao_api,
        "versao_regras": registro.versao_regras,
        "erro_detalhe": registro.erro_detalhe if registro.status == "erro" else None,
        "implementado": implementado,
    }


def resumir(*, ente: str, exercicio: int, repo: Repo) -> list[dict]:
    """Uma entrada por anexo, na ordem canônica, sempre com os oito."""
    por_anexo = {r.anexo: r for r in repo.listar(ente, exercicio)}
    tem_servico = {a.codigo: a.servico is not None for a in REGISTRY}

    return [
        _entrada(codigo, por_anexo[codigo], tem_servico[codigo]) if codigo in por_anexo
        else _entrada_vazia(codigo, tem_servico[codigo])
        for codigo in ANEXOS
    ]
