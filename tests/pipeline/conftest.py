"""Fundação da fase TEST da plataforma — fakes em memória, sem Postgres, Redis ou HTTP.

A spec exige que a apuração seja testável sem infraestrutura (`Requirement: Núcleo de apuração
isolado de infraestrutura`). Os fakes daqui implementam as mesmas portas que os adapters de
`infra/` implementarão, então o service sob teste não sabe de qual lado veio.

Nada aqui importa `app.` no topo: os módulos da F2/F3 ainda não existem, e a fase TEST tem de
falhar no **comportamento**, com a coleta dos testes funcionando.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import pytest

ENTE = "2507507"
EXERCICIO = 2025
ANEXO = "BO"
VERSAO_API = "0.1.0"
VERSAO_REGRAS = "a" * 64
OUTRA_VERSAO_REGRAS = "b" * 64


@dataclass
class RegistroFake:
    """Espelha `dca_anexo_cache`, com os campos que a decisão de servir ou reapurar consulta."""

    id_ente: str
    an_referencia: int
    anexo: str
    status: str = "ok"                      # ok | processando | erro
    resultado: dict | None = None
    versao_api: str | None = VERSAO_API
    versao_regras: str | None = VERSAO_REGRAS
    erro_detalhe: str | None = None
    solicitado_por: int | None = None
    procedencia: dict | None = None
    diagnostico: dict | None = None
    calculado_em: object = None

    @property
    def identidade(self) -> tuple[str, int, str]:
        return (self.id_ente, self.an_referencia, self.anexo)


STATUS_VALIDOS = ("ok", "processando", "erro")


class RepoFake:
    """Implementa a porta de persistência do cache. Uma tabela só, discriminada por `anexo`."""

    def __init__(self, registros: list[RegistroFake] | None = None):
        self._por_id: dict[tuple[str, int, str], RegistroFake] = {
            r.identidade: r for r in (registros or [])
        }
        self.gravacoes: list[RegistroFake] = []

    def obter(self, ente: str, exercicio: int, anexo: str) -> RegistroFake | None:
        return self._por_id.get((ente, exercicio, anexo))

    def gravar(self, registro: RegistroFake) -> None:
        if registro.status not in STATUS_VALIDOS:
            raise ValueError(f"status inválido: {registro.status}")
        self._por_id[registro.identidade] = registro
        self.gravacoes.append(replace(registro))

    def listar(self, ente: str, exercicio: int) -> list[RegistroFake]:
        return [r for r in self._por_id.values()
                if r.id_ente == ente and r.an_referencia == exercicio]


@dataclass
class FilaFake:
    """Porta da fila. Registra o que foi enfileirado, para o teste afirmar que **não** houve."""

    enfileirados: list[tuple[tuple[str, int, str], str]] = field(default_factory=list)
    falhar: bool = False

    def enfileirar(self, ente: str, exercicio: int, anexo: str, job_id: str) -> None:
        if self.falhar:
            raise RuntimeError("fila indisponível")
        self.enfileirados.append(((ente, exercicio, anexo), job_id))


class JobsFake:
    """Porta do estado de job — o que o polling e a stream leem. Dados puros, nada de pickle."""

    def __init__(self):
        self.registros: dict[str, dict] = {}

    def gravar(self, job_id: str, estado: dict) -> None:
        self.registros[job_id] = dict(estado)

    def obter(self, job_id: str) -> dict | None:
        estado = self.registros.get(job_id)
        return dict(estado) if estado else None


@dataclass
class NotificadorFake:
    """Canal de operação. `falhar` simula o webhook fora do ar; `ausente`, canal não configurado."""

    enviadas: list[dict] = field(default_factory=list)
    falhar: bool = False

    def enviar(self, mensagem: dict) -> None:
        if self.falhar:
            raise RuntimeError("webhook indisponível")
        self.enviadas.append(dict(mensagem))


class RepoVigenciasFake:
    """Espelha `dca_regra_mapeamento` — **INSERT-only**, uma tabela para todos os anexos.

    A chave é `(anexo, ano_vigencia, mes_vigencia)`. Inserir sobre chave existente é recusado
    aqui, como o `PRIMARY KEY` recusa no banco: corrigir mapeamento é publicar vigência nova, não
    reescrever a publicada — quem apurou com a anterior tem de continuar podendo lê-la.
    """

    def __init__(self, registros: list[dict] | None = None):
        self._linhas: list[dict] = [dict(r) for r in (registros or [])]

    def inserir(self, registro: dict) -> dict:
        chave = (registro["anexo"], registro["ano_vigencia"], registro["mes_vigencia"])
        if any(chave == (r["anexo"], r["ano_vigencia"], r["mes_vigencia"]) for r in self._linhas):
            raise KeyError(f"vigência já publicada: {chave}")
        self._linhas.append(dict(registro))
        return self._linhas[-1]

    def listar(self, anexo: str) -> list[dict]:
        """Vigências do anexo, da mais antiga para a mais recente."""
        return sorted((dict(r) for r in self._linhas if r["anexo"] == anexo),
                      key=lambda r: (r["ano_vigencia"], r["mes_vigencia"]))

    def __len__(self) -> int:
        return len(self._linhas)


@dataclass
class LockFake:
    """Lock por identidade, com recuperação de órfão."""

    tomados: dict[tuple[str, int, str], str] = field(default_factory=dict)
    orfaos: set[tuple[str, int, str]] = field(default_factory=set)
    limpezas: int = 0

    def adquirir(self, ente: str, exercicio: int, anexo: str, job_id: str) -> bool:
        chave = (ente, exercicio, anexo)
        if chave in self.tomados and chave not in self.orfaos:
            return False
        self.orfaos.discard(chave)
        self.tomados[chave] = job_id
        return True

    def liberar(self, ente: str, exercicio: int, anexo: str) -> None:
        self.tomados.pop((ente, exercicio, anexo), None)

    def dono(self, ente: str, exercicio: int, anexo: str) -> str | None:
        """`job_id` que detém o lock — é o que a resposta informa como job em voo."""
        return self.tomados.get((ente, exercicio, anexo))

    def limpar_orfaos(self) -> int:
        quantos = len(self.orfaos)
        for chave in list(self.orfaos):
            self.tomados.pop(chave, None)
        self.orfaos.clear()
        self.limpezas += 1
        return quantos


@pytest.fixture
def repo():
    return RepoFake()


@pytest.fixture
def fila():
    return FilaFake()


@pytest.fixture
def lock():
    return LockFake()


@pytest.fixture
def repo_vigencias():
    return RepoVigenciasFake()


@pytest.fixture
def jobs():
    return JobsFake()


@pytest.fixture
def notificador():
    return NotificadorFake()


@pytest.fixture
def servir():
    """O serviço sob teste: decide entre servir do cache e enfileirar job.

    Import tardio: a F2/F3 ainda não existe, e o teste tem de falhar no comportamento, não na
    coleta.
    """
    from app.services.pipeline.cache import ler_ou_enfileirar
    return ler_ou_enfileirar


@pytest.fixture
def pedido(repo, fila, lock):
    """Aplica o serviço com as portas fakes já ligadas, e os defaults do caso feliz."""
    def _pedir(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO,
               versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS, **extra):
        from app.services.pipeline.cache import ler_ou_enfileirar
        return ler_ou_enfileirar(
            ente=ente, exercicio=exercicio, anexo=anexo,
            repo=repo, fila=fila, lock=lock,
            versao_api=versao_api, versao_regras=versao_regras, **extra,
        )
    return _pedir


@pytest.fixture
def registro_ok(repo):
    """Um cache `ok` e atual para a identidade padrão."""
    r = RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok", resultado={"matriz": {"L1": {}}})
    repo.gravar(r)
    return r


@pytest.fixture
def carregar_mapa_de(tmp_path):
    """Carrega o mapa a partir de uma cópia da base, reescrita de outra forma.

    Serve à estabilidade do hash canônico (`versao_regras`): reescrever os YAMLs com CRLF, outra
    indentação ou outra ordem de chaves **não** pode mudá-lo, e alterar uma conta **tem** de mudar.
    Isso é verificável hoje, sem F2 nem F3 — o carregador da F1 já produz o hash.
    """
    import shutil
    from pathlib import Path

    import yaml

    origem = Path(__file__).resolve().parents[2] / "knowledge"

    def _carregar(reescrever: str | None):
        base = tmp_path / (reescrever or "original") / "knowledge"
        shutil.copytree(origem, base)
        alvos = sorted((base / "rules" / "bo").glob("*.yaml"))

        if reescrever in ("crlf", "lf"):
            # Normaliza primeiro: o repositório é conferido em CRLF, e um `replace` cego
            # produziria `\r\r\n` — que muda a estrutura de linhas e, por dobra de escalar
            # do YAML, o próprio valor. O teste mediria o seu próprio defeito.
            for arq in alvos:
                lf = arq.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                arq.write_bytes(lf.replace(b"\n", b"\r\n") if reescrever == "crlf" else lf)
        elif reescrever in ("indentacao", "ordem"):
            for arq in alvos:
                dados = yaml.safe_load(arq.read_text(encoding="utf-8"))
                arq.write_text(
                    yaml.safe_dump(dados, allow_unicode=True, default_flow_style=False,
                                   indent=6 if reescrever == "indentacao" else 2,
                                   sort_keys=(reescrever == "ordem")),
                    encoding="utf-8",
                )
        elif reescrever == "conta":
            arq = alvos[0]
            dados = yaml.safe_load(arq.read_text(encoding="utf-8"))
            for regra in dados["rules"]:
                for coluna in (regra.get("columns") or {}).values():
                    contas = coluna.get("accounts") or []
                    if contas:
                        contas[0]["pattern"] = contas[0]["pattern"] + "9"
                        arq.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
                        return _importar(base)
            raise AssertionError("nenhuma conta encontrada para alterar")

        return _importar(base)

    def _importar(base):
        from app.infra.regras.carregador import carregar
        return carregar(EXERCICIO, base=base)

    return _carregar
