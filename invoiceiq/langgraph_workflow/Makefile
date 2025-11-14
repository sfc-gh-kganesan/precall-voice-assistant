.PHONY: help run build-local run-local test-local build-spcs login-spcs push-spcs langgraph-studio clean eval-csv eval-snowflake

# Variables
IMAGE_NAME := invoiceiq-agent
IMAGE_TAG := latest
LOCAL_IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)
SPCS_REGISTRY := sfengineering-aifde.registry.snowflakecomputing.com
SPCS_IMAGE := $(SPCS_REGISTRY)/invoiceiq/service/image_repository/$(IMAGE_NAME):$(IMAGE_TAG)
PORT := 8000

# Default connection name for SPCS login (can be overridden)
CONNECTION_NAME ?= default

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

run: ## Run the FastAPI app locally with uv
	uv run python -m app.main

build-local: ## Build Docker image for local use
	docker build -t $(LOCAL_IMAGE) .

run-local: ## Run Docker container locally (requires .env file)
	docker run --rm --env-file .env -p $(PORT):$(PORT) $(LOCAL_IMAGE)

test-local: ## Send a test request to the local API
		curl -X POST "http://localhost:$(PORT)/process" \
			-H "Content-Type: application/json" \
			-d '{"target_table": "INVOICEIQ.SERVICE.INVOICES", "invoice_id": "2b0771cd-61b4-4ce7-9e29-5bcd9b19a568", "relative_path":"bfb86d4683af4210be180c673c621076_50b88f1f9ebe4317bf3892f66d4c0c74_invoice_01.pdf", "stage_name": "INVOICEIQ.SERVICE.TICKET_ATTACHMENTS"}'

build-spcs: ## Build Docker image for SPCS (linux/amd64)
	docker build --rm --platform linux/amd64 -t $(SPCS_IMAGE) .

login-spcs: ## Login to Snowflake image registry (set CONNECTION_NAME=<name>)
	snow spcs image-registry login -c "$(CONNECTION_NAME)"

push-spcs: ## Push Docker image to SPCS image repository
	docker push $(SPCS_IMAGE)

langgraph-studio: ## Run LangGraph Studio
	source .venv/bin/activate && langgraph dev

eval-csv: ## Run LangSmith evals using the bundled CSV test set
	uv run evals/eval.py --eval-csv-file evals/data/test_set.csv --eval-target-table INVOICEIQ.SERVICE.INVOICES --eval-stage-name INVOICEIQ.SERVICE.TICKET_ATTACHMENTS

eval-snowflake: ## Run LangSmith evals by pulling rows from a Snowflake table
	uv run evals/eval.py --eval-snowflake-table INVOICEIQ.SERVICE.TESTDATA --eval-target-table INVOICEIQ.SERVICE.INVOICES_EVALUATION --eval-stage-name INVOICEIQ.SERVICE.TICKET_ATTACHMENTS

clean: ## Remove local Docker images
	docker rmi -f $(LOCAL_IMAGE) 2>/dev/null || true
	docker rmi -f $(SPCS_IMAGE) 2>/dev/null || true

