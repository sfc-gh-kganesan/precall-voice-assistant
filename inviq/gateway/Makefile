.phony: install dev lint test check format formatcheck typecheck

install:
	uv sync

dev: install
	uv run uvicorn app.main:app --reload --port 8080

lint: install
	uv run ruff check .

test: install
	uv run pytest

check: formatcheck lint typecheck

format: install
	uv run ruff format .

formatcheck: install
	uv run ruff format --diff .

typecheck: install
	uv run pyright

fix: format
	uv run ruff check --fix