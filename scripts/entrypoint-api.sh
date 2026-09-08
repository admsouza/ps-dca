#!/bin/sh
# Migrations no boot, atrás de RUN_MIGRATIONS. O advisory lock 43812/1001 serializa a migração
# entre réplicas E entre projetos — RREO e RGF usam a mesma chave no mesmo schema.
set -e

if [ "${RUN_MIGRATIONS}" = "true" ] || [ "${RUN_MIGRATIONS}" = "True" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
else
  echo "[entrypoint] RUN_MIGRATIONS=${RUN_MIGRATIONS} — migrations não aplicadas neste boot"
fi

exec "$@"
