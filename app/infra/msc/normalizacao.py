"""Contrato único de colunas da MSC — as duas fontes entregam o mesmo `Registro`.

O SICONFI responde em snake_case; a PublicSoft, em camelCase. A diferença morre aqui, e o
apurador não sabe qual fonte respondeu.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.domain.bo.modelo import Registro

# Nome no payload -> campo do contrato. Cobre as duas grafias.
CAMPOS = {
    "conta": ("conta_contabil", "codConta", "co_conta", "conta"),
    "natureza": ("natureza_conta", "naturezaConta", "natureza"),
    "valor": ("valor", "vl_saldo", "valorSaldo"),
    "natureza_receita": ("natureza_receita", "naturezaReceita"),
    "natureza_despesa": ("natureza_despesa", "naturezaDespesa"),
    "funcao": ("funcao", "funcao_programatica", "funcaoProgramatica"),
    "subfuncao": ("subfuncao", "subFuncao"),
    "poder_orgao": ("poder_orgao", "poderOrgao"),
    "fonte_recursos": ("fonte_recursos", "fonteRecursos"),
}


def decodificar(valor: str | bytes) -> str:
    """Texto do SICONFI e do `tt/dca` vem em latin-1.

    Comparar rótulo sem decodificar acusa divergência que não existe — foi o que aconteceu na
    medição de João Pessoa antes de decodificar.
    """
    if isinstance(valor, bytes):
        return valor.decode("latin-1")
    return valor


def _primeiro(bruto: dict, nomes: tuple[str, ...]) -> str:
    for nome in nomes:
        if bruto.get(nome) not in (None, ""):
            return decodificar(bruto[nome])
    return ""


def _decimal(valor: str) -> Decimal:
    if not valor:
        return Decimal("0.00")
    try:
        return Decimal(str(valor).replace(",", "."))
    except InvalidOperation:
        return Decimal("0.00")


def normalizar(bruto: dict) -> Registro:
    """Um item da resposta de qualquer fonte vira um `Registro` do domínio."""
    return Registro(
        conta="".join(c for c in _primeiro(bruto, CAMPOS["conta"]) if c.isdigit()),
        natureza=_primeiro(bruto, CAMPOS["natureza"]).upper()[:1],
        valor=_decimal(_primeiro(bruto, CAMPOS["valor"])),
        natureza_receita=_primeiro(bruto, CAMPOS["natureza_receita"]),
        natureza_despesa=_primeiro(bruto, CAMPOS["natureza_despesa"]),
        funcao=_primeiro(bruto, CAMPOS["funcao"]),
        subfuncao=_primeiro(bruto, CAMPOS["subfuncao"]),
        poder_orgao=_primeiro(bruto, CAMPOS["poder_orgao"]),
        fonte_recursos=_primeiro(bruto, CAMPOS["fonte_recursos"]),
    )


def itens(resposta: dict) -> list[dict]:
    """A lista de registros, sob `items` (ORDS) ou `data` (PublicSoft)."""
    for chave in ("items", "data"):
        if isinstance(resposta.get(chave), list):
            return resposta[chave]
    return []
