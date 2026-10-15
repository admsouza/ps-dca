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
4. **Coluna anterior de duas origens** (`bp-anterior-publicado-siconfi`): `publicado_siconfi`
   (padrão) apura as contas folha do `DCA-Anexo I-AB` do ano anterior pelas mesmas regras; a
   `msce_exercicio_anterior` lê a MSC como sempre. Sem `I-AB`, a coluna é `None` — nunca a MSC.
5. **Linha `review_required` é parcela inexistente** (D2b): `None` com o bloqueio no diagnóstico, e
   o total soma as demais. Total cujas parcelas são todas bloqueadas também é `None`.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import StrEnum

from app.domain.bo.matriz import apurar as apurar_matriz
from app.domain.bo.matriz import ordem_topologica
from app.domain.bo.modelo import Linha, MapaBO, NaoApurada, RefLinha, Registro, Residuo
from app.domain.bo.saldo import _casa, saldo_da_conta
from app.infra.msc.fonte import COMPETENCIA_DE_ENCERRAMENTO, fonte_de
from app.infra.pcasp.natureza import do_pcasp
from app.infra.regras.carregador import carregar_em_cache
from app.services.bp.fontes import rotulo_fonte
from app.services.bp.informados import partir as _partir_informados
from app.services.bp.publicado import DirecaoDoPublicado, registros_publicados, totais_fp

DEMONSTRATIVO = "BP"
COLUNA_ATUAL = "exercicio_atual"
COLUNA_ANTERIOR = "exercicio_anterior"
QUADRO_PRINCIPAL = "QUADRO_PRINCIPAL"
NAO_INFORMADO = "não informado"
SEM_LINHA_ANTERIOR = "sem linha no exercício anterior"
SEM_VALOR_ANTERIOR = "não apurada no exercício anterior"
SEM_ATRIBUTO = "a MSC não traz o atributo financeiro/permanente em nenhum fato (IPC 04, P4)"
TODAS_BLOQUEADAS = "todas as parcelas são não apuráveis"

# Quadro F/P: o `I-AB` publica estes totais, e o atributo F/P não vem por conta.
FP_PUBLICADO = {"L2": "AtivoFinanceiro", "L3": "AtivoPermanente",
                "L5": "PassivoFinanceiro", "L6": "PassivoPermanente"}
QUADRO_FP = "ATIVOS_PASSIVOS_FINANCEIROS"
NAO_PUBLICADO = "total F/P não publicado no I-AB"
QUADRO_SUPERAVIT = "SUPERAVIT_DEFICIT"
CONTAS_SUPERAVIT = ("821110100", "821110200")


class Anterior(StrEnum):
    """De onde vem a coluna do exercício anterior."""

    PUBLICADO = "publicado_siconfi"
    MSCE = "msce_exercicio_anterior"
    PROCESSADO = "processado_exercicio_anterior"     # a coluna pronta, do cache de N−1
    MANUAL = "manual"                                # `P:`/`FP:`/`C:`/`S:`, só por unidade


CONSOLIDADO = "consolidado"

