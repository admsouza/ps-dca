"""Apuração do Quadro Principal do Balanço Financeiro — IPC 06, ed. 2024-06.

Mesmo fluxo do Balanço Orçamentário: síncrono, puro, sem sessão de banco nem cliente HTTP
construído por quem chama — a mesma função serve à rota, ao worker e ao CLI.

O que difere do BO, e por quê (tudo medido em 2026-09-18,
`docs/evidencia-bf-medicao-2026-09-18.md`):

1. **Direção do saldo por conta**, não da coluna (G7): a regra do IPC 06 já traz o sinal do par
   redutor, e com a direção da coluna `L1` de Recife erra em 754 milhões.
2. **A origem do saldo é por linha** (N1): quase tudo vem da abertura do exercício, mas `L25` e
   `L26` só existem no **encerramento** — é quando a inscrição de restos a pagar acontece — e
   `L29`–`L32` são o **exercício anterior**, porque a abertura do exercício já traz a posição
   final, que é `L62`.
3. **Quatro linhas não têm conta declarada no IPC 06** e ficam não apuradas, nunca zero (G8-b).
   `L28`/`L61` saíram desse grupo: somam `period_change` das 12 competências, só crédito (L28) ou
   só débito (L61), sem subtrair o lado oposto (change `bf-l28-l61-contas-especificas`, D1/D2).
   `L27` soma créditos e `L60` soma débitos nos dois exercícios (classe 2, fontes
   extraorçamentárias). `L61` soma débitos nos dois exercícios, nas mesmas 15 contas de classe 1
   e nas mesmas fontes. `L28` continua só no exercício atual.
4. **O item 38 não é aplicado** (G11-a): a policy não diz quais códigos caracterizam a
   transferência intra, e a interpretação natural quebra `L1` e `L34` em dois entes que batiam
   em centavos. Fica declarada e não executada.
"""
from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from app.domain.bo.matriz import apurar as apurar_matriz
from app.domain.bo.matriz import ordem_topologica
from app.domain.bo.modelo import Linha, MapaBO, NaoApurada, Registro, Residuo
from app.infra.msc.fonte import COMPETENCIA_DE_ENCERRAMENTO, TipoSaldo, fonte_de, fonte_periodo
from app.infra.pcasp.natureza import do_pcasp
from app.services.bf.informados import QUADRO_ANEXO, QUADRO_PRINCIPAL
from app.services.bf.informados import mapa_bf as _mapa
from app.services.bf.informados import partir_informados as _partir_informados
from app.services.bf.informados import validar_informados as _validar_informados
from app.services.bf.origem import (
    DO_ENCERRAMENTO,
    DO_EXERCICIO_ANTERIOR,
    origem_da_celula,
)
from app.services.bf.origem import (
    PERIODO_MENSAL as _PERIODO_MENSAL,
)
from app.services.bf.origem import (
    PERIODO_MENSAL_ANTERIOR as _PERIODO_MENSAL_ANTERIOR,
)

DEMONSTRATIVO = "BF"
COLUNA_ATUAL = "exercicio_atual"
COLUNA_ANTERIOR = "exercicio_anterior"
SUFIXO_ATUAL = "_atual"
SUFIXO_ANTERIOR = "_anterior"
NAO_INFORMADO = "não informado no preenchimento manual"

POLICIES_NAO_APLICADAS = (
    "item 38 (exclusão de intraorçamentárias): a policy não declara quais códigos caracterizam a "
    "transferência intra acompanhada de execução; a interpretação por categoria 7/8 e modalidade "
    "91 foi medida e quebra L1 e L34 em Belo Horizonte e João Pessoa (G11-a)",
)


class Anterior(Enum):
    """De onde vem a coluna do exercício anterior."""

    MSCE = "msce_exercicio_anterior"
    MANUAL = "manual"


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
    # O que muda o valor tem de estar declarado, ou duas apurações incomparáveis passam por iguais.
    origens_por_linha: dict[str, str] = field(default_factory=dict)
    origem_exercicio_anterior: str = Anterior.MSCE.value
    # Mapa informado, na forma em que chegou. É o que o pedido seguinte reaplica.
    valores_anteriores: dict[str, str] | None = None
    # Override G8 do exercício atual (D1/D2) — independente do mapa acima.
    valores_sem_mapeamento: dict[str, str] | None = None


