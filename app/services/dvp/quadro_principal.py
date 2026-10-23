"""Apuração do Quadro Principal da DVP — IPC 05, ed. 2020-01.

Mesmo fluxo do BP, mais simples: um quadro, sem visões, sem equilíbrio e sem publicado SICONFI.
A coluna anterior por unidade tem as origens do BP (`dvp-por-unidade-gestora`): MSCE, processado
de N−1 e manual; o consolidado e o grupo de poder a recebem somada, pronta (`com_recortes`).
Nenhuma regra tem `filters` nem `exclusion_groups` (D1): o saldo de cada célula é o da MSC de
abertura, classes 3 e 4, tomado na direção da coluna (D2).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from app.domain.bo.matriz import apurar as apurar_matriz
from app.domain.bo.matriz import ordem_topologica
from app.domain.bo.modelo import MapaBO, NaoApurada, Registro
from app.infra.msc.fonte import COMPETENCIA_DE_ENCERRAMENTO, fonte_de
from app.infra.pcasp.natureza import do_pcasp
from app.infra.regras.carregador import carregar_em_cache
from app.services.dvp.informados import partir as _partir_informados

DEMONSTRATIVO = "DVP"
COLUNA_ATUAL = "exercicio_atual"
COLUNA_ANTERIOR = "exercicio_anterior"
NAO_INFORMADO = "não informado"
SEM_LINHA_ANTERIOR = "sem linha no exercício anterior"
SEM_VALOR_ANTERIOR = "não apurada no exercício anterior"

POLICIES_NAO_APLICADAS = (
    "itens 15 e 16 do IPC 05 (exclusões por conta): declarados, não executados (D1)",
)


class Anterior(StrEnum):
    MSCE = "msce_exercicio_anterior"
    PROCESSADO = "processado_exercicio_anterior"     # a coluna pronta, do cache de N−1
    MANUAL = "manual"                                # `L<n>` das linhas-base, só por unidade


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
    origem_exercicio_anterior: str = Anterior.MSCE.value
    # Como chegou: o pedido seguinte reaplica (`pipeline-anterior-por-recorte`).
    valores_anteriores: dict[str, str] | None = None
    escolha_anterior: dict | None = None
    anterior_processado: dict | None = None


@dataclass
class Diagnostico:
    nao_apuradas: list[NaoApurada] = field(default_factory=list)
    residuos: list = field(default_factory=list)
    duracao_ms: int = 0
    sem_dados: bool = False
    sem_dados_exercicio_anterior: bool = False
    policies_nao_aplicadas: tuple[str, ...] = POLICIES_NAO_APLICADAS


@dataclass
class Resultado:
    matriz: dict[str, dict[str, Decimal | None]]
    procedencia: Procedencia
    diagnostico: Diagnostico
    mapa: MapaBO | None = None


def apurar(ente: int, exercicio: int, fonte, direcao=None, mapa: MapaBO | None = None,
           competencia: int = COMPETENCIA_DE_ENCERRAMENTO,
           anterior: Anterior = Anterior.MSCE, anterior_pronto: dict | None = None,
           valores_anteriores: dict[str, str] | None = None,
           zero_sem_anterior: bool = False) -> Resultado:
    """Apura as 19 linhas da DVP; a coluna atual vem da MSC de N, a anterior de `anterior`.

    `anterior_pronto` é a coluna já pronta (`PROCESSADO`, ver `pipeline/anterior.py`);
    `valores_anteriores`, a digitada (`MANUAL`). `zero_sem_anterior`: a coluna anterior sai em
    `0,00` onde faltaria dado (sem MSC em N−1, ou coluna pronta sem a célula).
    """
    inicio = time.monotonic()
    anterior = Anterior(anterior)
    mapa = mapa or carregar_em_cache(exercicio, demonstrativo="dvp")
    direcao = _DirecaoDaDVP(direcao or do_pcasp())
    origem = fonte_de(DEMONSTRATIVO, competencia)

    def da_msc(ano: int) -> list[Registro]:
        return [registro for classe in origem.classes for registro in fonte.registros(
            ente=ente, ano=ano, mes=competencia, classe=classe,
            matriz=origem.matriz, tipo_saldo=origem.tipo_saldo,
        )]

    atual, nao_atual, sem_atual = _coluna(mapa, da_msc(exercicio), direcao, COLUNA_ATUAL)
    informado = dict(valores_anteriores or {}) if anterior is Anterior.MANUAL else None
    if anterior is Anterior.MSCE:
        ant, nao_ant, sem_ant = _coluna(mapa, da_msc(exercicio - 1), direcao, COLUNA_ANTERIOR,
                                        zero_sem_anterior)
    else:                                    # nenhuma leitura de N−1
        pronta = (_totalizar(mapa, _partir_informados(informado or {}))
                  if informado is not None else (anterior_pronto or {}).get("matriz", {}))
        ant, nao_ant = _coluna_pronta(mapa, pronta, zero_sem_anterior, NAO_INFORMADO
                                      if informado is not None else SEM_LINHA_ANTERIOR)
        sem_ant = False
    matriz = {linha.id: {COLUNA_ATUAL: atual[linha.id], COLUNA_ANTERIOR: ant[linha.id]}
              for linha in mapa.linhas}

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
            origem_exercicio_anterior=anterior.value,
            valores_anteriores=informado,
        ),
        diagnostico=Diagnostico(
            nao_apuradas=nao_atual + nao_ant,
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            sem_dados=sem_atual,
            sem_dados_exercicio_anterior=sem_ant and anterior is Anterior.MSCE,
        ),
    )


def _coluna(mapa: MapaBO, registros: list[Registro], direcao, coluna: str,
            zero_se_vazio: bool = False,
            ) -> tuple[dict[str, Decimal | None], list[NaoApurada], bool]:
    """Uma coluna: sem registros não há posição (`None`, nunca zero); com eles, linha sem
    movimento é `0,00`. `zero_se_vazio`: apura zero e sinaliza `sem_dados` (unidade sem MSC em
    N−1, num job que leu N−1)."""
    if not registros and not zero_se_vazio:
        return {linha.id: None for linha in mapa.linhas}, [], True
    calculada = apurar_matriz(mapa, registros, direcao)
    valores = {rule_id: celulas.get(COLUNA_ATUAL) for rule_id, celulas in calculada.valores.items()}
    nao_apuradas = [n._replace(coluna=coluna) for n in calculada.nao_apuradas
                    if n.coluna in (COLUNA_ATUAL, "-")]
    return valores, nao_apuradas, not registros


def _totalizar(mapa: MapaBO, folhas: dict[str, Decimal]) -> dict[tuple[str, str], dict]:
    """As folhas informadas e, por cima, as totalizadoras: soma das parcelas informadas, como o
    manual do BP. Totalizadora sem nenhuma parcela informada não existe."""
    linhas = mapa.por_id()
    por_id = {linha.id: folhas[linha.codigo] for linha in mapa.linhas if linha.codigo in folhas}
    for rule_id in ordem_topologica(linhas):
        parcelas = [por_id[r.regra] if r.sinal == "+" else -por_id[r.regra]
                    for r in linhas[rule_id].referencias if r.regra in por_id]
        if parcelas:
            por_id[rule_id] = sum(parcelas, Decimal("0.00"))
    return {(linha.quadro, linha.codigo): {COLUNA_ANTERIOR: por_id[linha.id]}
            for linha in mapa.linhas if linha.id in por_id}


def _coluna_pronta(mapa: MapaBO, celulas: dict, zerar: bool, ausente: str,
                   ) -> tuple[dict[str, Decimal | None], list[NaoApurada]]:
    """Coluna anterior pronta (processado de N−1 ou digitada), casada por quadro e código.

    `zerar`: célula ausente vale `0,00` e não registra `NaoApurada` (sem exercício anterior).
    """
    valores: dict[str, Decimal | None] = {}
    nao_apuradas: list[NaoApurada] = []
    for linha in mapa.linhas:
        celula = celulas.get((linha.quadro, linha.codigo))
        valores[linha.id] = None if celula is None else celula.get(COLUNA_ANTERIOR)
        if valores[linha.id] is None and zerar and celula is None:
            valores[linha.id] = Decimal("0.00")
        elif valores[linha.id] is None:
            motivo = ausente if celula is None else SEM_VALOR_ANTERIOR
            nao_apuradas.append(NaoApurada(linha.id, COLUNA_ANTERIOR, "-", motivo))
    return valores, nao_apuradas


class _DirecaoDaDVP:
    """PCASP com a conta sintética resolvida pelo prefixo (D3): `442510000` não é folha."""

    def __init__(self, base):
        self._base = base

    def credora(self, conta: str) -> bool | None:
        direta = self._base.credora(conta)
        if direta is None:
            direta = self._base.credora_prefixo(conta)
        if direta is None:
            direta = self._base.credora_prefixo(conta.rstrip("0"))
        return direta

    def credora_prefixo(self, prefixo: str) -> bool | None:
        return self._base.credora_prefixo(prefixo)