POLICIES_NAO_APLICADAS = (
    "item 9 (intraorçamentárias de 5º nível = 2 criadas pelo ente): declarado, não "
    "executado (P6-a); as exclusões do item 8 valem só na visão consolidada",
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
    origem_exercicio_anterior: str = Anterior.PUBLICADO.value
    # Mapa informado, como chegou: o pedido seguinte reaplica (`pipeline-anterior-por-recorte`).
    valores_anteriores: dict[str, str] | None = None
    escolha_anterior: dict | None = None        # escolha explícita da unidade; `null` = padrão
    anterior_processado: dict | None = None     # de que resultado de N−1 veio a coluna


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
    # `I-AB` do ano anterior ausente no `tt/dca`: coluna anterior `None`, sem cair para a MSC.
    sem_publicacao_exercicio_anterior: bool = False
    # `L7` apurado × `SaldoPatrimonial` publicado. Diferença é achado, nunca ajuste.
    conferencia_publicado: dict[str, Decimal | None] | None = None
    # Saldo da 82111 sem código de fonte, por coluna: fora do quadro de superávit e do total.
    fonte_vazia: dict[str, Decimal] = field(default_factory=dict)
    policies_nao_aplicadas: tuple[str, ...] = POLICIES_NAO_APLICADAS


@dataclass
class VisaoBP:
    matriz: dict[str, dict[str, Decimal | None]]
    equilibrio: dict[str, Decimal]


@dataclass
class Resultado:
    """`matriz` e `diagnostico.equilibrio` são os da visão isolada (espelho do `I-AB`)."""

    matriz: dict[str, dict[str, Decimal | None]]
    procedencia: Procedencia
    diagnostico: Diagnostico
    mapa: MapaBO | None = None
    visoes: dict[str, VisaoBP] = field(default_factory=dict)


@dataclass
class _Coluna:
    valores: dict[str, Decimal | None]
    nao_apuradas: list[NaoApurada]
    residuos: list[Residuo]
    sem_dados: bool
    sem_atributo_fp: bool


def apurar(ente: int, exercicio: int, fonte, direcao=None, mapa: MapaBO | None = None,
           competencia: int = COMPETENCIA_DE_ENCERRAMENTO,
           anterior: Anterior = Anterior.PUBLICADO, dca=None,
           anterior_pronto: dict | None = None,
           valores_anteriores: dict[str, str] | None = None,
           zero_sem_anterior: bool = False) -> Resultado:
    """Apura os quatro quadros do BP, nas duas colunas.

    `dca` lê o `I-AB` publicado (`.itens(ente, ano)`); sem ele, o `tt/dca` do SICONFI.
    `anterior_pronto` é a coluna anterior já pronta (`PROCESSADO`, ver `pipeline/anterior.py`);
    `valores_anteriores`, a digitada (`MANUAL`). `zero_sem_anterior`: a unidade sem MSC em N−1,
    num job que leu N−1, sai em zero, e não não apurada.
    """
    inicio = time.monotonic()
    anterior = Anterior(anterior)                # o job chega com string
    mapa = mapa or carregar_em_cache(exercicio, demonstrativo="bp")
    direcao = _DirecaoDoBP(direcao or do_pcasp())
    origem = fonte_de(DEMONSTRATIVO, competencia)

    def da_msc(ano: int) -> list[Registro]:
        return [registro for classe in origem.classes for registro in fonte.registros(
            ente=ente, ano=ano, mes=competencia, classe=classe,
            matriz=origem.matriz, tipo_saldo=origem.tipo_saldo,
        )]

    # A fonte é lida uma vez; as duas visões são apuradas sobre os mesmos registros.
    registros_atual = da_msc(exercicio)
    publicado: list[dict] = []
    registros_anterior: list[Registro] = []
    informado = dict(valores_anteriores or {}) if anterior is Anterior.MANUAL else None
    pronto = anterior_pronto
    por_fonte_manual: dict[str, Decimal] | None = None
    if anterior is Anterior.MANUAL:
        folhas, por_fonte_manual = _partir_informados(informado or {})
        pronto = {"matriz": _totalizar(mapa, folhas)}
    if anterior is Anterior.MSCE:
        registros_anterior = da_msc(exercicio - 1)
    elif pronto is not None:
        pass                                     # nenhuma leitura de N−1
    else:
        if dca is None:
            from app.infra.siconfi.dca import SiconfiDCA
            dca = SiconfiDCA()
        publicado = dca.itens(ente, exercicio - 1)

    def apurar_visao(m: MapaBO) -> tuple[_Coluna, _Coluna, dict]:
        atual = _apurar_exercicio(m, registros_atual, direcao, COLUNA_ATUAL)
        if anterior is Anterior.MSCE:
            anterior_ = _apurar_exercicio(m, registros_anterior, direcao, COLUNA_ANTERIOR,
                                          zero_se_vazio=zero_sem_anterior)
        elif pronto is not None:
            anterior_ = _coluna_pronta(m, pronto["matriz"], NAO_INFORMADO
                                       if anterior is Anterior.MANUAL else SEM_LINHA_ANTERIOR)
        else:
            anterior_ = _apurar_publicado(m, publicado, direcao)
        matriz_ = {
            linha.id: {COLUNA_ATUAL: atual.valores[linha.id],
                       COLUNA_ANTERIOR: anterior_.valores[linha.id]}
            for linha in m.linhas
        }
        return atual, anterior_, matriz_

    # ponytail: as duas visões incluem todas as contas (PO 2026-10-08).
    # Os filtros visao=consolidado ficam na regra e não entram na apuração.
    atual, coluna_anterior, matriz = apurar_visao(_sem_visao(mapa, CONSOLIDADO))
    if pronto is not None:
        saldos_anterior = _saldos_do_pronto(pronto, por_fonte_manual)
    else:
        saldos_anterior = _saldos_por_fonte(
            registros_anterior if anterior is Anterior.MSCE else list(
                fonte.registros(ente=ente, ano=exercicio - 1, mes=competencia, classe=8,
                                matriz=origem.matriz, tipo_saldo=origem.tipo_saldo)))
    mapa, atual, coluna_anterior, fonte_vazia = _superavit(
        mapa, matriz, registros_atual, saldos_anterior, atual, coluna_anterior,
        anterior_informado=anterior is Anterior.MANUAL,
    )
    visoes = {CONSOLIDADO: VisaoBP(matriz, _equilibrio(mapa, matriz))}
    if anterior is Anterior.PROCESSADO and CONSOLIDADO in pronto.get("visoes", {}):
        da_visao = _com_anterior(mapa, matriz, pronto["visoes"][CONSOLIDADO])
        visoes[CONSOLIDADO] = VisaoBP(da_visao, _equilibrio(mapa, da_visao))

    return Resultado(
        mapa=mapa,
        matriz=matriz,
        visoes=visoes,
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
            origem_exercicio_anterior=anterior.value,
            valores_anteriores=informado,
        ),
        diagnostico=Diagnostico(
            nao_apuradas=atual.nao_apuradas + coluna_anterior.nao_apuradas,
            residuos=atual.residuos,
            equilibrio=_equilibrio(mapa, matriz),
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            sem_dados=atual.sem_dados,
            sem_dados_exercicio_anterior=(anterior is Anterior.MSCE and coluna_anterior.sem_dados),
            sem_atributo_fp=atual.sem_atributo_fp or coluna_anterior.sem_atributo_fp,
            sem_publicacao_exercicio_anterior=(anterior is Anterior.PUBLICADO
                                               and coluna_anterior.sem_dados),
            conferencia_publicado=_conferencia(mapa, matriz, publicado),
            fonte_vazia=fonte_vazia,
        ),
    )


