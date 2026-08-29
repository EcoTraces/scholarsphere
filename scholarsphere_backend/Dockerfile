FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
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

