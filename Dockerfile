# ========= Base (общие настройки) =========
ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim AS base

WORKDIR /code
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

# ========= Builder (runtime venv) =========
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY app ./app
RUN uv sync --frozen --no-dev

# ========= Dev (локальная разработка) =========
FROM base AS dev
ENV PATH="/code/.venv/bin:${PATH}"
COPY . .
RUN uv sync --frozen --group dev
EXPOSE 8000
ENTRYPOINT ["/code/docker-entrypoint.sh"]

# ========= Prod (чистый рантайм) =========
FROM base AS prod
COPY --from=builder /code/.venv /code/.venv
ENV PATH="/code/.venv/bin:${PATH}"
COPY app ./app
COPY docker-entrypoint.sh /code/docker-entrypoint.sh
RUN chmod +x /code/docker-entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/code/docker-entrypoint.sh"]
