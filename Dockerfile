# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:latest AS uv

# ---------- Builder stage ----------
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /build

COPY pyproject.toml uv.lock ./

RUN uv venv "$VIRTUAL_ENV" && \
    uv sync --frozen --no-dev

COPY src/ src/
COPY main.py .

# ---------- Runtime stage ----------
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

WORKDIR /app

COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser main.py .
COPY --chown=appuser:appuser models/ models/

RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

ENV MODEL_PATH=/app/models/test_run_id/model.pkl

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "src.serving.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]