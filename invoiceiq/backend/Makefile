.PHONY: check fix format formatcheck install lint run dev test typecheck clean docker-build docker-run help

check: lint typecheck
	uv run ruff format --diff

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

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8001

dev: install
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

test: install
	uv run pytest

typecheck: install
	uv run pyright

clean:
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf app/__pycache__
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t invoiceiq-backend .

docker-run:
	docker run -p 8001:8001 --env-file .env invoiceiq-backend

help:
	@echo "Available commands:"
	@echo "  make check        - Run lint, typecheck, and format diff"
	@echo "  make fix          - Format code and fix linting issues"
	@echo "  make format       - Format code with ruff"
	@echo "  make formatcheck  - Check if code is formatted"
	@echo "  make install      - Install dependencies"
	@echo "  make lint         - Run ruff linter"
	@echo "  make run          - Run the server"
	@echo "  make dev          - Run with auto-reload"
	@echo "  make test         - Run tests"
	@echo "  make typecheck    - Run pyright type checker"
	@echo "  make clean        - Clean up cache files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run Docker container"


