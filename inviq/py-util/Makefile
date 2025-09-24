.phony: check fix format install lint typecheck

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

typecheck: install
	uv run pyright