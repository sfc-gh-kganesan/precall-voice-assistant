.PHONY: install parse test clean help

# Default PDF for testing
PDF ?= sample.pdf

help:
	@echo "Document Parser - Available commands:"
	@echo ""
	@echo "  make install     Install dependencies with uv"
	@echo "  make parse       Parse a PDF (use PDF=path/to/file.pdf)"
	@echo "  make parse-text  Parse and output text only"
	@echo "  make test        Run tests"
	@echo "  make clean       Remove build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make parse PDF=invoice.pdf"
	@echo "  make parse PDF=invoice.pdf OUTPUT=result.json"
	@echo "  make parse-text PDF=invoice.pdf"

install:
	uv sync

parse:
ifdef OUTPUT
	uv run python -m document_parser $(PDF) -o $(OUTPUT)
else
	uv run python -m document_parser $(PDF)
endif

parse-text:
	uv run python -m document_parser $(PDF) --text-only

parse-fast:
	uv run python -m document_parser $(PDF) --skip-ocr

test:
	uv run pytest -v

clean:
	rm -rf __pycache__ .pytest_cache
	rm -rf document_parser/__pycache__
	rm -rf .venv
	rm -rf dist build *.egg-info
