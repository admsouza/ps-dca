"""Apuração da Demonstração dos Fluxos de Caixa — IPC 08, ed. 2020-01.

Mesmo fluxo de BO, BF, BP e DVP: síncrono, puro, sem sessão de banco nem cliente HTTP construído
por quem chama. A mesma função serve à rota, ao worker e ao CLI.

O que difere, e por quê (medido em 2026-10-26/27 contra Porto Alegre/RS 2025):

1. **As agregadoras são totalizadas aqui, não no motor** (D2). `L16`, `L21` e `L30` não declaram
   `columns` — o item 17 manda o ente adaptá-las, e elas são campo informado. O motor marca a
   agregadora que as referencia como não apurada ("referências sem coluna em comum"), o que
   derrubava `L1`, `L12`, `L17`, `L18`, `L26`, `L27`, `L34` e `L36` de uma vez. Aqui as folhas
   vêm do motor, as informadas entram por cima e os totais saem em ordem topológica — o mesmo que
   `dvp/quadro_principal.py` já faz para a coluna manual.
2. **`L35` é o caixa do exercício anterior** (D3). A MSC de encerramento de N traz a posição
   **final** de N; o caixa inicial de N é o `1.1.1` da MSC de N−1. Sem isto `L35` saía igual a
   `L36`. Confere com `L29`/`L62` do BF do mesmo ente.
3. **Quatro quadros**: o principal e três auxiliares que detalham `L10`, `L13`, `L14` e `L15`.
   Todos saem da mesma leitura; o que os separa são os filtros de natureza, função e subfunção,
   que o motor já aplica.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.bo.matriz import apurar as apurar_matriz
from app.domain.bo.matriz import ordem_topologica
from app.domain.bo.modelo import MapaBO, NaoApurada, Registro
from app.domain.bo.saldo import atende
from app.infra.msc.fonte import COMPETENCIA_DE_ENCERRAMENTO, fonte_de
from app.infra.pcasp.natureza import do_pcasp
from app.infra.regras.carregador import carregar_em_cache
from app.services.dfc.informados import (
    CODIGOS_SEM_MAPEAMENTO,
)
from app.services.dfc.informados import (
    partir as _partir_informados,
)
from app.services.dfc.informados import (
    validar_valores_informados as _validar,
)

DEMONSTRATIVO = "DFC"
COLUNA_ATUAL = "exercicio_atual"
COLUNA_ANTERIOR = "exercicio_anterior"
QUADRO_PRINCIPAL = "QUADRO_PRINCIPAL"
CAIXA = "L35"                      # lê o exercício anterior (D3)
# `L25` é residual: o IPC 08 filtra `L23` por elemento e `L25` por modalidade, e as duas listas se
# sobrepõem — a mesma aquisição entrava nas duas. Medido em Cuitegi 2025: 1.791.501,94 contado
# duas vezes, contra `L25` = 0,00 publicada (change `dfc-l25-residual`).
RESIDUAL = "L25"
JA_CONTADAS = ("L23", "L24")
CLASSE_DO_CAIXA = 1
ZERO = Decimal("0.00")
SEM_CAIXA_ANTERIOR = "sem caixa do exercício anterior"

POLICIES_NAO_APLICADAS = (
    "item 17 do IPC 08: L16, L21 e L30 são campo informado pelo ente, não mapeadas (D10)",
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
    valores_informados: dict[str, str] | None = None


@dataclass
class Diagnostico:
    nao_apuradas: list[NaoApurada] = field(default_factory=list)
    residuos: list = field(default_factory=list)
    duracao_ms: int = 0
    sem_dados: bool = False
    sem_dados_exercicio_anterior: bool = False
    # Linhas que o ente preenche à mão (item 17), para a tela abrir o campo.
    informaveis: tuple[str, ...] = tuple(sorted(CODIGOS_SEM_MAPEAMENTO))
    policies_nao_aplicadas: tuple[str, ...] = POLICIES_NAO_APLICADAS


@dataclass
class Resultado:
    matriz: dict[str, dict[str, Decimal | None]]
    procedencia: Procedencia
    diagnostico: Diagnostico
    mapa: MapaBO | None = None


def apurar(ente: int, exercicio: int, fonte, direcao=None, mapa: MapaBO | None = None,
           competencia: int = COMPETENCIA_DE_ENCERRAMENTO,
           valores_informados: dict[str, str] | None = None) -> Resultado:
    """Apura as 84 linhas da DFC nas duas colunas.

    `valores_informados` são as linhas do item 17 (`L16`, `L21`, `L30`) digitadas pelo contador;
    ausentes valem `0,00` na agregadora, nunca derrubam o total.
    """
    inicio = time.monotonic()
    informados = dict(valores_informados or {})
    _validar(informados)
    mapa = mapa or carregar_em_cache(exercicio, demonstrativo="dfc")
    direcao = direcao or do_pcasp()
    origem = fonte_de(DEMONSTRATIVO, competencia)

    def da_msc(ano: int, classes: tuple[int, ...] = origem.classes) -> list[Registro]:
        return [registro for classe in classes for registro in fonte.registros(
            ente=ente, ano=ano, mes=competencia, classe=classe,
            matriz=origem.matriz, tipo_saldo=origem.tipo_saldo,
        )]

    # Três leituras: N, N−1 e o caixa de N−2 — este só para `L35` da coluna anterior (D3).
    do_exercicio, do_anterior = da_msc(exercicio), da_msc(exercicio - 1)
    caixa_anterior = [r for r in do_anterior if _e_do_caixa(r)]
    caixa_retrasado = da_msc(exercicio - 2, (CLASSE_DO_CAIXA,))

    folhas = _partir_informados(informados)
    atual, nao_atual = _coluna(mapa, do_exercicio, caixa_anterior, direcao, folhas, COLUNA_ATUAL)
    ant, nao_ant = _coluna(mapa, do_anterior, caixa_retrasado, direcao, folhas, COLUNA_ANTERIOR)

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
            valores_informados=informados or None,
        ),
        diagnostico=Diagnostico(
            nao_apuradas=nao_atual + nao_ant,
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            sem_dados=not do_exercicio,
            sem_dados_exercicio_anterior=not caixa_anterior,
        ),
    )


def _e_do_caixa(registro: Registro) -> bool:
    """Registro de `1.1.1` — o caixa e equivalentes de caixa do PCASP."""
    return registro.conta.startswith("111")


def _coluna(mapa: MapaBO, registros: list[Registro], caixa: list[Registro], direcao,
            folhas_informadas: dict[str, Decimal], coluna: str,
            ) -> tuple[dict[str, Decimal | None], list[NaoApurada]]:
    """Uma coluna inteira: folhas pelo motor, informadas por cima, totais em ordem topológica.

    Sem registros não há posição: tudo `None`, nunca zero — zero é valor legítimo do
    demonstrativo e usá-lo para "não sei" apagaria a diferença.
    """
    if not registros:
        return {linha.id: None for linha in mapa.linhas}, []

    linhas = mapa.por_id()
    por_codigo = {linha.codigo: linha for linha in mapa.linhas
                  if linha.quadro == QUADRO_PRINCIPAL}
    # `L35` lê o caixa do exercício anterior (D3); `L25`, só o que não entrou em `L23`/`L24`.
    calculada = apurar_matriz(mapa, registros, direcao, registros_por_regra={
        por_codigo[CAIXA].id: caixa,
        por_codigo[RESIDUAL].id: _residuais(registros, por_codigo),
    })

    valores: dict[str, Decimal | None] = {}
    nao_apuradas = [n._replace(coluna=coluna) for n in calculada.nao_apuradas
                    if n.coluna in (COLUNA_ATUAL, "-") and not _agrega(linhas, n.rule_id)]
    for linha in mapa.linhas:
        if linha.composta:
            continue                                   # totalizada abaixo
        if linha.codigo in CODIGOS_SEM_MAPEAMENTO and linha.quadro == QUADRO_PRINCIPAL:
            valores[linha.id] = folhas_informadas.get(linha.codigo, ZERO)
        else:
            valores[linha.id] = (calculada.valores.get(linha.id) or {}).get(COLUNA_ATUAL)

    if not caixa:                                      # sem MSC em N−1: o caixa inicial não existe
        caixa_id = por_codigo[CAIXA].id
        valores[caixa_id] = None
        nao_apuradas.append(NaoApurada(caixa_id, coluna, "-", SEM_CAIXA_ANTERIOR))

    _totalizar(linhas, valores)
    return valores, nao_apuradas


def _residuais(registros: list[Registro], por_codigo: dict) -> list[Registro]:
    """Registros que não atendem aos filtros de `L23` nem de `L24`.

    Por registro, nunca por subtração de totais: `L23` captura o elemento 51 de **qualquer**
    modalidade, inclusive uma que `L25` exclui — subtrair o total de `L23` tiraria de `L25` o que
    nunca entrou nela, e podia deixá-la negativa.
    """
    contadas = [por_codigo[codigo].filtros for codigo in JA_CONTADAS
                if por_codigo[codigo].filtros]
    return [r for r in registros
            if not any(atende(r, filtros) for filtros in contadas)]


def _agrega(linhas: dict, rule_id: str) -> bool:
    """A linha é agregadora? O motor a reporta não apurada quando uma parcela não tem coluna —
    aqui ela é recalculada, então o aviso não vale."""
    linha = linhas.get(rule_id)
    return bool(linha and linha.composta)


def _totalizar(linhas: dict, valores: dict[str, Decimal | None]) -> None:
    """Agregadoras em ordem topológica. Parcela não apurada torna o total não apurado."""
    for rule_id in ordem_topologica(linhas):
        referencias = linhas[rule_id].referencias
        if not referencias:
            continue
        parcelas = [valores.get(r.regra) for r in referencias]
        if any(parcela is None for parcela in parcelas):
            valores[rule_id] = None
            continue
        valores[rule_id] = sum(
            (parcela if r.sinal == "+" else -parcela
             for r, parcela in zip(referencias, parcelas, strict=True)), ZERO)
