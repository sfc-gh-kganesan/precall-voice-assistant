.phony: check dbclean dbinit dbshell fix format formatcheck install lint dev test typecheck

dbfile=./filestore.db

check: formatcheck lint typecheck

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