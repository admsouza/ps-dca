"""Orquestração da apuração do quadro principal.

Síncrono, puro e sem estado: a mesma chamada serve à rota (F2), ao worker (F3) e ao CLI. Não
recebe sessão de banco, dependência de framework nem cliente HTTP construído por quem chama —
é o requisito "serviço chamável por rota, worker e CLI" do delta spec da plataforma.

O resultado carrega, além dos valores, **procedência** e **diagnóstico** (P9): sem eles, uma
divergência contra o STN vira investigação manual.
"""
from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.bo.matriz import apurar as apurar_matriz
from app.domain.bo.modelo import MapaBO, NaoApurada, Registro, Residuo
from app.domain.bo.saldo import atende
from app.infra.msc.fonte import COMPETENCIA_DE_ENCERRAMENTO, fonte_de
from app.infra.pcasp.natureza import do_pcasp
from app.infra.regras.carregador import carregar

DEMONSTRATIVO = "BO"
# A competência é parâmetro, não constante: há entes que prestam contas mensalmente. O padrão é o
# exercício fechado. De onde cada competência lê — matriz e tipo de saldo — vem de `msc/fonte.py`,
# por decisão do PO de 2026-09-14, que revoga a C1.


@dataclass(frozen=True)
class Procedencia:
    """O que produziu estes números — permite explicar divergência sem reapurar.

    Matriz, tipo de saldo e competência entram aqui porque **mudam o valor**: os mesmos `rule_id`
    apurados de pares diferentes dão números diferentes, e sem a declaração duas apurações
    incomparáveis passam por iguais.
    """

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
    """O que não fechou. Declarado sempre, vazio inclusive."""

    nao_apuradas: list[NaoApurada] = field(default_factory=list)
    residuos: list[Residuo] = field(default_factory=list)
    duracao_ms: int = 0
    sem_dados: bool = False


@dataclass
class Resultado:
    matriz: dict[str, dict[str, Decimal | None]]
    procedencia: Procedencia
    diagnostico: Diagnostico
    # O mapa que produziu estes números. Carrega o template de apresentação (rótulo, quadro,
    # grupo, nível e ordem de cada linha), que o resultado publica junto dos valores — sem ele,
    # quem renderiza declararia os 69 rótulos por fora.
    mapa: MapaBO | None = None


def apurar(ente: int, exercicio: int, fonte, direcao=None, mapa: MapaBO | None = None,
           competencia: int = COMPETENCIA_DE_ENCERRAMENTO) -> Resultado:
    """Apura o quadro principal do BO para um ente, exercício e competência."""
    inicio = time.monotonic()

    mapa = mapa or carregar(exercicio=exercicio)
    direcao = direcao or do_pcasp()
    origem = fonte_de(DEMONSTRATIVO, competencia)

    registros: list[Registro] = []
    for classe in origem.classes:
        registros.extend(fonte.registros(
            ente=ente, ano=exercicio, mes=competencia, classe=classe,
            matriz=origem.matriz, tipo_saldo=origem.tipo_saldo,
        ))

    matriz = apurar_matriz(mapa, registros, direcao)
    residuos = _residuos(mapa, registros)

    return Resultado(
        mapa=mapa,
        matriz=matriz.valores,
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
            nao_apuradas=matriz.nao_apuradas,
            residuos=residuos,
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            sem_dados=not registros,
        ),
    )


def _residuos(mapa: MapaBO, registros: Sequence[Registro]) -> list[Residuo]:
    """Classificações que nenhuma linha de filtro captura.

    Medido em João Pessoa: R$ 12.000.000,00 de natureza `9.9.9.0.00.0.0` não entram no total
    das receitas — compõem a linha de saldos de exercícios anteriores. Resíduo é dado a
    reportar, nunca a somar no total nem a descartar em silêncio.
    """
    # Só natureza de receita e de despesa: são elas que classificam o registro numa linha do
    # total. Função e subfunção qualificam algumas linhas, e tratá-las como classificação
    # devolveria "resíduo" para quase todo registro — ruído, não achado.
    campos = ("natureza_receita", "natureza_despesa")
    filtros_por_campo: dict[str, list] = {}
    for linha in mapa.linhas:
        for filtro in linha.filtros:
            if filtro.operador == "in" and filtro.campo in campos:
                filtros_por_campo.setdefault(filtro.campo, []).append(filtro)

    totais: dict[tuple[str, str], Decimal] = {}
    for registro in registros:
        for campo, filtros in filtros_por_campo.items():
            codigo = getattr(registro, campo, "") or ""
            if not codigo:
                continue
            if any(atende(registro, [f]) for f in filtros):
                continue
            chave = (campo, codigo)
            totais[chave] = totais.get(chave, Decimal("0.00")) + registro.valor

    return [Residuo(campo, codigo, valor) for (campo, codigo), valor in sorted(totais.items())]
