"""Configuração lida do ambiente, em um lugar só.

Nomes idênticos aos de `regras-rreo-api` e `regras-rgf-api` sempre que significam o mesmo — num
monolito modular com Postgres e Redis compartilhados, nome divergente para o mesmo conceito
transforma o `.env` de produção em adivinhação.
"""
from __future__ import annotations

import os
from functools import lru_cache


def _int(nome: str, padrao: int) -> int:
    try:
        return int(os.getenv(nome, str(padrao)))
    except (TypeError, ValueError):
        return padrao


def _bool(nome: str, padrao: bool = False) -> bool:
    return os.getenv(nome, str(padrao)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Instantâneo do ambiente. Construído uma vez, lido em todo lugar."""

    def __init__(self) -> None:
        self.ambiente = os.getenv("ENVIRONMENT", "development")
        self.debug = _bool("DEBUG")

        # Postgres — compartilhado com RREO e RGF; a separação da DCA é por prefixo de tabela.
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = _int("POSTGRES_PORT", 5432)
        self.postgres_user = os.getenv("POSTGRES_USER", "postgres")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "")
        self.postgres_db = os.getenv("POSTGRES_DB", "db-ps-rreo-rgf-dca")
        self.db_pool_size = _int("DB_POOL_SIZE", 5)
        self.db_max_overflow = _int("DB_MAX_OVERFLOW", 10)
        self.db_echo = _bool("DB_ECHO")
        self.db_connect_timeout = _int("DB_CONNECT_TIMEOUT", 10)
        self.run_migrations = _bool("RUN_MIGRATIONS")
        self.alembic_lock_timeout = _int("ALEMBIC_LOCK_TIMEOUT_SECONDS", 120)

        # Redis — instância comum. `REDIS_PREFIX` nomeia o cache de MSC e é compartilhado de
        # propósito; o estado de execução da DCA vive sob `dca:` (app/infra/fila/chaves.py).
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = _int("REDIS_PORT", 6379)
        self.redis_db = _int("REDIS_DB", 0)
        self.redis_password = os.getenv("REDIS_PASSWORD") or None
        self.redis_socket_timeout = _int("REDIS_SOCKET_TIMEOUT", 5)
        self.redis_connect_timeout = _int("REDIS_SOCKET_CONNECT_TIMEOUT", 5)
        self.redis_max_connections = _int("REDIS_MAX_CONNECTIONS", 120)

        # Fila e job
        self.fila = os.getenv("DCA_ARQ_QUEUE_NAME", "arq:queue:dca")
        self.job_timeout = _int("DCA_JOB_TIMEOUT_SECONDS", 3600)
        self.job_ttl = _int("DCA_JOB_TTL_SECONDS", 3600)
        self.max_concorrentes = _int("PIPELINE_MAX_CONCORRENTES", 2)

        # Auth — `SECRET_KEY` e `S2S_API_SECRET` são as do hub: o JWT é HS256 verificado
        # localmente, e chave própria não validaria token emitido pelo hub.
        self.secret_key = os.getenv("SECRET_KEY", "")
        self.algoritmo = os.getenv("ALGORITHM", "HS256")
        self.s2s_secret = os.getenv("S2S_API_SECRET", "")
        self.auth_api_url = os.getenv("AUTH_API_URL", "")
        # Exceção deliberada: chave dedicada, não derivada do `SECRET_KEY`.
        self.token_encryption_key = os.getenv("TOKEN_ENCRYPTION_KEY", "")

        # Fontes
        self.fonte_padrao = os.getenv("DATA_SOURCE", "siconfi")
        self.siconfi_url = os.getenv("SICONFI_API_URL",
                                     "https://apidatalake.tesouro.gov.br/ords/siconfi")
        self.siconfi_timeout = _int("SICONFI_TIMEOUT", 30)
        self.publicsoft_url = os.getenv("PUBLICSOFT_API_URL", "")
        self.publicsoft_audit_url = os.getenv("PUBLICSOFT_AUDIT_URL", "")
        self.publicsoft_timeout = _int("PUBLICSOFT_TIMEOUT", 120)
        self.publicsoft_ssl_verify = _bool("PUBLICSOFT_SSL_VERIFY")

        # Operação
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.swagger = _bool("ENABLE_SWAGGER")
        self.swagger_publico = _bool("ENABLE_SWAGGER_PUBLIC", True)
        self.cors_origens_raw = os.getenv("CORS_ORIGINS", "")

    @property
    def cors_origens(self) -> list[str]:
        cru = self.cors_origens_raw.strip()
        if cru == "*":
            return []
        return [o.strip() for o in cru.split(",") if o.strip() and o.strip() != "*"]

    @property
    def database_url(self) -> str:
        """URL do SQLAlchemy a partir de `POSTGRES_*`.

        O padrão do RGF: senha **sem** URL-encoding manual no `.env`, encodada aqui. O RREO
        publica a mesma senha percent-encoded porque a embute em `DATABASE_URL`.
        """
        from urllib.parse import quote_plus

        credencial = (f"{quote_plus(self.postgres_user)}:{quote_plus(self.postgres_password)}"
                      if self.postgres_password else quote_plus(self.postgres_user))
        return (f"postgresql+psycopg2://{credencial}"
                f"@{self.postgres_host}:{self.postgres_port}/{quote_plus(self.postgres_db)}")

    def exigir(self, *nomes: str) -> None:
        """Falha nomeando o que falta, antes de a ausência virar erro obscuro em runtime."""
        faltando = [n for n in nomes if not getattr(self, n, None)]
        if faltando:
            raise RuntimeError(f"configuração ausente no ambiente: {', '.join(faltando)}")


@lru_cache(maxsize=1)
def config() -> Config:
    return Config()