def _sem_visao(mapa: MapaBO, visao: str) -> MapaBO:
    """O mapa sem os filtros que só valem na `visao` (a isolada é o mapa sem os consolidados)."""
    return replace(mapa, linhas=tuple(
        linha._replace(filtros=tuple(f for f in linha.filtros if f.visao != visao))
        for linha in mapa.linhas
    ))


def _apurar_publicado(mapa: MapaBO, itens: list[dict], direcao) -> _Coluna:
    """Coluna anterior pelo `I-AB`: folhas pelas regras do IPC 04, F/P pelos totais publicados."""
    registros = registros_publicados(itens, DirecaoDoPublicado(direcao))
    if not registros:
        return _Coluna({linha.id: None for linha in mapa.linhas}, [], [], True, False)
    totais = totais_fp(itens)
    fixos = {linha.id: totais.get(FP_PUBLICADO[linha.codigo])
             for linha in mapa.linhas if linha.quadro == QUADRO_FP and linha.codigo in FP_PUBLICADO}
    return _apurar_exercicio(mapa, registros, DirecaoDoPublicado(direcao), COLUNA_ANTERIOR, fixos)


def _conferencia(mapa: MapaBO, matriz: dict, itens: list[dict]) -> dict | None:
    """`L7` apurado pelo publicado × `SaldoPatrimonial` publicado."""
    publicado = totais_fp(itens).get("SaldoPatrimonial")
    l7 = next((linha.id for linha in mapa.linhas
               if linha.quadro == QUADRO_FP and linha.codigo == "L7"), None)
    if publicado is None or l7 is None:
        return None
    apurado = matriz[l7][COLUNA_ANTERIOR]
    return {"l7_apurado": apurado, "saldo_patrimonial_publicado": publicado,
            "diferenca": None if apurado is None else apurado - publicado}


