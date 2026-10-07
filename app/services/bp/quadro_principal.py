"""Apuração do Balanço Patrimonial — IPC 04, ed. 2020-01.

Mesmo fluxo do BO e do BF: síncrono, puro, a mesma função serve à rota, ao worker e ao CLI. O BP é
o mais simples dos três — uma leitura só, `MSCE`/encerramento, no exercício e no anterior.

O que é próprio do BP (change `bp-apuracao-f1`, medido em `docs/evidencia-bp-fp-2025.md`):

1. **Direção do saldo pela coluna** (critério do BO, D2c): as redutoras ficam dentro do grupo —
   depreciação `1.2.3.8` dentro de `1.2.3` — e pela direção da própria conta somariam.
2. **Atributo F/P do fato**, por termo de conta (D2). Fato sem atributo numa conta coberta por termo
   qualificado não entra: é resíduo. Fonte sem atributo nenhum deixa o quadro F/P `None`.
3. **Conta mista assume a direção da classe**: `2.3.4` e `2.3.7` são `Credora/Devedora` no PCASP, e
   o BP apresenta o PL credor — déficit acumulado sai negativo, como Cuitegi publica. Conta fora
   do PCASP continua não apurada.
4. **Linha `review_required` é parcela inexistente** (D2b): `None` com o bloqueio no diagnóstico, e
   o total soma as demais. Total cujas parcelas são todas bloqueadas também é `None`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from decimal import Decimal

from app.domain.bo.matriz import apurar as apurar_matriz
from app.domain.bo.matriz import ordem_topologica
from app.domain.bo.modelo import MapaBO, NaoApurada, Registro, Residuo
from app.domain.bo.saldo import _casa, saldo_da_conta
from app.infra.msc.fonte import COMPETENCIA_DE_ENCERRAMENTO, fonte_de
from app.infra.pcasp.natureza import do_pcasp
from app.infra.regras.carregador import carregar_em_cache

DEMONSTRATIVO = "BP"
COLUNA_ATUAL = "exercicio_atual"
COLUNA_ANTERIOR = "exercicio_anterior"
QUADRO_PRINCIPAL = "QUADRO_PRINCIPAL"
SEM_ATRIBUTO = "a MSC não traz o atributo financeiro/permanente em nenhum fato (IPC 04, P4)"
TODAS_BLOQUEADAS = "todas as parcelas são não apuráveis"

POLICIES_NAO_APLICADAS = (
    "itens 8 e 9 (intraorçamentárias de 5º nível = 2 criadas pelo ente): declarados, não "
    "executados (P6-a); as exclusões explícitas de cada linha continuam aplicadas",
)


@dataclass(frozen=True)
class Procedencia:
    documento: str
    edicao: str
    exercicio: int
    versao_regras: str
    regras_aplicadas: int
    tabelas_stn: dict[str, str] = field(default_factory=dict)
    matriz: str = ""
    tipo_saldo: str = ""
    competencia: int = COMPETENCIA_DE_ENCERRAMENTO
    classes: tuple[int, ...] = ()


@dataclass
class Diagnostico:
    nao_apuradas: list[NaoApurada] = field(default_factory=list)
    residuos: list[Residuo] = field(default_factory=list)
    # `L1 − L15` do quadro principal, por coluna. Diferença é achado, nunca ajuste.
    equilibrio: dict[str, Decimal] = field(default_factory=dict)
    duracao_ms: int = 0
    sem_dados: bool = False
    sem_dados_exercicio_anterior: bool = False
    sem_atributo_fp: bool = False
    policies_nao_aplicadas: tuple[str, ...] = POLICIES_NAO_APLICADAS


@dataclass
class Resultado:
    matriz: dict[str, dict[str, Decimal | None]]
    procedencia: Procedencia
    diagnostico: Diagnostico
    mapa: MapaBO | None = None


@dataclass
class _Coluna:
    valores: dict[str, Decimal | None]
    nao_apuradas: list[NaoApurada]
    residuos: list[Residuo]
    sem_dados: bool
    sem_atributo_fp: bool


def apurar(ente: int, exercicio: int, fonte, direcao=None, mapa: MapaBO | None = None,
           competencia: int = COMPETENCIA_DE_ENCERRAMENTO) -> Resultado:
    """Apura os quatro quadros do BP, nas duas colunas."""
    inicio = time.monotonic()
    mapa = mapa or carregar_em_cache(exercicio, demonstrativo="bp")
    direcao = _DirecaoDoBP(direcao or do_pcasp())
    origem = fonte_de(DEMONSTRATIVO, competencia)

    atual = _apurar_exercicio(mapa, ente, exercicio, competencia, fonte, direcao, origem,
                              COLUNA_ATUAL)
    anterior = _apurar_exercicio(mapa, ente, exercicio - 1, competencia, fonte, direcao, origem,
                                 COLUNA_ANTERIOR)
    matriz = {
        linha.id: {COLUNA_ATUAL: atual.valores[linha.id],
                   COLUNA_ANTERIOR: anterior.valores[linha.id]}
        for linha in mapa.linhas
    }

    return Resultado(
        mapa=mapa,
        matriz=matriz,
        procedencia=Procedencia(
            documento=mapa.vigencia.documento,
            edicao=mapa.vigencia.edicao,
            exercicio=exercicio,
            versao_regras=mapa.versao_regras,
            regras_aplicadas=len(mapa.linhas),
            tabelas_stn=dict(mapa.tabelas_stn),
            matriz=str(origem.matriz),
            tipo_saldo=str(origem.tipo_saldo),
            competencia=competencia,
            classes=origem.classes,
        ),
        diagnostico=Diagnostico(
            nao_apuradas=atual.nao_apuradas + anterior.nao_apuradas,
            residuos=atual.residuos,
            equilibrio=_equilibrio(mapa, matriz),
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            sem_dados=atual.sem_dados,
            sem_dados_exercicio_anterior=anterior.sem_dados,
            sem_atributo_fp=atual.sem_atributo_fp or anterior.sem_atributo_fp,
        ),
    )


def _apurar_exercicio(mapa: MapaBO, ente, exercicio, competencia, fonte, direcao, origem,
                      coluna: str) -> _Coluna:
    """Uma coluna: a `exercicio_atual` do exercício pedido, publicada sob o nome `coluna`."""
    registros: list[Registro] = [
        registro for classe in origem.classes for registro in fonte.registros(
            ente=ente, ano=exercicio, mes=competencia, classe=classe,
            matriz=origem.matriz, tipo_saldo=origem.tipo_saldo,
        )
    ]
    if not registros:
        # Sem leitura (auditoria pendente → 409 → vazio) não há posição: `None`, nunca zero.
        return _Coluna({linha.id: None for linha in mapa.linhas}, [], [], True, False)

    qualificados = _termos_qualificados(mapa)
    cobertos = [r for r in registros if any(_casa(r.conta, cc) for cc in qualificados)]
    sem_atributo = bool(cobertos) and not any(r.financeiro_permanente for r in cobertos)

    bloqueadas = {linha.id: linha.bloqueio for linha in mapa.linhas if linha.bloqueio}
    if sem_atributo:
        bloqueadas.update({linha.id: SEM_ATRIBUTO for linha in mapa.linhas
                           if _qualificada(linha)})

    # Linha bloqueada é apurada sem contas: soma zero no total, e sai `None` abaixo (D5 do BF).
    apuravel = replace(mapa, linhas=tuple(
        linha._replace(colunas=tuple(c._replace(contas=()) for c in linha.colunas))
        if linha.id in bloqueadas else linha
        for linha in mapa.linhas
    ))
    calculada = apurar_matriz(apuravel, registros, direcao)

    valores = {rule_id: celulas.get(COLUNA_ATUAL)
               for rule_id, celulas in calculada.valores.items()}
    nao_apuradas = [n._replace(coluna=coluna) for n in calculada.nao_apuradas
                    if n.coluna in (COLUNA_ATUAL, "-")]

    linhas = mapa.por_id()
    for rule_id in ordem_topologica(linhas):
        linha = linhas[rule_id]
        if linha.referencias and all(r.regra in bloqueadas for r in linha.referencias):
            bloqueadas[rule_id] = TODAS_BLOQUEADAS
    for rule_id, motivo in bloqueadas.items():
        valores[rule_id] = None
        nao_apuradas.append(NaoApurada(rule_id, coluna, "-", motivo))

    residuos = [] if sem_atributo else _residuos_fp(cobertos, direcao)
    return _Coluna(valores, nao_apuradas, residuos, False, sem_atributo)


class _DirecaoDoBP:
    """PCASP com a conta mista resolvida pela direção da classe (`2` → credora)."""

    def __init__(self, base):
        self._base = base

    def credora(self, conta: str) -> bool | None:
        return self._resolver(conta, self._base.credora(conta))

    def credora_prefixo(self, prefixo: str) -> bool | None:
        return self._resolver(prefixo, self._base.credora_prefixo(prefixo))

    def _resolver(self, codigo: str, direta: bool | None) -> bool | None:
        mista = getattr(self._base, "mista", None)
        if direta is not None or mista is None or not mista(codigo):
            return direta
        return self._base.credora_prefixo(codigo[:1])


def _termos_qualificados(mapa: MapaBO) -> set[str]:
    return {conta.cc for linha in mapa.linhas for coluna in linha.colunas
            for conta in coluna.contas if conta.financeiro_permanente}


def _qualificada(linha) -> bool:
    return any(conta.financeiro_permanente for coluna in linha.colunas for conta in coluna.contas)


def _residuos_fp(cobertos: list[Registro], direcao) -> list[Residuo]:
    """Fato sem atributo F/P numa conta que o quadro qualifica: declarado, nunca classificado."""
    total = Decimal("0.00")
    for registro in cobertos:
        if registro.financeiro_permanente in ("F", "P"):
            continue
        total += saldo_da_conta([registro], bool(direcao.credora(registro.conta)))
    return [Residuo("financeiro_permanente", "(sem atributo na MSC)", total)] if total else []


def _equilibrio(mapa: MapaBO, matriz: dict) -> dict[str, Decimal]:
    """`L1 ATIVO − L15 PASSIVO E PATRIMÔNIO LÍQUIDO`, por coluna."""
    por_codigo = {linha.codigo: linha.id for linha in mapa.linhas
                  if linha.quadro == QUADRO_PRINCIPAL}
    ativo, passivo = por_codigo.get("L1"), por_codigo.get("L15")
    if ativo is None or passivo is None:
        return {}
    saida: dict[str, Decimal] = {}
    for coluna in (COLUNA_ATUAL, COLUNA_ANTERIOR):
        a, p = matriz[ativo][coluna], matriz[passivo][coluna]
        if a is not None and p is not None:
            saida[coluna] = a - p
    return saida
