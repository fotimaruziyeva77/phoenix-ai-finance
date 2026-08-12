# Keep in sync with CI (`.github/workflows/*.yml`), `pyproject.toml` / `.python-version`.
#
# Build args (optional): bake release metadata for Sentry and OpenAPI `version`.
# CI should pass: --build-arg APP_VERSION=<sha|semver> --build-arg SENTRY_RELEASE=<same or semver-sha>
FROM python:3.12-slim-bookworm

ARG APP_VERSION=0.1.0
ARG SENTRY_RELEASE=

ENV APP_VERSION=${APP_VERSION} \
    SENTRY_RELEASE=${SENTRY_RELEASE}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY main.py .

RUN useradd --create-home --uid 1000 app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["python", "main.py"]
