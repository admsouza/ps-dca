"""Apuração da matriz — três passos, nesta ordem.

    (a) células     contas da coluna × filtros da linha
    (b) agregações  linhas compostas, coluna a coluna, em ordem topológica — e, na mesma passagem,
                    a guarda condicional da linha, para que quem a agregar já leia o estado final
    (c) derivadas   colunas calculadas de outras colunas da mesma linha

Derivadas **depois** das agregações mantém `saldo = c − b` verdadeira também nos totais por
construção, e não por conferência posterior. Por isso o passo (b) ignora as colunas derivadas:
somá-las das filhas daria o mesmo número em quase todo caso, mas seria coincidência aritmética,
não garantia — e propagaria `None` de uma filha para um total que sabe se calcular sozinho.
"""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app.domain.bo.modelo import Linha, MapaBO, Matriz, NaoApurada, RefColuna, Registro
from app.domain.bo.saldo import atende, excluido, saldo_da_celula

ZERO = Decimal("0.00")


class CicloDeDependencia(RuntimeError):
    """Referências circulares entre linhas. Aborta sem produzir matriz parcial."""


def apurar(mapa: MapaBO, registros: Sequence[Registro], direcao) -> Matriz:
    matriz = Matriz(vigencia=mapa.vigencia)
    linhas = mapa.por_id()
    ordem = _ordem_topologica(linhas)
    derivadas = _catalogo_de_derivadas(mapa)

    for linha in mapa.linhas:                                   # (a)
        if not linha.composta:
            matriz.valores[linha.id] = _celulas(linha, registros, direcao, matriz, derivadas)

    for rule_id in ordem:                                       # (b)
        linha = linhas[rule_id]
        if linha.composta:
            matriz.valores[rule_id] = _agregar(linha, matriz, derivadas)
        if linha.condicao:
            _aplicar_condicao(linha, matriz)   # antes de quem a agrega ler o valor

    for linha in mapa.linhas:                                   # (c)
        _derivar(linha, matriz, derivadas)

    return matriz


def _catalogo_de_derivadas(mapa: MapaBO) -> dict[str, tuple[RefColuna, ...]]:
    """Coluna derivada -> como calculá-la.

    A definição vem das linhas que declaram colunas; as compostas herdam pelo nome da coluna,
    já que o IPC não repete a fórmula do `saldo` em cada total.
    """
    catalogo: dict[str, tuple[RefColuna, ...]] = {}
    for linha in mapa.linhas:
        for coluna in linha.colunas:
            if coluna.derivada and coluna.id not in catalogo:
                catalogo[coluna.id] = coluna.derivada
    return catalogo


# ─── (a) células ─────────────────────────────────────────────────────────────

def _celulas(linha: Linha, registros: Sequence[Registro], direcao, matriz: Matriz,
             derivadas: dict) -> dict[str, Decimal | None]:
    if not linha.colunas:
        return {}   # linha sem coluna de valor (B6, caso L51) — nem zero, nem aviso

    elegiveis = [
        r for r in registros
        if atende(r, linha.filtros) and not excluido(r, linha.exclusoes)
    ]

    celulas: dict[str, Decimal | None] = {}
    for coluna in linha.colunas:
        if coluna.derivada:
            celulas[coluna.id] = None   # preenchida no passo (c)
            continue
        valor, pendencias = saldo_da_celula(elegiveis, coluna.contas, direcao)
        celulas[coluna.id] = valor
        for conta, motivo in pendencias:
            matriz.nao_apuradas.append(NaoApurada(linha.id, coluna.id, conta, motivo))
    return celulas


# ─── (b) agregações ──────────────────────────────────────────────────────────

def _agregar(linha: Linha, matriz: Matriz, derivadas: dict) -> dict[str, Decimal | None]:
    resultado: dict[str, Decimal | None] = {}
    colunas = _colunas_das_filhas(linha, matriz)

    if not colunas and linha.referencias:
        matriz.nao_apuradas.append(NaoApurada(
            linha.id, "-", "-",
            "referências sem coluna em comum — o IPC 07 não diz em qual coluna a linha "
            "cruzada entre receita e despesa é apresentada (pendência C5)",
        ))
        return {}

    for coluna in colunas:
        if coluna in derivadas:
            resultado[coluna] = None    # o passo (c) calcula, sobre os próprios totais
            continue
        total = ZERO
        indeterminada = False
        for referencia in linha.referencias:
            valores = matriz.valores.get(referencia.regra) or {}
            lida = referencia.coluna or coluna
            if lida not in valores:
                continue                # a linha não declara a coluna: a parcela não existe
            parcela = valores[lida]
            if parcela is None:
                if (referencia.regra, lida) in matriz.suprimidas:
                    continue            # suprimida pela condição: contribui zero
                indeterminada = True    # não apurada: `None` não é zero, propaga
                break
            total += parcela if referencia.sinal == "+" else -parcela
        resultado[coluna] = None if indeterminada else total
        if indeterminada:
            matriz.nao_apuradas.append(
                NaoApurada(linha.id, coluna, "-", "agregação de célula não apurada")
            )
    return resultado


