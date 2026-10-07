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
    casou = any(_casa_no_campo(filtro.campo, valor, padrao) for padrao in filtro.valores)
    return casou if filtro.operador == "in" else not casou


def _casa_no_campo(campo: str, valor: str, padrao: str) -> bool:
    """Fonte de recursos casa por **igualdade**; os demais campos, por prefixo.

    Medido (G1): a fonte do IPC 06 tem 3 dígitos e é um código completo, não um prefixo — a
    fonte `500` não pode ser capturada por um padrão `50`, que pegaria também `501`, `502` e
    `503`, cada uma de uma linha diferente do demonstrativo.
    """
    if campo == "fonte_recurso":
        return bool(valor) and valor == padrao
    return _casa(valor, padrao)


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
    if nome == "fonte_recurso":
        return _fonte_do_ipc(registro.fonte_recursos)
    return getattr(registro, nome, "") or ""


def _fonte_do_ipc(fonte: str) -> str:
    """Os 3 dígitos que o IPC 06 declara, a partir dos 4 que a MSC entrega.

    O 1º dígito da fonte escriturada é o **exercício da vinculação** (`1500` é a fonte `500`);
    o detalhamento do ente vai em coluna separada. Medido em 2026-09-18 nos 5 entes de
    homologação: com o corte, `L1 = L2 + L3 + L11` fecha em 0,00 e o resíduo de fonte é zero;
    sem ele, **nenhuma** das 22 linhas por fonte casaria — e sairiam zeradas, sem erro.
    """
    digitos = "".join(c for c in fonte if c.isdigit())
    return digitos[1:4] if len(digitos) == 4 else digitos


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
        casados = _do_termo(registros, conta)
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


def saldo_da_celula_por_conta(
    registros: Sequence[Registro],
    contas: Sequence[ContaCC],
    direcao,
) -> tuple[Decimal | None, list[tuple[str, str]]]:
    """Como `saldo_da_celula`, mas cada conta entra na direção **dela**, não na da coluna.

    É o critério do BF (G7), medido em 3 entes: com a direção da coluna, `L1` de Recife sai
    5.872.854.713,27; com a direção por conta, sai 10.390.050.823,18 — o valor que o ente
    declarou no RREO. A redutora continua reduzindo porque a própria regra do IPC 06 traz o
    sinal do par (`6.2.1.2 (+)` / `6.2.1.3 (−)`), o que no BO vinha da direção do grupo.
    """
    total = ZERO
    pendencias: list[tuple[str, str]] = []

    for conta in contas:
        casados = _do_termo(registros, conta)
        if not casados:
            continue                      # conta declarada sem escrituração contribui zero
        por_folha: dict[str, list[Registro]] = {}
        for registro in casados:
            por_folha.setdefault(registro.conta, []).append(registro)

        parcial, indeterminada = ZERO, False
        for folha, registros_da_folha in por_folha.items():
            credora = direcao.credora(folha)
            if credora is None:
                pendencias.append((folha, "sem natureza de saldo no PCASP nem na regra"))
                indeterminada = True
                break
            parcial += saldo_da_conta(registros_da_folha, credora)
        if indeterminada:
            continue
        total += parcial if conta.operacao == "+" else -parcial

    return (None if pendencias else total), pendencias


def soma_da_celula_por_natureza(
    registros: Sequence[Registro], contas: Sequence[ContaCC], natureza: str,
) -> tuple[Decimal, list[tuple[str, str]]]:
    """Soma só os lançamentos de `natureza` ("C" ou "D") das contas, sem subtrair o lado oposto.

    Usado por L28/L61 (proposal `bf-l28-l61-contas-especificas`): não lê a natureza da conta no
    PCASP, só a do lançamento — por isso nunca gera pendência de direção.
    """
    total = ZERO
    for conta in contas:
        casados = [r for r in registros if _casa(r.conta, conta.cc) and r.natureza == natureza]
        parcial = sum((r.valor for r in casados), ZERO)
        total += parcial if conta.operacao == "+" else -parcial
    return total, []


def _do_termo(registros: Sequence[Registro], conta: ContaCC) -> list[Registro]:
    """Registros da conta; com atributo F/P no termo, só os fatos com o mesmo atributo (IPC 04)."""
    return [r for r in registros if _casa(r.conta, conta.cc)
            and (not conta.financeiro_permanente
                 or r.financeiro_permanente == conta.financeiro_permanente)]


def _direcao_da_coluna(contas: Sequence[ContaCC], direcao) -> bool | None:
    """Direção do grupo, dada pela primeira conta declarada que a tabela souber resolver."""
    for conta in contas:
        prefixo = getattr(direcao, "credora_prefixo", None)
        resolvida = prefixo(conta.cc) if prefixo else direcao.credora(conta.cc)
        if resolvida is not None:
            return resolvida
    return None
