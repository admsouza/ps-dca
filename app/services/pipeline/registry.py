"""Os anexos da DCA, declarados **uma vez**, na ordem canônica de apresentação.

`BO` vem primeiro por ser o demonstrativo derivado — apurado da MSC pelas regras do IPC 07, e
publicado pelo STN como `RREO-Anexo 01`, não como anexo da DCA. Os sete seguintes são os anexos da
DCA na ordem em que o SICONFI os lista (`docs/anexos-siconfi-inventario.md`).

Anexo sem implementação entra com `servico=None`: é assim que o resumo o reporta como `sem_cache`
em vez de omiti-lo. Um job só, parametrizado por anexo (P4).
"""
from __future__ import annotations

from dataclasses import dataclass

ANEXO_BO = "BO"
JOB_APURAR = "apurar_anexo"


@dataclass(frozen=True)
class Anexo:
    codigo: str
    servico: str | None          # "modulo:funcao" — `None` = ainda não implementado
    job: str = JOB_APURAR


REGISTRY: tuple[Anexo, ...] = (
    Anexo(ANEXO_BO, "app.services.bo.quadro_principal:apurar"),
    Anexo("I-AB", None),
    Anexo("I-C", None),
    Anexo("I-D", None),
    Anexo("I-E", None),
    Anexo("I-F", None),
    Anexo("I-G", None),
    Anexo("I-HI", None),
)

ANEXOS: tuple[str, ...] = tuple(a.codigo for a in REGISTRY)

# Grafias que chegam de cliente e apontam o mesmo anexo. Sem isto, `i-c` e `I_C` fragmentariam o
# cache em três entradas para o mesmo demonstrativo.
_CANONICO = {a.codigo.upper().replace("-", "").replace("_", ""): a.codigo for a in REGISTRY}


class AnexoDesconhecido(ValueError):
    """Anexo fora do conjunto fechado. Nunca cria entrada de cache."""


def validar_anexo(anexo: str) -> str:
    """Devolve a grafia canônica. Recusa o que não está no registry."""
    chave = str(anexo or "").strip().upper().replace("-", "").replace("_", "").replace(" ", "")
    if chave not in _CANONICO:
        raise AnexoDesconhecido(
            f"anexo desconhecido: {anexo!r} — esperado um de {', '.join(ANEXOS)}"
        )
    return _CANONICO[chave]


def anexo(codigo: str) -> Anexo:
    canonico = validar_anexo(codigo)
    return next(a for a in REGISTRY if a.codigo == canonico)


def implementado(codigo: str) -> bool:
    return anexo(codigo).servico is not None
