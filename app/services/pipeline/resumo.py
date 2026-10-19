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

from app.domain import recorte as recortes
from app.services.pipeline.cache import escolhas_gravadas
from app.services.pipeline.registry import ANEXOS, REGISTRY

SEM_CACHE = "sem_cache"
COM_UNIDADES = ("BF", "BP")      # só estes anexos trazem `recortes`


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


def _unidades(registro, poderes: tuple[str, ...]) -> list[dict]:
    """`ug:`/`po:` do resultado `ok` que o usuário vê, como na leitura do anexo. Sem `ok`, sem
    recortes gravados ou sem poderes: `[]`. O rótulo é o gravado."""
    ok = registro is not None and registro.status == "ok"
    gravados = (registro.resultado or {}).get("recortes") if ok else None
    unidades = {c: r["poderOrgao"] for c, r in (gravados or {}).items()
                if c not in recortes.GRUPOS}
    escolhas = escolhas_gravadas(registro) if registro is not None else {}
    return [{"chave": c, "tipo": recortes.tipo(c), "rotulo": gravados[c]["rotulo"],
             **_anterior(escolhas.get(c))}
            for c in recortes.visiveis(unidades, unidades, poderes)]


def _anterior(escolha: dict | None) -> dict:
    """A escolha que a apuração aplica na unidade. Ausente = automática (padrão do pipeline).

    Sem ela o front só teria a preferência do navegador, que some entre sessões e passa a
    contradizer a coluna servida (a escolha vive na procedência, não no `sessionStorage`).
    """
    if not escolha:
        return {}
    return {"anterior": {"origem": escolha["origem"], "manual": bool(escolha.get("valores"))}}


def resumir(*, ente: str, exercicio: int, repo: Repo,
            poderes: tuple[str, ...] = ()) -> list[dict]:
    """Uma entrada por anexo, na ordem canônica, sempre com os oito."""
    por_anexo = {r.anexo: r for r in repo.listar(ente, exercicio)}
    tem_servico = {a.codigo: a.servico is not None for a in REGISTRY}

    entradas = [
        _entrada(codigo, por_anexo[codigo], tem_servico[codigo]) if codigo in por_anexo
        else _entrada_vazia(codigo, tem_servico[codigo])
        for codigo in ANEXOS
    ]
    for entrada in entradas:
        if entrada["anexo"] in COM_UNIDADES:
            entrada["recortes"] = _unidades(por_anexo.get(entrada["anexo"]), poderes)
    return entradas
