FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY . /app

ENV UV_LINK_MODE=copy

EXPOSE 8000

CMD ["sh", "-lc", "uv sync --locked && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"]