def _colunas_das_filhas(linha: Linha, matriz: Matriz) -> list[str]:
    """Colunas que a linha composta pode agregar: as presentes em **todas** as referências.

    Interseção, não união, para quem não declara: somar por união produziria coluna com uma
    parcela só, passando por total.

    As linhas que cruzam receita e despesa — `L25`, `L26`, `L49`, `L50` — **declaram** suas
    colunas, medidas no publicado do STN, e por isso não passam pela interseção. Interseção vazia
    em linha que não declara segue reportada como pendência.
    """
    if linha.colunas:
        return [c.id for c in linha.colunas]

    conjuntos = [
        list(matriz.valores.get(referencia.regra) or {}) for referencia in linha.referencias
    ]
    if not conjuntos:
        return []
    comuns = set(conjuntos[0]).intersection(*(set(c) for c in conjuntos[1:]))
    return [coluna for coluna in conjuntos[0] if coluna in comuns]


# ─── (c) derivadas ───────────────────────────────────────────────────────────

def _derivar(linha: Linha, matriz: Matriz, derivadas: dict) -> None:
    celulas = matriz.valores.get(linha.id)
    if not celulas:
        return
    for coluna, referencias in derivadas.items():
        if coluna not in celulas:
            continue
        total = ZERO
        indeterminada = False
        for referencia in referencias:
            parcela = celulas.get(referencia.coluna)
            if parcela is None:
                indeterminada = True
                break
            total += parcela if referencia.sinal == "+" else -parcela
        celulas[coluna] = None if indeterminada else total


# ─── condição de apresentação ────────────────────────────────────────────────

def _aplicar_condicao(linha: Linha, matriz: Matriz) -> None:
    """Déficit e superávit só aparecem quando a condição vale — e nunca os dois juntos.

    A célula suprimida vira `None` na apresentação e entra em `matriz.suprimidas`. É o conjunto
    que permite ao total que a agrega somar **zero** em vez de propagar indeterminação: medido, o
    STN publica `TotalDespesasComSuperavit` mesmo em ente deficitário, onde `Superavit` fica em
    branco.
    """
    celulas = matriz.valores.get(linha.id) or {}

    def suprimir(coluna: str) -> None:
        celulas[coluna] = None
        matriz.suprimidas.add((linha.id, coluna))

    def vale(valor: Decimal) -> bool:
        positivo = valor > 0
        return positivo if linha.condicao == "result_positive" else not positivo

    if linha.condicao_coluna:
        # O resultado orçamentário é decidido **uma vez**, na coluna declarada, e vale para a
        # linha inteira. Medido em São Paulo 2025: déficit contra a empenhada e superávit contra
        # liquidadas e pagas, e o STN deixa `Superavit` em branco nas três. Decidir célula a
        # célula publicaria as duas outras.
        decisor = celulas.get(linha.condicao_coluna)
        if decisor is None or not vale(decisor):
            for coluna in list(celulas):
                if celulas[coluna] is not None:
                    suprimir(coluna)
        return

    for coluna, valor in list(celulas.items()):
        if valor is not None and not vale(valor):
            suprimir(coluna)


# ─── ordem topológica ────────────────────────────────────────────────────────

def _ordem_topologica(linhas: dict[str, Linha]) -> list[str]:
    ordem: list[str] = []
    estado: dict[str, int] = {}    # 0 = não visto, 1 = na pilha, 2 = fechado
    pilha: list[str] = []

    def visitar(rule_id: str) -> None:
        estado[rule_id] = 1
        pilha.append(rule_id)
        for referencia in linhas[rule_id].referencias:
            alvo = referencia.regra
            if alvo not in linhas:
                continue
            if estado.get(alvo, 0) == 1:
                caminho = pilha[pilha.index(alvo):] + [alvo]
                raise CicloDeDependencia("dependência circular: " + " → ".join(caminho))
            if estado.get(alvo, 0) == 0:
                visitar(alvo)
        pilha.pop()
        estado[rule_id] = 2
        ordem.append(rule_id)

    for rule_id in linhas:
        if estado.get(rule_id, 0) == 0:
            visitar(rule_id)
    return ordem
