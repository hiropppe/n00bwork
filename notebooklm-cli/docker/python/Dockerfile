FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        less \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
RUN uv run playwright install chromium --with-deps
