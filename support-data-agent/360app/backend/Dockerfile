FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

COPY . /app

ENV UV_LINK_MODE=copy

EXPOSE 8000

CMD ["sh", "-lc", "uv sync --locked && uv run server"]