def _apurar_exercicio(mapa: MapaBO, registros: list[Registro], direcao, coluna: str,
                      fixos: dict[str, Decimal | None] | None = None,
                      zero_se_vazio: bool = False) -> _Coluna:
    """Uma coluna: a `exercicio_atual` das regras sobre `registros`, publicada sob o nome `coluna`.

    `fixos` são as linhas que o publicado traz prontas (F/P `L2`, `L3`, `L5`, `L6`): não passam
    pelo motor, e os totais que as somam são refeitos sobre elas. `zero_se_vazio`: sem registros,
    apura zero e sinaliza `sem_dados` (unidade sem MSC em N−1, num job que leu N−1).
    """
    if not registros and not zero_se_vazio:
        # Sem leitura (auditoria pendente → 409 → vazio) não há posição: `None`, nunca zero.
        return _Coluna({linha.id: None for linha in mapa.linhas}, [], [], True, False)

    qualificados = _termos_qualificados(mapa)
    cobertos = [r for r in registros if any(_casa(r.conta, cc) for cc in qualificados)]
    sem_atributo = (fixos is None and bool(cobertos)
                    and not any(r.financeiro_permanente for r in cobertos))

    bloqueadas = {linha.id: linha.bloqueio for linha in mapa.linhas if linha.bloqueio}
    if sem_atributo:
        bloqueadas.update({linha.id: SEM_ATRIBUTO for linha in mapa.linhas
                           if _qualificada(linha)})

    # Linha bloqueada é apurada sem contas: soma zero no total, e sai `None` abaixo (D5 do BF).
    fixos = fixos or {}
    apuravel = replace(mapa, linhas=tuple(
        linha._replace(colunas=tuple(c._replace(contas=()) for c in linha.colunas))
        if linha.id in bloqueadas or linha.id in fixos else linha
        for linha in mapa.linhas
    ))
    calculada = apurar_matriz(apuravel, registros, direcao)

    valores = {rule_id: celulas.get(COLUNA_ATUAL)
               for rule_id, celulas in calculada.valores.items()}
    nao_apuradas = [n._replace(coluna=coluna) for n in calculada.nao_apuradas
                    if n.coluna in (COLUNA_ATUAL, "-")]

    linhas = mapa.por_id()
    for rule_id, valor in fixos.items():
        valores[rule_id] = valor
        if valor is None:
            nao_apuradas.append(NaoApurada(rule_id, coluna, "-", NAO_PUBLICADO))
    for rule_id in ordem_topologica(linhas):
        linha = linhas[rule_id]
        if fixos and linha.referencias and linha.quadro == QUADRO_FP:
            valores[rule_id] = _somar(linha, valores)
            if valores[rule_id] is None:
                nao_apuradas.append(NaoApurada(rule_id, coluna, "-",
                                               "agregação de célula não apurada"))
        if linha.referencias and all(r.regra in bloqueadas for r in linha.referencias):
            bloqueadas[rule_id] = TODAS_BLOQUEADAS
    for rule_id, motivo in bloqueadas.items():
        valores[rule_id] = None
        nao_apuradas.append(NaoApurada(rule_id, coluna, "-", motivo))

    residuos = [] if sem_atributo or fixos else _residuos_fp(cobertos, direcao)
    return _Coluna(valores, nao_apuradas, residuos, not registros, sem_atributo)


