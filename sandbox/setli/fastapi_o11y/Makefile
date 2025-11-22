.phony: check fix format install lint dev test typecheck jaeger

.env:
	cp .env.example .env

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

jaeger:
	docker run -it --rm --name jaeger \
	  -p 16686:16686 \
	  -p 4417:4317 \
	  -p 4418:4318 \
	  -p 5778:5778 \
	  -p 9411:9411 \
	  cr.jaegertracing.io/jaegertracing/jaeger:2.11.0
