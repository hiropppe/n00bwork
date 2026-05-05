FROM debian:bookworm-slim

ARG DUCKDB_VERSION=v1.5.2

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        unzip \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    arch="$(uname -m)"; \
    case "$arch" in \
        x86_64) ddb_arch=amd64 ;; \
        aarch64|arm64) ddb_arch=arm64 ;; \
        *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fL -o /tmp/duckdb.zip \
        "https://github.com/duckdb/duckdb/releases/download/${DUCKDB_VERSION}/duckdb_cli-linux-${ddb_arch}.zip"; \
    unzip /tmp/duckdb.zip -d /usr/local/bin; \
    rm /tmp/duckdb.zip; \
    chmod +x /usr/local/bin/duckdb; \
    duckdb --version

WORKDIR /data
