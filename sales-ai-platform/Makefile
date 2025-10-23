-include .env
export

# Build connection flag once (empty if "default", otherwise --connection NAME)
CONNECTION_FLAG = $(if $(filter-out default,$(SNOW_CONNECTION)),--connection $(SNOW_CONNECTION),)

.DEFAULT_GOAL := help

.PHONY: studio api dev help deploy deploy-service deploy-functions build push setup-infra service-status service-logs service-drop clean check-env registry-login

help: ## Show this help message
	@echo "Sales AI Platform"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ""

# Development
dev: ## Start dev server with auto-reload
	@uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload

api: ## Start production server
	@uv run uvicorn app:app --host 0.0.0.0 --port 8000

studio: ## Open LangGraph Studio
	@langgraph dev

check-env: ## Validate .env and show config
	@echo "🔍 Checking environment configuration..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found"; \
		echo ""; \
		echo "Create .env from template:"; \
		echo "  cp .env.example .env"; \
		echo ""; \
		echo "Then fill in all required values."; \
		exit 1; \
	fi
	@echo "📋 Validating required variables..."
	@MISSING=""; \
	for var in SNOW_CONNECTION COMPUTE_POOL DATABASE SCHEMA STAGE IMAGE_REPOSITORY IMAGE_NAME IMAGE_TAG SERVICE_NAME CONTAINER_NAME; do \
		if ! grep -q "^$$var=..*" .env 2>/dev/null; then \
			MISSING="$$MISSING $$var"; \
		fi; \
	done; \
	if [ -n "$$MISSING" ]; then \
		echo "❌ Missing or empty required variables:$$MISSING"; \
		echo ""; \
		echo "Edit .env and set all required values."; \
		exit 1; \
	fi
	@echo "✅ Environment configuration is valid"
	@echo ""
	@echo "Configuration:"
	@echo "  Connection:   $$SNOW_CONNECTION"
	@echo "  Database:     $$DATABASE"
	@echo "  Schema:       $$SCHEMA"
	@echo "  Service:      $$SERVICE_NAME"
	@echo "  Container:    $$CONTAINER_NAME"
	@echo "  Image:        $$IMAGE_NAME:$$IMAGE_TAG"
	@echo "  Compute Pool: $$COMPUTE_POOL"

registry-login: check-env ## Login to Snowflake image registry
	@echo "🔐 Logging into Snowflake image registry..."
	@snow spcs image-registry login $(CONNECTION_FLAG)
	@echo "✅ Login successful"

setup-infra: check-env ## Create Snowflake resources
	@echo "🏗️  Setting up Snowflake infrastructure..."
	@echo "Creating database: $$DATABASE"; \
	snow object create database name=$$DATABASE --if-not-exists $(CONNECTION_FLAG); \
	echo "Creating schema: $$SCHEMA"; \
	snow object create schema name=$$SCHEMA --database $$DATABASE --if-not-exists $(CONNECTION_FLAG); \
	echo "Creating compute pool: $$COMPUTE_POOL"; \
	cd release && snow spcs compute-pool deploy $(CONNECTION_FLAG) || echo "⚠️  Compute pool may already exist"; \
	echo "Creating image repository: $$IMAGE_REPOSITORY"; \
	snow spcs image-repository deploy $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA || echo "⚠️  Image repository may already exist"; \
	echo "✅ Infrastructure setup complete"

deploy: check-env registry-login setup-infra build push deploy-service deploy-functions ## 🚀 Full deployment pipeline
	@echo ""
	@echo "✅ 🎉 Deployment complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  make service-status  - Check service status"
	@echo "  make service-logs    - View service logs"
	@echo ""
	@echo "Test in Snowflake:"
	@echo "  SELECT $$DATABASE.$$SCHEMA.sales_ai_greeting('Alice');"
	@echo ""

build: check-env ## Build Docker image
	@echo "🐳 Building Docker image..."
	@echo "Getting image repository URL..."; \
	REPO_URL=$$(snow spcs image-repository url $$IMAGE_REPOSITORY $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA); \
	echo "Repository URL: $$REPO_URL"; \
	cd release && docker build --rm --platform linux/amd64 -t $$REPO_URL/$$IMAGE_NAME:$$IMAGE_TAG ../. && \
	echo "✅ Built: $$REPO_URL/$$IMAGE_NAME:$$IMAGE_TAG"

push: check-env ## Push image to Snowflake registry
	@echo "📤 Pushing to Snowflake image repository..."
	@REPO_URL=$$(snow spcs image-repository url $$IMAGE_REPOSITORY $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA); \
	echo "Pushing $$REPO_URL/$$IMAGE_NAME:$$IMAGE_TAG..."; \
	docker push $$REPO_URL/$$IMAGE_NAME:$$IMAGE_TAG && \
	echo "✅ Pushed successfully"

deploy-service: check-env ## Deploy SPCS service
	@echo "🚢 Deploying service to Snowflake..."
	@REPO_URL=$$(snow spcs image-repository url $$IMAGE_REPOSITORY $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA); \
	echo "Updating service_spec.yaml with image path..."; \
	sed -i.bak "s|image:.*|image: $$REPO_URL/$$IMAGE_NAME:$$IMAGE_TAG|" release/service_spec.yaml && rm -f release/service_spec.yaml.bak; \
	echo "Dropping existing service (if exists)..."; \
	snow spcs service drop $$SERVICE_NAME $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA 2>/dev/null || echo "⚠️  No existing service to drop"; \
	echo "Deploying service..."; \
	cd release && snow spcs service deploy $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA; \
	echo "Waiting for service to initialize..."; \
	sleep 5; \
	echo "✅ Service deployed"

deploy-functions: check-env ## Deploy SQL functions
	@echo "📝 Deploying Snowflake functions..."
	@cd release && envsubst < function.sql > function.sql.tmp && \
	snow sql -q "!source function.sql.tmp" $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA && \
	rm -f function.sql.tmp; \
	echo "✅ Functions deployed"

service-status: check-env ## Check service status
	@echo "📊 Checking service status..."
	@snow spcs service status $$SERVICE_NAME $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA

service-logs: check-env ## View service logs (instance 0)
	@echo "📋 Fetching service logs..."
	@snow spcs service logs $$SERVICE_NAME $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA --container-name $$CONTAINER_NAME --instance-id 0

service-drop: check-env ## Drop service
	@echo "🗑️  Dropping service..."
	@snow spcs service drop $$SERVICE_NAME $(CONNECTION_FLAG) --database $$DATABASE --schema $$SCHEMA

clean: ## Clean Docker images and cache
	@echo "🧹 Cleaning up..."
	@docker images | grep sales-ai-platform | awk '{print $$3}' | xargs docker rmi -f 2>/dev/null || true
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@echo "✓ Cleanup complete"