@dataclass
class Diagnostico:
    nao_apuradas: list[NaoApurada] = field(default_factory=list)
    residuos: list[Residuo] = field(default_factory=list)
    # `L14 (c)` do anexo contra `L1` do principal: a mesma receita líquida por dois caminhos.
    # Diferença é reportada, nunca ajustada — em Recife ela é a receita sem fonte de recursos.
    conferencia_anexo: dict | None = None
    # `L33 TOTAL (VI)` contra `L66 TOTAL (XII)`, por coluna. Equilíbrio é a propriedade que define
    # o demonstrativo; diferença é **medida**, nunca ajustada para forçar o fechamento.
    equilibrio: dict[str, Decimal] = field(default_factory=dict)
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
           anterior: Anterior = Anterior.MSCE,
           valores_anteriores: dict[str, Decimal] | None = None,
           valores_sem_mapeamento: dict[str, Decimal] | None = None) -> Resultado:
    """Apura as 66 linhas do quadro principal, nas duas colunas."""
    inicio = time.monotonic()
    anterior = Anterior(anterior)                # o job chega com string; a apuração compara o enum
    manual = anterior is Anterior.MANUAL and valores_anteriores
    informado = dict(valores_anteriores) if manual else None
    if valores_anteriores:
        valores_anteriores = {str(c): Decimal(str(v)) for c, v in valores_anteriores.items()}
    informado_g8 = dict(valores_sem_mapeamento) if valores_sem_mapeamento else None
    if valores_sem_mapeamento:
        valores_sem_mapeamento = {
            str(c): Decimal(str(v)) for c, v in valores_sem_mapeamento.items()
        }
    mapa = mapa or _mapa(exercicio)
    direcao = direcao or do_pcasp()
    origem = fonte_de(DEMONSTRATIVO, competencia)

    if anterior is Anterior.MANUAL:
        principal, anexo = _partir_informados(valores_anteriores or {})
        _validar_informados(principal, mapa, QUADRO_PRINCIPAL)
        _validar_informados(anexo, mapa, QUADRO_ANEXO)
    else:
        principal, anexo = {}, {}

    atual, nao_apuradas, sem_dados, registros_do_exercicio = _apurar_exercicio(
        mapa, ente, exercicio, competencia, fonte, direcao, origem,
        codigos_periodo=frozenset(_PERIODO_MENSAL))

    if valores_sem_mapeamento:
        atual, nao_apuradas = _completar_sem_mapeamento(
            mapa, atual, nao_apuradas, valores_sem_mapeamento)

    sem_dados_anterior = False
    if anterior is Anterior.MSCE:
        coluna_anterior, _, sem_dados_anterior, _ = _apurar_exercicio(
            mapa, ente, exercicio - 1, competencia, fonte, direcao, origem,
            codigos_periodo=_PERIODO_MENSAL_ANTERIOR)
    else:
        principal, saldos_anexo = _completar_manual(mapa, principal, anexo)
        coluna_anterior = {}
        for linha in mapa.linhas:
            if linha.quadro != QUADRO_ANEXO:
                coluna_anterior[linha.id] = {COLUNA_ATUAL: principal.get(linha.codigo)}
                continue
            info = anexo.get(linha.codigo, {})
            receita, deducoes = info.get("receita"), info.get("deducoes")
            saldo = saldos_anexo.get(linha.codigo)
            if saldo is None and receita is not None and deducoes is not None:
                saldo = receita - deducoes
            coluna_anterior[linha.id] = {
                "receita_orcamentaria_atual": receita,
                "deducoes_atual": deducoes,
                "saldo_atual": saldo,
            }
            nao_apuradas += [
                NaoApurada(linha.id, coluna, "-", NAO_INFORMADO)
                for coluna, valor in (
                    ("receita_orcamentaria_anterior", receita),
                    ("deducoes_anterior", deducoes),
                )
                if valor is None and not linha.composta
            ]
        nao_apuradas += [
            NaoApurada(linha.id, COLUNA_ANTERIOR, "-", NAO_INFORMADO)
            for linha in mapa.linhas
            if linha.quadro == QUADRO_PRINCIPAL and linha.codigo not in principal
        ]

    matriz = _montar(mapa, atual, coluna_anterior, anterior)

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
            origens_por_linha=_origens(mapa, origem),
            origem_exercicio_anterior=anterior.value,
            valores_anteriores=informado,
            valores_sem_mapeamento=informado_g8,
        ),
        diagnostico=Diagnostico(
            nao_apuradas=nao_apuradas,
            residuos=_residuos_de_fonte(mapa, registros_do_exercicio),
            conferencia_anexo=_conferir_anexo(mapa, matriz),
            equilibrio=_equilibrio(mapa, matriz),
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            sem_dados=sem_dados,
            sem_dados_exercicio_anterior=sem_dados_anterior,
        ),
    )


