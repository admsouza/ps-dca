"""Mapa do BF e validação dos valores informados — sem tocar na fonte de dados.

Separado de `quadro_principal` porque a rota precisa recusar um mapa manual inválido **antes** de
enfileirar o job, e o fecho transitivo de `app/routes/` não pode alcançar `app.infra.msc`: a API
lê cache, enfileira e responde. Aqui só entram regras e o mapa.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.domain.bo.modelo import MapaBO
from app.infra.regras.carregador import carregar_em_cache

QUADRO_PRINCIPAL = "QUADRO_PRINCIPAL"
QUADRO_ANEXO = "QUADRO_ANEXO"


class LinhaDesconhecida(ValueError):
    """Valor informado para uma linha que o IPC 06 não declara. Recusado antes de apurar."""


# Quatro linhas do quadro principal sem conta declarada no IPC 06 (G8-b) — override pontual do
# exercício atual, independente do modo Manual do exercício anterior (D3). L28/L61 saíram da
# whitelist (change `bf-l28-l61-contas-especificas`): passaram a ter conta e cálculo próprios.
CODIGOS_SEM_MAPEAMENTO = frozenset({"L22", "L23", "L55", "L56"})


def decimal_informado(chave: str, bruto) -> Decimal:
    """Valor digitado como `Decimal` finito e de escala razoável (até 10^15), ou `ValueError`.

    `Decimal("1E+999999999")` e `NaN` passam em `Decimal()` e estouram só dentro do job.
    """
    try:
        valor = Decimal(str(bruto))
    except InvalidOperation as erro:
        raise ValueError(f"valor inválido em {chave}") from erro
    if not valor.is_finite() or abs(valor.adjusted()) > 15:
        raise ValueError(f"valor inválido em {chave}")
    return valor


def validar_valores_sem_mapeamento(valores: dict[str, str]) -> None:
    """Recusa código fora das quatro linhas G8 e valor não decimal, antes de enfileirar o job."""
    desconhecidos = sorted(set(valores) - CODIGOS_SEM_MAPEAMENTO)
    if desconhecidos:
        raise LinhaDesconhecida(
            f"linhas fora das quatro sem conta no IPC 06: {', '.join(desconhecidos)}")
    for codigo, valor in valores.items():
        decimal_informado(codigo, valor)


def validar_valores_anteriores(exercicio: int, valores: dict[str, str]) -> None:
    """Recusa valor não-numérico e código que o IPC 06 não declara, antes de enfileirar o job."""
    decimais = {}
    for codigo, valor in valores.items():
        decimais[codigo] = decimal_informado(codigo, valor)
    mapa = mapa_bf(exercicio)
    principal, anexo = partir_informados(decimais)
    validar_informados(principal, mapa, QUADRO_PRINCIPAL)
    validar_informados(anexo, mapa, QUADRO_ANEXO)


def mapa_bf(exercicio: int) -> MapaBO:
    """Os dois quadros do BF — o principal e o anexo — num mapa só.

    Separá-los em dois serviços duplicaria a leitura da MSC: as mesmas classes, o mesmo ente, o
    mesmo exercício, para produzir dois pedaços do mesmo demonstrativo.
    """
    return carregar_em_cache(exercicio, demonstrativo="bf")


def partir_informados(informados: dict[str, Decimal]):
    """Principal é `L2`. Anexo é `A:L1:receita` e `A:L1:deducoes` — o código L1 existe nos dois."""
    principal: dict[str, Decimal] = {}
    anexo: dict[str, dict[str, Decimal]] = {}
    for chave, valor in informados.items():
        partes = chave.split(":")
        if len(partes) == 3 and partes[0] == "A" and partes[2] in ("receita", "deducoes"):
            anexo.setdefault(partes[1], {})[partes[2]] = valor
        else:
            principal[chave] = valor
    return principal, anexo


def validar_informados(informados: dict, mapa: MapaBO, quadro: str) -> None:
    declarados = {linha.codigo for linha in mapa.linhas if linha.quadro == quadro}
    desconhecidas = sorted(set(informados) - declarados)
    if desconhecidas:
        raise LinhaDesconhecida(
            f"linhas informadas que o IPC 06 não declara: {', '.join(desconhecidas)}")
