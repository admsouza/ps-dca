"""BP declarado: o `DCA-Anexo I-AB` do `tt/dca` convertido nas entradas do motor do IPC 04.

O `I-AB` publica a hierarquia inteira (1º ao 5º/6º nível), com o mesmo saldo repetido em cada nível.
Só a **folha** — conta publicada sem filha publicada — vira `Registro`; somar a hierarquia contaria
a mesma conta várias vezes. O valor publicado é a posição (PL deficitário vem negativo); o motor
soma saldo, então a posição vira lançamento na direção da conta. O atributo F/P não vem por conta,
só nos totais `AtivoFinanceiro`… (change `bp-anterior-publicado-siconfi`, D1).
"""
from __future__ import annotations

import re
from decimal import Decimal

from app.domain.bo.modelo import Registro

# `P1.1.1.1.2.00.00`; algumas contas vêm com sufixo (`P6.3.1.1.0.00.00BP`). `P` + dígito exclui
# `PassivoFinanceiro`, `PassivoPermanente`.
_CONTA = re.compile(r"^P(\d+(?:\.\d+)*)")
CENTAVO = Decimal("0.01")

TOTAIS_FP = ("AtivoFinanceiro", "AtivoPermanente", "PassivoFinanceiro", "PassivoPermanente",
             "SaldoPatrimonial")


class DirecaoDoPublicado:
    """Direção do saldo para a conta publicada, que nem sempre é folha do PCASP.

    O `I-AB` publica `1.1.2.9.1.00.00` (`112910000`), que o PCASP não lista — só as contas de 7º
    nível. Sem direção exata, vale a do grupo sob o prefixo da conta. Sem isso, o motor reportaria
    a célula inteira como sem natureza de saldo.
    """

    def __init__(self, base):
        self._base = base

    def credora(self, conta: str) -> bool | None:
        direta = self._base.credora(conta)
        # ponytail: `rstrip("0")` também come zero real de nível de 2 dígitos (`…10`); o prefixo
        # fica mais largo, e a direção do grupo é a mesma.
        return direta if direta is not None else self._base.credora_prefixo(conta.rstrip("0"))

    def credora_prefixo(self, prefixo: str) -> bool | None:
        return self._base.credora_prefixo(prefixo)


def _valor(item: dict) -> Decimal:
    return Decimal(str(item["valor"])).quantize(CENTAVO)


def contas_publicadas(itens: list[dict]) -> dict[tuple[str, ...], Decimal]:
    """`cod_conta` do PCASP (partes da máscara) → valor publicado. Não-PCASP fica de fora."""
    contas: dict[tuple[str, ...], Decimal] = {}
    for item in itens:
        achado = _CONTA.match(str(item.get("cod_conta") or ""))
        if achado:
            contas.setdefault(tuple(achado.group(1).split(".")), _valor(item))
    return contas


def _chave(partes: tuple[str, ...]) -> tuple[str, ...]:
    """A conta sem os níveis zerados do fim: `1.1.3.8.0.00.00` → `1.1.3.8`."""
    fim = len(partes)
    while fim > 1 and not partes[fim - 1].strip("0"):
        fim -= 1
    return partes[:fim]


def folhas(contas: dict[tuple[str, ...], Decimal]) -> dict[tuple[str, ...], Decimal]:
    """Contas sem filha publicada. Filha é a que tem a chave da conta como prefixo próprio."""
    com_filha = {chave[:i] for chave in map(_chave, contas) for i in range(1, len(chave))}
    return {partes: valor for partes, valor in contas.items() if _chave(partes) not in com_filha}


def efeito_no_grupo(partes: tuple[str, ...], valor: Decimal, direcao) -> tuple[Decimal, bool]:
    """Quanto a conta publicada soma ao seu grupo, e se o grupo é credor.

    O `I-AB` não tem convenção única de sinal para a conta redutora: a `(-) Ajuste de Perdas`
    (credora no Ativo) sai positiva, e a `2.2.7.2.2` (devedora no Passivo) sai negativa — medido em
    João Pessoa 2024. Nas duas o efeito é reduzir o grupo, então conta de natureza oposta à do
    grupo vale `−|valor|`. Conta de mesma natureza mantém o sinal (PL deficitário sai negativo).
    """
    credora = direcao.credora("".join(partes))
    if partes[0] in ("1", "2"):
        grupo_credor = partes[0] == "2"
        if credora is not None and credora != grupo_credor:
            return -abs(valor), grupo_credor
        return valor, grupo_credor
    return valor, bool(credora)       # classe 6: sem grupo de classe, vale a própria conta


def registros_publicados(itens: list[dict], direcao) -> list[Registro]:
    """Folhas `P*` do `I-AB` como `Registro`: o efeito no grupo vira lançamento, em valor absoluto.

    Conta sem direção no PCASP segue a do grupo; o motor a reporta não apurada, que é a regra.
    """
    registros = []
    for partes, valor in folhas(contas_publicadas(itens)).items():
        efeito, grupo_credor = efeito_no_grupo(partes, valor, direcao)
        natureza = "C" if (efeito >= 0) == grupo_credor else "D"
        registros.append(Registro(conta="".join(partes), natureza=natureza, valor=abs(efeito)))
    return registros


def totais_fp(itens: list[dict]) -> dict[str, Decimal]:
    """`AtivoFinanceiro`, `AtivoPermanente`, `PassivoFinanceiro`, `PassivoPermanente` e
    `SaldoPatrimonial`, quando publicados."""
    return {str(item["cod_conta"]): _valor(item) for item in itens
            if item.get("cod_conta") in TOTAIS_FP}
