FROM python:3.14-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip wheel --no-deps --wheel-dir /wheels .


FROM python:3.14-slim AS runtime

ARG VERSION=0.9.0
ARG VCS_REF=unknown

LABEL org.opencontainers.image.title="Energy Flex Trust Platform" \
      org.opencontainers.image.description="Auditable energy-flexibility coordination reference platform" \
      org.opencontainers.image.source="https://github.com/bilgekayali/energy-flex-trust-platform" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 10001 appgroup \
    && useradd --no-log-init --uid 10001 --gid 10001 --create-home appuser

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

COPY --chown=10001:10001 alembic.ini ./alembic.ini
COPY --chown=10001:10001 migrations ./migrations

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

STOPSIGNAL SIGTERM

CMD ["uvicorn", "energy_flex_trust.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
