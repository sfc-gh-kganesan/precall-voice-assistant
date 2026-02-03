.PHONY: install extract clean help

# Default file for testing
FILE ?= sample/sample_parsed.json

help:
	@echo "Document Extractor - Available commands:"
	@echo ""
	@echo "  make install     Install dependencies with uv"
	@echo "  make extract     Extract metadata from a file (use FILE=path/to/file)"
	@echo "  make clean       Remove build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make extract FILE=contract.txt"
	@echo "  make extract FILE=sample/sample_parsed.json"

install:
	uv sync

extract:
	uv run python -m document_extractor $(FILE)

clean:
	rm -rf __pycache__ .pytest_cache
	rm -rf document_extractor/__pycache__
	rm -rf baml_client/__pycache__
	rm -rf .venv
	rm -rf dist build *.egg-info