def _totalizar(mapa: MapaBO, folhas: dict[tuple[str, str], Decimal],
               ) -> dict[tuple[str, str], dict[str, Decimal]]:
    """As folhas informadas e, por cima, as totalizadoras: soma das parcelas informadas, como o
    manual do BF. Totalizadora sem nenhuma parcela informada não existe."""
    linhas = mapa.por_id()
    por_id = {linha.id: folhas[(linha.quadro, linha.codigo)] for linha in mapa.linhas
              if (linha.quadro, linha.codigo) in folhas}
    for rule_id in ordem_topologica(linhas):
        parcelas = [por_id[r.regra] if r.sinal == "+" else -por_id[r.regra]
                    for r in linhas[rule_id].referencias if r.regra in por_id]
        if parcelas:
            por_id[rule_id] = sum(parcelas, Decimal("0.00"))
    return {(linha.quadro, linha.codigo): {COLUNA_ANTERIOR: por_id[linha.id]}
            for linha in mapa.linhas if linha.id in por_id}


def _coluna_pronta(mapa: MapaBO, celulas: dict, ausente: str) -> _Coluna:
    """Coluna anterior pronta (processado de N−1 ou digitada), casada por quadro e código."""
    valores: dict[str, Decimal | None] = {}
    nao_apuradas: list[NaoApurada] = []
    for linha in mapa.linhas:
        celula = celulas.get((linha.quadro, linha.codigo))
        valores[linha.id] = None if celula is None else celula.get(COLUNA_ANTERIOR)
        if valores[linha.id] is None:
            motivo = ausente if celula is None else SEM_VALOR_ANTERIOR
            nao_apuradas.append(NaoApurada(linha.id, COLUNA_ANTERIOR, "-", motivo))
    return _Coluna(valores, nao_apuradas, [], False, False)


def _saldos_do_pronto(pronto: dict, informadas: dict[str, Decimal] | None,
                      ) -> dict[str, Decimal | None]:
    """Saldo anterior por fonte: as informadas, ou as linhas de fonte de N−1 e o saldo sem fonte."""
    if informadas is not None:
        return dict(informadas)
    saldos = {codigo: celula[COLUNA_ANTERIOR]
              for (quadro, codigo), celula in pronto["matriz"].items()
              if quadro == QUADRO_SUPERAVIT and codigo != "Total"
              and COLUNA_ANTERIOR in celula}           # `None` = não apurada, não ausente
    if pronto.get("fonte_vazia"):
        saldos["0000"] = pronto["fonte_vazia"]
    return saldos


def _com_anterior(mapa: MapaBO, matriz: dict, celulas: dict) -> dict:
    """A matriz com a coluna anterior trocada pela de uma visão de N−1."""
    por_chave = {(linha.quadro, linha.codigo): linha.id for linha in mapa.linhas}
    saida = {rule_id: dict(coluna) for rule_id, coluna in matriz.items()}
    for chave, celula in celulas.items():
        if chave in por_chave and COLUNA_ANTERIOR in celula:
            saida[por_chave[chave]][COLUNA_ANTERIOR] = celula[COLUNA_ANTERIOR]
    return saida


def _somar(linha, valores: dict[str, Decimal | None]) -> Decimal | None:
    """Total de referências já apuradas; `None` se alguma parcela não existe."""
    parcelas = [valores.get(r.regra) for r in linha.referencias]
    if any(p is None for p in parcelas):
        return None
    sinais = zip(linha.referencias, parcelas, strict=True)
    return sum((p if r.sinal == "+" else -p for r, p in sinais), Decimal("0.00"))


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