# ─── apuração de um exercício, combinando as três origens ────────────────────

def _apurar_exercicio(mapa, ente, exercicio, competencia, fonte, direcao, origem,
                      codigos_periodo: frozenset[str] = frozenset()):
    """Devolve `(valores, nao_apuradas, sem_dados, registros)` para um exercício."""
    do_exercicio = _ler(fonte, ente, exercicio, competencia, origem, origem.tipo_saldo)
    do_encerramento = _ler(fonte, ente, exercicio, competencia, origem, TipoSaldo.ENCERRAMENTO)
    do_anterior = _ler(fonte, ente, exercicio - 1, competencia, origem, origem.tipo_saldo)
    classes = {_PERIODO_MENSAL[codigo] for codigo in codigos_periodo}
    por_classe = _ler_periodo_mensal(fonte, ente, exercicio, classes) if classes else {}

    por_regra: dict[str, list[Registro]] = {}
    for linha in mapa.linhas:
        if linha.codigo in DO_ENCERRAMENTO:
            por_regra[linha.id] = do_encerramento
        elif linha.codigo in DO_EXERCICIO_ANTERIOR:
            por_regra[linha.id] = do_anterior
        elif linha.codigo in codigos_periodo:
            por_regra[linha.id] = por_classe[_PERIODO_MENSAL[linha.codigo]]

    matriz = apurar_matriz(mapa, do_exercicio, direcao, por_conta=True,
                           registros_por_regra=por_regra)
    valores, nao_apuradas = _sem_conta_declarada(mapa, matriz)
    return valores, nao_apuradas, not do_exercicio, do_exercicio


def _ler(fonte, ente, exercicio, competencia, origem, tipo_saldo) -> list[Registro]:
    registros: list[Registro] = []
    for classe in origem.classes:
        registros.extend(fonte.registros(
            ente=ente, ano=exercicio, mes=competencia, classe=classe,
            matriz=origem.matriz, tipo_saldo=tipo_saldo,
        ))
    return registros


def _ler_periodo_mensal(fonte, ente, exercicio, classes: set[int]) -> dict[int, list[Registro]]:
    """12 competências de `period_change` por classe. Cada linha lê só a classe das suas contas."""
    saida: dict[int, list[Registro]] = {}
    for classe in classes:
        origem = fonte_periodo((classe,))
        saida[classe] = [
            registro for competencia in range(1, 13) for registro in fonte.registros(
                ente=ente, ano=exercicio, mes=competencia, classe=classe,
                matriz=origem.matriz, tipo_saldo=origem.tipo_saldo,
            )
        ]
    return saida


def _sem_conta_declarada(mapa: MapaBO, matriz):
    """Linha sem conta no IPC 06 é **não apurada**, não zero (G8-b).

    O motor devolve `0,00` para coluna sem conta — correto para conta declarada e sem
    escrituração, errado para linha que a norma não mapeou. A diferença importa: zero afirma
    que não houve movimento; aqui não se sabe.
    """
    valores = dict(matriz.valores)
    nao_apuradas = list(matriz.nao_apuradas)
    for linha in mapa.linhas:
        if linha.composta or _tem_conta(linha):
            continue
        valores[linha.id] = {coluna.id: None for coluna in linha.colunas}
        nao_apuradas += [
            NaoApurada(linha.id, coluna.id, "-",
                       "linha sem conta declarada no IPC 06 — não apurável pela MSC (G8)")
            for coluna in linha.colunas
        ]
    return valores, nao_apuradas


def _tem_conta(linha: Linha) -> bool:
    return any(coluna.contas or coluna.derivada for coluna in linha.colunas)


