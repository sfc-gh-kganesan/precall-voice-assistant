.phony: check dbclean dbinit dbshell fix format install lint dev test typecheck

dbfile=./invoicestore.db

check: lint typecheck
	uv run ruff format --diff

dbclean:
	rm $(dbfile)

dbinit:
	sqlite3 $(dbfile) < ./sql/init.sql -echo -bail

dbshell:
	sqlite3 $(dbfile)

fix: format
	uv run ruff check --fix

format: install
	uv run ruff format

install:
	uv sync

lint: install
	uv run ruff check

dev: install
	uv run python run_dev.py

test: install
	uv run pytest

typecheck: install
	uv run pyright