def _superavit(mapa: MapaBO, matriz: dict, atual: list[Registro],
               saldos_anterior: dict[str, Decimal | None], coluna_atual: _Coluna,
               coluna_anterior: _Coluna, anterior_informado: bool = False,
               ) -> tuple[MapaBO, _Coluna, _Coluna, dict[str, Decimal]]:
    """Uma linha por fonte de 4 dígitos. Complemento soma na fonte.

    O saldo sem fonte volta à parte, por coluna: não vira linha nem entra no total.
    `anterior_informado` (manual): a fonte de N que não foi informada fica não apurada, e o total
    anterior só existe se alguma fonte foi informada.
    """
    saldos_atual = _saldos_por_fonte(atual)
    saldos_anterior = dict(saldos_anterior)
    ausente = None if anterior_informado else Decimal("0.00")
    total = next((linha for linha in mapa.linhas
                  if linha.quadro == QUADRO_SUPERAVIT and linha.codigo == "Total"), None)
    if total is None:
        return mapa, coluna_atual, coluna_anterior, {}

    linhas_fonte: list[Linha] = []
    vazio_atual = saldos_atual.pop("0000", Decimal(0))
    vazio_anterior = saldos_anterior.pop("0000", Decimal(0))
    for codigo in sorted(set(saldos_atual) | set(saldos_anterior)):
        valor_atual = saldos_atual.get(codigo, Decimal("0.00"))
        valor_anterior = saldos_anterior.get(codigo, ausente)
        if valor_atual == 0 and valor_anterior == 0:
            continue
        linhas_fonte.append(total._replace(
            id=f"bp.superavit_deficit.{codigo}",
            codigo=codigo,
            rotulo=rotulo_fonte(codigo),
            bloqueio="",
            ordem=len(linhas_fonte) + 1,
            nivel=2,
            colunas=(),
            referencias=(),
            fonte=codigo,
        ))
        matriz[linhas_fonte[-1].id] = {COLUNA_ATUAL: valor_atual, COLUNA_ANTERIOR: valor_anterior}

    total_anterior = (None if anterior_informado and not saldos_anterior
                      or None in saldos_anterior.values()
                      else sum(saldos_anterior.values(), Decimal("0.00")))
    matriz[total.id] = {COLUNA_ATUAL: sum(saldos_atual.values(), Decimal("0.00")),
                        COLUNA_ANTERIOR: total_anterior}
    # As referências não recalculam (a matriz do total já está acima): publicam a linha como
    # totalizadora, que é o que decide o destaque em quem renderiza.
    total = total._replace(ordem=len(linhas_fonte) + 1, bloqueio="",
                           referencias=tuple(RefLinha(linha.id, "+") for linha in linhas_fonte))
    demais = tuple(linha for linha in mapa.linhas if linha.quadro != QUADRO_SUPERAVIT)
    mapa = replace(mapa, linhas=(*demais, *linhas_fonte, total))
    ids = {linha.id for linha in linhas_fonte} | {total.id}

    def _sem(coluna: _Coluna) -> _Coluna:
        return replace(coluna, nao_apuradas=[
            n for n in coluna.nao_apuradas if n.rule_id not in ids])

    vazio = {COLUNA_ATUAL: vazio_atual, COLUNA_ANTERIOR: vazio_anterior}
    fonte_vazia = {coluna: valor for coluna, valor in vazio.items() if valor}
    coluna_anterior = _sem(coluna_anterior)
    if total_anterior is None:
        coluna_anterior.nao_apuradas.append(
            NaoApurada(total.id, COLUNA_ANTERIOR, "-", NAO_INFORMADO))
    return mapa, _sem(coluna_atual), coluna_anterior, fonte_vazia


def _saldos_por_fonte(registros: list[Registro]) -> dict[str, Decimal]:
    saldos: dict[str, Decimal] = defaultdict(Decimal)
    for registro in registros:
        if registro.conta not in CONTAS_SUPERAVIT:
            continue
        chave = "".join(filter(str.isdigit, registro.fonte_recursos)).zfill(4)[-4:]
        saldos[chave] += registro.valor if registro.natureza == "C" else -registro.valor
    return saldos




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