def _completar_sem_mapeamento(
    mapa: MapaBO, atual: dict, nao_apuradas: list[NaoApurada], g8: dict[str, Decimal],
) -> tuple[dict, list[NaoApurada]]:
    """Sobrescreve as células G8 informadas no atual e reaplica as compostas (D6).

    Só o `exercicio_atual` do quadro principal; código fora da whitelist já foi recusado na rota.
    """
    por_codigo = {linha.codigo: linha.id for linha in mapa.linhas
                 if linha.quadro == QUADRO_PRINCIPAL}
    informados = {codigo for codigo in g8 if codigo in por_codigo}
    if not informados:
        return atual, nao_apuradas

    principal = {
        linha.codigo: (atual.get(linha.id) or {}).get(COLUNA_ATUAL)
        for linha in mapa.linhas if linha.quadro == QUADRO_PRINCIPAL
    }
    principal.update({codigo: g8[codigo] for codigo in informados})
    principal = _aplicar_compostas_manual(mapa, principal, preservar=frozenset())

    saida = dict(atual)
    for codigo, valor in principal.items():
        rule_id = por_codigo[codigo]
        saida[rule_id] = {**(saida.get(rule_id) or {}), COLUNA_ATUAL: valor}

    ids_informados = {por_codigo[codigo] for codigo in informados}
    restante = [
        n for n in nao_apuradas
        if not (n.coluna == COLUNA_ATUAL and n.rule_id in ids_informados)
    ]
    return saida, restante


# ─── apoio ───────────────────────────────────────────────────────────────────

def _normalizar_rotulo(rotulo: str) -> str:
    texto = unicodedata.normalize("NFD", rotulo)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\([^)]*\)", " ", texto)
    return re.sub(r"[^a-zA-Z0-9]+", " ", texto).lower().strip()


def _codigos_bloco_receita_i(mapa: MapaBO) -> set[str]:
    ingressos = [
        linha for linha in mapa.linhas
        if linha.quadro == QUADRO_PRINCIPAL and linha.grupo == "INGRESSOS"
    ]
    inicio = next((i for i, linha in enumerate(ingressos) if linha.codigo == "L1"), None)
    if inicio is None:
        return set()
    nivel = ingressos[inicio].nivel
    saida = {ingressos[inicio].codigo}
    for linha in ingressos[inicio + 1:]:
        if linha.nivel <= nivel:
            break
        saida.add(linha.codigo)
    return saida


def _saldos_anexo_manual(
    mapa: MapaBO, anexo: dict[str, dict[str, Decimal]],
) -> dict[str, Decimal]:
    """Saldo (f) por código do anexo a partir do mapa Manual."""
    saldos: dict[str, Decimal] = {}
    for linha in mapa.linhas:
        if linha.quadro != QUADRO_ANEXO or linha.composta:
            continue
        info = anexo.get(linha.codigo, {})
        receita, deducoes = info.get("receita"), info.get("deducoes")
        if receita is None and deducoes is None:
            continue
        saldos[linha.codigo] = (receita or Decimal("0.00")) - (deducoes or Decimal("0.00"))
    folhas = list(saldos)

    por_id = mapa.por_id()
    for linha in mapa.linhas:
        if linha.quadro != QUADRO_ANEXO:
            continue
        if not (linha.composta or _normalizar_rotulo(linha.rotulo) == "total"):
            continue
        if linha.referencias:
            soma = Decimal("0.00")
            algum = False
            for ref in linha.referencias:
                filha = por_id.get(ref.regra)
                if filha is None or filha.codigo not in saldos:
                    continue
                parcela = saldos[filha.codigo]
                soma += parcela if ref.sinal == "+" else -parcela
                algum = True
            if algum:
                saldos[linha.codigo] = soma
                continue
        if _normalizar_rotulo(linha.rotulo) == "total" and folhas:
            saldos[linha.codigo] = sum(
                (saldos[c] for c in folhas), Decimal("0.00"),
            )
    return saldos


def _derivar_receita_i_do_anexo(
    mapa: MapaBO, saldos: dict[str, Decimal],
) -> dict[str, Decimal]:
    bloco = _codigos_bloco_receita_i(mapa)
    if not bloco or not saldos:
        return {}
    por_rotulo: dict[str, Decimal] = {}
    saldo_total: Decimal | None = None
    for linha in mapa.linhas:
        if linha.quadro != QUADRO_ANEXO:
            continue
        valor = saldos.get(linha.codigo)
        if valor is None:
            continue
        if linha.composta or _normalizar_rotulo(linha.rotulo) == "total":
            saldo_total = valor
        else:
            por_rotulo[_normalizar_rotulo(linha.rotulo)] = valor

    out: dict[str, Decimal] = {}
    for linha in mapa.linhas:
        if linha.codigo not in bloco:
            continue
        if linha.codigo == "L1":
            if saldo_total is not None:
                out[linha.codigo] = saldo_total
            continue
        casado = por_rotulo.get(_normalizar_rotulo(linha.rotulo))
        if casado is not None:
            out[linha.codigo] = casado
    return out


