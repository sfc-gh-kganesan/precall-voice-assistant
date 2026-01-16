.PHONY: install extract batch clean help

help:
	@echo "Invoice Extractor Commands:"
	@echo ""
	@echo "  make install          - Install dependencies"
	@echo "  make extract PDF=...  - Extract from PDF and save to results/"
	@echo "  make batch DIR=...    - Batch extract all PDFs in directory"
	@echo "  make clean            - Remove results and cache"
	@echo ""
	@echo "Examples:"
	@echo "  make extract PDF=invoice.pdf"
	@echo "  make batch DIR=invoices/"
	@echo ""

install:
	uv pip install -e .

extract:
	@if [ -z "$(PDF)" ]; then \
		echo "Usage: make extract PDF=path/to/invoice.pdf"; \
		exit 1; \
	fi
	uv run python -m app.main extract $(PDF) --output results/$$(basename $(PDF) .pdf).json

batch:
	@if [ -z "$(DIR)" ]; then \
		echo "Usage: make batch DIR=path/to/invoices/"; \
		exit 1; \
	fi
	uv run python -m app.main batch $(DIR) --output results/

clean:
	rm -rf results/*.json
	rm -rf __pycache__ app/__pycache__
	rm -rf .pytest_cache

