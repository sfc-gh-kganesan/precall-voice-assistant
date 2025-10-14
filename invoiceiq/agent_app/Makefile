.PHONY: help run build-local run-local test-local build-spcs login-spcs push-spcs langgraph-studio clean

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
		-d '{"invoice_id": "74f1cb0b-07ba-4a6f-8c71-4c0dc212b90e"}'

build-spcs: ## Build Docker image for SPCS (linux/amd64)
	docker build --rm --platform linux/amd64 -t $(SPCS_IMAGE) .

login-spcs: ## Login to Snowflake image registry (set CONNECTION_NAME=<name>)
	snow spcs image-registry login -c "$(CONNECTION_NAME)"

push-spcs: ## Push Docker image to SPCS image repository
	docker push $(SPCS_IMAGE)

langgraph-studio: ## Run LangGraph Studio
	source .venv/bin/activate && langgraph dev

clean: ## Remove local Docker images
	docker rmi -f $(LOCAL_IMAGE) 2>/dev/null || true
	docker rmi -f $(SPCS_IMAGE) 2>/dev/null || true

