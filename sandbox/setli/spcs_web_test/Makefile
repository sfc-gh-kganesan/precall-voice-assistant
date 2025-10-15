.phony: check fix format install lint dev test typecheck

check: lint typecheck
	uv run ruff format --diff

fix: format
	uv run ruff check --fix

format: install
	uv run ruff format

install:
	uv sync

lint: install
	uv run ruff check

dev: install
	uv run fastapi dev ./app/main.py

test: install
	uv run pytest

typecheck: install
	uv run pyright
