.phony: check dev fix format install lint run test typecheck

check: lint typecheck
	uv run ruff format --diff

dev: install
	uv run langgraph dev

fix: format
	uv run ruff check --fix

format: install
	uv run ruff format

install:
	uv sync

lint: install
	uv run ruff check

run: install
	uv run python -m app.main

test: install
	uv run pytest

typecheck: install
	uv run pyright