def _aplicar_compostas_manual(
    mapa: MapaBO,
    principal: dict[str, Decimal],
    preservar: frozenset[str],
) -> dict[str, Decimal]:
    """Preenche totalizadoras do principal somando parcelas disponíveis (D6)."""
    linhas = {
        linha.id: linha for linha in mapa.linhas if linha.quadro == QUADRO_PRINCIPAL
    }
    if not linhas:
        return principal
    out = dict(principal)
    codigo_por_id = {linha.id: linha.codigo for linha in linhas.values()}
    for rule_id in ordem_topologica(linhas):
        linha = linhas[rule_id]
        if not linha.composta or linha.codigo in preservar:
            continue
        soma = Decimal("0.00")
        algum = False
        for ref in linha.referencias:
            codigo = codigo_por_id.get(ref.regra)
            if codigo is None:
                continue
            parcela = out.get(codigo)
            if parcela is None:
                continue
            soma += parcela if ref.sinal == "+" else -parcela
            algum = True
        if algum:
            out[linha.codigo] = soma
    return out


def _completar_manual(
    mapa: MapaBO,
    principal: dict[str, Decimal],
    anexo: dict[str, dict[str, Decimal]],
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """De-para anexo → (I) e totalizadoras do principal na coluna anterior."""
    saldos = _saldos_anexo_manual(mapa, anexo)
    derivados = _derivar_receita_i_do_anexo(mapa, saldos)
    if anexo:
        bloco_i = _codigos_bloco_receita_i(mapa)
        principal = {k: v for k, v in principal.items() if k not in bloco_i}
    principal = {**principal, **derivados}
    # L1 é o TOTAL do anexo: as compostas do principal não podem sobrescrevê-lo.
    preservar = frozenset({"L1"}) & derivados.keys()
    return _aplicar_compostas_manual(mapa, principal, preservar), saldos


def _origens(mapa: MapaBO, origem) -> dict[str, str]:
    """Qual saldo cada linha leu — parte da procedência, porque muda o valor."""
    descricao = {
        "period_change": "MSCC/period_change dos meses 1 a 12",
        "encerramento": f"{origem.matriz}/{TipoSaldo.ENCERRAMENTO} do exercício",
        "exercicio_anterior": f"{origem.matriz}/{origem.tipo_saldo} do exercício anterior",
        "abertura": f"{origem.matriz}/{origem.tipo_saldo} do exercício",
    }
    return {linha.codigo: descricao[origem_da_celula(linha.codigo, COLUNA_ATUAL).nome]
            for linha in mapa.linhas}


# ─── montagem das colunas e conferências ─────────────────────────────────────

def _montar(mapa: MapaBO, atual: dict, anterior_valores: dict, anterior: Anterior) -> dict:
    """Junta as colunas do exercício e do exercício anterior, linha a linha.

    O par de colunas é dado pelo **sufixo** declarado na regra: `_atual` e `_anterior`. Vale para
    os dois quadros — no principal são `exercicio_atual`/`exercicio_anterior`, no anexo são três
    pares (receita, deduções e saldo). A coluna `_anterior` recebe o valor da `_atual`
    correspondente, apurada no exercício anterior.
    """
    matriz: dict[str, dict[str, Decimal | None]] = {}
    for linha in mapa.linhas:
        celulas: dict[str, Decimal | None] = {}
        for coluna in _colunas_de(linha, atual):
            if coluna.endswith(SUFIXO_ANTERIOR):
                par = coluna[: -len(SUFIXO_ANTERIOR)] + SUFIXO_ATUAL
                lido = anterior_valores.get(linha.id) or {}
                manual_principal = anterior is Anterior.MANUAL and linha.quadro != QUADRO_ANEXO
                celulas[coluna] = lido.get(COLUNA_ATUAL if manual_principal else par)
            else:
                celulas[coluna] = (atual.get(linha.id) or {}).get(coluna)
        matriz[linha.id] = celulas
    return matriz


def _colunas_de(linha: Linha, atual: dict) -> tuple[str, ...]:
    """Colunas declaradas na linha; as compostas herdam as das filhas, já apuradas."""
    if linha.colunas:
        return tuple(coluna.id for coluna in linha.colunas)
    return tuple((atual.get(linha.id) or {}).keys())


def _conferir_anexo(mapa: MapaBO, matriz: dict) -> dict | None:
    """`L14` do anexo contra `L1` do principal — atual e, no Manual, também anterior."""
    por_quadro = {(linha.quadro, linha.codigo): linha.id for linha in mapa.linhas}
    anexo = por_quadro.get((QUADRO_ANEXO, "L14"))
    principal = por_quadro.get((QUADRO_PRINCIPAL, "L1"))
    if anexo is None or principal is None:
        return None
    saida: dict = {}
    for sufixo, col_anexo, col_principal in (
        ("", "saldo_atual", COLUNA_ATUAL),
        ("_anterior", "saldo_anterior", COLUNA_ANTERIOR),
    ):
        do_anexo = (matriz.get(anexo) or {}).get(col_anexo)
        do_principal = (matriz.get(principal) or {}).get(col_principal)
        if do_anexo is None or do_principal is None:
            continue
        saida[f"anexo_l14_saldo{sufixo}"] = do_anexo
        saida[f"principal_l1{sufixo}"] = do_principal
        saida[f"diferenca{sufixo}"] = do_anexo - do_principal
    return saida or None


def _residuos_de_fonte(mapa: MapaBO, registros) -> list[Residuo]:
    """Receita que nenhuma linha por fonte captura — declarada, nunca rateada.

    Medido em Recife: 450.202.814,72 em dois registros da conta sintética de receita orçamentária,
    sem fonte de recursos na MSC. O ente os classificou por critério próprio; a apuração não tem
    como saber qual, e inventar um rateio seria afirmar uma vinculação que ninguém declarou.

    Qual conta é essa vem da base canônica, nunca daqui: conta contábil literal no código cria uma
    segunda fonte de regra, e é o que o teste `test_nenhuma_conta_literal_no_apurador` proíbe.
    """
    from app.domain.bo.saldo import _casa, atende

    do_anexo = [linha for linha in mapa.linhas
                if linha.quadro == QUADRO_ANEXO and linha.filtros]
    if not do_anexo:
        return []

    # As contas vêm da própria base canônica — a coluna de receita do anexo declara quais são.
    # Nenhuma conta literal no código: a regra é o único lugar onde conta contábil aparece.
    contas = {conta.cc for linha in do_anexo for coluna in linha.colunas
              if coluna.id.startswith("receita") for conta in coluna.contas}

    total = Decimal("0.00")
    for registro in registros:
        if not any(_casa(registro.conta, conta) for conta in contas):
            continue
        if any(atende(registro, linha.filtros) for linha in do_anexo):
            continue
        total += registro.valor if registro.natureza == "C" else -registro.valor
    return [Residuo("fonte_recurso", "(sem fonte na MSC)", total)] if total else []


def _equilibrio(mapa: MapaBO, matriz: dict) -> dict[str, Decimal]:
    """`L33 − L66` em cada coluna do quadro principal.

    Zero é o esperado: ingressos e dispêndios fecham por construção quando todas as linhas existem.
    Diferente de zero é **achado**, e fica declarado — as quatro linhas sem conta no IPC 06 e a
    receita sem fonte de recursos aparecem aqui como resíduo, não como ajuste.
    """
    por_codigo = {linha.codigo: linha.id for linha in mapa.linhas
                  if linha.quadro == QUADRO_PRINCIPAL}
    ingressos, dispendios = por_codigo.get("L33"), por_codigo.get("L66")
    if ingressos is None or dispendios is None:
        return {}

    saida: dict[str, Decimal] = {}
    for coluna in (COLUNA_ATUAL, COLUNA_ANTERIOR):
        total_ingressos = (matriz.get(ingressos) or {}).get(coluna)
        total_dispendios = (matriz.get(dispendios) or {}).get(coluna)
        if total_ingressos is None or total_dispendios is None:
            continue
        saida[coluna] = total_ingressos - total_dispendios
    return saida
