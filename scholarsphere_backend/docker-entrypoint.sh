#!/bin/sh
set -e

# Optional, portable alternative to a platform-specific "secret file"
# feature (Render's, Cloud Run's, etc. all differ, and not every platform
# a deployer might pick supports one at all): if the service account JSON
# is supplied base64-encoded in FIREBASE_CREDENTIALS_JSON_BASE64, decode
# it to a real file and point FIREBASE_CREDENTIALS_PATH at it. Skipped
# entirely when unset, so this changes nothing for docker-compose (which
# has never set it) or any deployment using Application Default
# Credentials instead.
if [ -n "${FIREBASE_CREDENTIALS_JSON_BASE64:-}" ]; then
  echo "docker-entrypoint: decoding FIREBASE_CREDENTIALS_JSON_BASE64 to a credentials file"
  echo "$FIREBASE_CREDENTIALS_JSON_BASE64" | base64 -d > /tmp/firebase-service-account.json
  export FIREBASE_CREDENTIALS_PATH=/tmp/firebase-service-account.json
fi

# Opt-in only, so this doesn't change docker-compose.yml's existing
# behavior (it already runs a dedicated `migrate` service, once, before
# `api` starts - see its `depends_on: migrate: condition:
# service_completed_successfully`). Platforms without a separate
# release-phase step (e.g. a single Render web service) set
# RUN_MIGRATIONS_ON_BOOT=true instead. alembic upgrade head is idempotent
# - safe to run on every boot, including concurrent/rolling deploys,
# since it no-ops once the database is already at head.
if [ "${RUN_MIGRATIONS_ON_BOOT:-false}" = "true" ]; then
  echo "docker-entrypoint: running 'alembic upgrade head'"
  alembic upgrade head
fi

# $PORT is injected by most PaaS platforms (Render, Cloud Run, ...) and
# must be bound exactly, not assumed to be 8000 - falls back to 8000 for
# docker-compose/local use where PORT is unset.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
