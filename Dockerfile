FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential unzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /workspace
