"""Saldo de conta e de célula.

A regra, medida contra o STN em João Pessoa 12/2025 (`docs/validacao-bo-jp-2025.md`):

    saldo(conta) = Σ C − Σ D   se a conta é credora no PCASP
                 = Σ D − Σ C   se a conta é devedora no PCASP

A direção vem da tabela, **por conta folha do registro** — nunca da classe contábil, nunca do
prefixo declarado na regra, nunca do campo `natureza` do lançamento. Este módulo não conhece
nenhum conjunto de classes credoras, e o teste
`test_heuristica_de_classe_e_rejeitada` falha se alguém introduzir um: a heurística
`{2,6,8}` do `regras-rgf-api` inverte o sinal de 29 contas das classes 5 e 6.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal

from app.domain.bo.modelo import ContaCC, Filtro, Registro

ZERO = Decimal("0.00")


def saldo_da_conta(registros: Iterable[Registro], credora: bool) -> Decimal:
    """`Σ C − Σ D` para conta credora; `Σ D − Σ C` para devedora."""
    creditos = sum((r.valor for r in registros if r.natureza == "C"), ZERO)
    debitos = sum((r.valor for r in registros if r.natureza == "D"), ZERO)
    return creditos - debitos if credora else debitos - creditos


def atende(registro: Registro, filtros: Sequence[Filtro]) -> bool:
    """Todos os filtros valem em conjunto (E lógico)."""
    return all(_atende_um(registro, filtro) for filtro in filtros)


def _atende_um(registro: Registro, filtro: Filtro) -> bool:
    valor = _campo(registro, filtro.campo)
    casou = any(_casa(valor, padrao) for padrao in filtro.valores)
    return casou if filtro.operador == "in" else not casou


def excluido(registro: Registro, grupos: Sequence[Sequence[Filtro]]) -> bool:
    """Verdadeiro se o registro cai em **algum** grupo de exclusão, inteiro.

    Cada grupo é uma combinação independente (D2): achatar os grupos numa lista só excluiria o
    produto cartesiano, mais do que o IPC 07 manda em `L38`.
    """
    return any(
        grupo and all(_casa_no_grupo(registro, filtro) for filtro in grupo)
        for grupo in grupos
    )


def _casa_no_grupo(registro: Registro, filtro: Filtro) -> bool:
    valor = _campo(registro, filtro.campo)
    return any(_casa(valor, padrao) for padrao in filtro.valores)


def _campo(registro: Registro, nome: str) -> str:
    if nome == "conta_contabil":
        return registro.conta
    return getattr(registro, nome, "") or ""


def _casa(valor: str, padrao: str) -> bool:
    """Casamento por prefixo sobre os dígitos, com `x` como coringa de um dígito."""
    digitos = "".join(c for c in valor if c.isdigit())
    if not padrao:
        return False
    if "x" in padrao.lower():
        alvo = padrao.lower()
        if len(digitos) < len(alvo):
            return False
        pares = zip(alvo, digitos[: len(alvo)], strict=True)
        return all(p in ("x", d) for p, d in pares)
    return digitos.startswith(padrao)


def saldo_da_celula(
    registros: Sequence[Registro],
    contas: Sequence[ContaCC],
    direcao,
) -> tuple[Decimal | None, list[tuple[str, str]]]:
    """Soma `operacao × saldo(conta)` sobre as contas declaradas na coluna.

    O saldo de cada registro é tomado **na direção da coluna**, não na da própria conta. É o que
    faz a conta redutora reduzir: no PCASP ela tem natureza oposta à do grupo e `(-)` no título
    — a conta de redução de dotação é credora entre devedoras, e a de dedução do FUNDEB é
    devedora entre credoras. Somar cada uma na direção dela devolveria a redutora positiva,
    inflando a coluna.

    Devolve `(valor, pendencias)`. Direção desconhecida torna a **célula inteira** não apurada —
    `None`, nunca `0`: zero é valor legítimo do demonstrativo, e usá-lo para "não sei" apagaria
    a diferença entre conta sem escrituração e conta sem direção conhecida.
    """
    total = ZERO
    pendencias: list[tuple[str, str]] = []

    credora_da_coluna = _direcao_da_coluna(contas, direcao)
    if credora_da_coluna is None and contas:
        return None, [(contas[0].cc, "direção da coluna indeterminada no PCASP e na regra")]

    for conta in contas:
        casados = [r for r in registros if _casa(r.conta, conta.cc)]
        if not casados:
            # Conta declarada sem escrituração no período contribui zero. Não é "não sei":
            # `5.2.2.1.9` é declarada pelo IPC e pode não ter movimento no exercício.
            continue
        desconhecidas = [r.conta for r in casados if direcao.credora(r.conta) is None]
        if desconhecidas:
            pendencias.append((desconhecidas[0], "sem natureza de saldo no PCASP nem na regra"))
            continue
        parcial = saldo_da_conta(casados, credora_da_coluna)
        total += parcial if conta.operacao == "+" else -parcial

    return (None if pendencias else total), pendencias


def _direcao_da_coluna(contas: Sequence[ContaCC], direcao) -> bool | None:
    """Direção do grupo, dada pela primeira conta declarada que a tabela souber resolver."""
    for conta in contas:
        prefixo = getattr(direcao, "credora_prefixo", None)
        resolvida = prefixo(conta.cc) if prefixo else direcao.credora(conta.cc)
        if resolvida is not None:
            return resolvida
    return None
