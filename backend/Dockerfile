ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.7.20
FROM ${UV_IMAGE} AS uv-source

FROM python:3.12-slim-bookworm AS builder

ARG NODE_MAJOR=22
ARG UV_INDEX_URL

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gnupg \
    ca-certificates \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-source /uv /uvx /usr/local/bin/

WORKDIR /app

COPY backend/ .

RUN UV_INDEX_URL=${UV_INDEX_URL:-https://pypi.org/simple} uv sync

FROM python:3.12-slim-bookworm

COPY --from=builder /usr/bin/node /usr/bin/node
COPY --from=builder /usr/lib/node_modules /usr/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/bin/npx

COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker

COPY --from=uv-source /uv /uvx /usr/local/bin/

WORKDIR /app

COPY --from=builder /app .

EXPOSE 8001 2024

CMD ["sh", "-c", "PYTHONPATH=. uv run --no-sync uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001"]
