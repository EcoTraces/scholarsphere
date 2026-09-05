# Pinned to bookworm (Debian 12), not the floating `python:3.12-slim` tag:
# that tag now resolves to trixie (Debian 13), a codename Playwright 1.49.1
# doesn't recognize (its registry only maps debian11/debian12/ubuntu20-24) -
# unable to identify the OS, it silently falls back to its ubuntu20.04
# package list (`ttf-ubuntu-font-family`, `ttf-unifont`), which trixie's
# apt repo has since renamed (e.g. to `fonts-unifont`), so
# `playwright install --with-deps chromium` fails the build with
# "Package 'ttf-unifont' has no installation candidate". bookworm is a
# codename Playwright explicitly supports with the correct current
# package names, so this is real and reproducible, not floating-tag drift.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Browser-rendering fallback (app/services/browser_rendering.py) - only
# used by scraper sources that opt in via `allow_browser_rendering = True`
# (none do yet as of this line's addition; see docs/AUTHORITATIVE_SOURCES.md
# for which do, if any, once one does). This is a real, material tradeoff:
# it adds Chromium plus its OS dependencies to every image built from this
# Dockerfile - api, worker, and beat alike (docker-compose.yml builds all
# three from this one image) - roughly +300-400MB, even though only the
# worker (which runs the scraper Celery tasks) ever actually needs it; the
# api process itself never launches a browser. If image size/deploy time
# becomes a real problem (e.g. for the free-tier Render API deployment in
# render.yaml, which uses this same Dockerfile), splitting this into a
# separate Dockerfile.worker that only the worker/beat services build from
# is the fix - not attempted here to keep this one deployment story intact.
RUN playwright install --with-deps chromium

COPY . .
RUN chmod +x docker-entrypoint.sh

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
# Deliberately CMD, not ENTRYPOINT: docker-compose.yml's worker/beat
# services override this with their own `command: celery -A ... worker`/
# `beat` - an ENTRYPOINT would instead receive those as arguments to this
# script, which doesn't forward them, silently breaking both services.
CMD ["./docker-entrypoint.sh"]

