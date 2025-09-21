.phony: check format formatcheck install lint dev test typecheck

check: formatcheck lint typecheck

format: install
	uv run ruff format

formatcheck: install
	uv run ruff format --diff

install:
	uv sync

lint: install
	uv run ruff check

dev: install
	uv run python -m app.main

test: install
	uv run pytest

typecheck: install
	uv run pyright