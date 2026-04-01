SNOW_CONNECTION?=default
SNOW_REPO=sfengineering-aifde.registry.snowflakecomputing.com/p67_src/core/img_repo
DASH_REPO=sfengineering-aifde.registry.snowflakecomputing.com/p67_src/dash/img_repo
CONTROLD_IMAGE=controld
DASH_IMAGE=p67-dash
DASH_DIR=tools/dash
TAG_FILE=.build-tag
RUNNER_PLATFORM_FILE=containers/runner/runner-platform.json
RUNNER_PYTHON_VERSION := $(shell jq -r .python_version $(RUNNER_PLATFORM_FILE))
RUNNER_DOCKER_PLATFORM := $(shell jq -r .docker_platform $(RUNNER_PLATFORM_FILE))
.PHONY: help build build-controld build-dash ci deploy describe dev fix \
ensure-encryption-key init-provider-account install-cli list-services login logs logs-dash push push-controld push-dash \
url dash-url dbmigrate cert spcs-data-secret spcs-snowflake-eai

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*##"; printf ""} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)

build: build-controld build-dash ## Build Docker images

build-controld: ## Build controld Docker image for linux/amd64
	$(eval TAG := $(shell git rev-parse --short HEAD)-$(shell date +%s))
	@echo "$(TAG)" > $(TAG_FILE)
	docker build \
		--platform $(RUNNER_DOCKER_PLATFORM) \
		--target runner \
		--build-arg SERVICE_NAME=controld \
		--build-arg SERVICE_PORT=8000 \
		--build-arg PYTHON_VERSION=$(RUNNER_PYTHON_VERSION) \
		-t $(CONTROLD_IMAGE):$(TAG) \
		.
	@echo "Built $(CONTROLD_IMAGE):$(TAG)"

build-dash: ## Build dashboard frontend and Docker image for linux/amd64
	$(eval TAG := $(shell git rev-parse --short HEAD)-$(shell date +%s))
	@echo "$(TAG)" > $(TAG_FILE)
	cd $(DASH_DIR) && pnpm install && pnpm run build
	docker build \
		--platform linux/amd64 \
		-t $(DASH_IMAGE):$(TAG) \
		$(DASH_DIR)
	@echo "Built $(DASH_IMAGE):$(TAG)"

ci:
	pnpm run ci

dbmigrate:
	$(MAKE) -C ./packages/db migrate

deploy: login build push ## Deploy to Snowflake (login, build, push, and run app)
	snow app run -c $(SNOW_CONNECTION)
	@echo "Granting application roles to account roles..."
	snow sql -q "GRANT APPLICATION ROLE P67.app_admin TO ROLE P67_PROVIDER_ADMIN_RL" -c $(SNOW_CONNECTION) || true
	snow sql -q "GRANT APPLICATION ROLE P67.app_user TO ROLE P67_USER_RL" -c $(SNOW_CONNECTION) || true
	@echo "Application role grants complete."

describe: ## Describe the p67.app.controld service
	snow spcs service describe p67.app.controld --format json -c $(SNOW_CONNECTION)

dev: ensure-encryption-key ## Start local development environment with Docker Compose
	$(MAKE) -C packages/db init
	$(MAKE) -C services/controld init
	docker compose up --build -d
	@echo "Waiting for postgres to be ready..."
	@until docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Postgres is ready!"
	$(MAKE) -C packages/db deploy
	docker compose logs -f

ensure-encryption-key: ## Generate ENCRYPTION_KEY in .env if not set
	@grep -q '^ENCRYPTION_KEY=.' .env 2>/dev/null || { \
		echo "Generating ENCRYPTION_KEY..."; \
		grep -v '^ENCRYPTION_KEY=' .env > .env.tmp 2>/dev/null || true; \
		echo "ENCRYPTION_KEY=$$(openssl rand -base64 32)" >> .env.tmp; \
		mv .env.tmp .env; \
		echo "ENCRYPTION_KEY added to .env"; \
	}


fix: ## Fix linting and formatting issues
	pnpm lint:fix
	pnpm format

init-provider-account: ## Initialize provider account with setup SQL
	snow sql -f "./ops/provider_account_setup.sql" -c $(SNOW_CONNECTION)

install-cli: ## Install the P67 CLI tool
	pnpm install --filter "@p67/workflow-sdk" --filter "@p67/cli"
	pnpm --filter "@p67/workflow-sdk" run build
	make clean install -C ./tools/p67-cli

list: ## List all services in p67 database
	snow spcs service list --format json --in database p67 -c $(SNOW_CONNECTION)

login: ## Log in to Snowflake image registry
	snow spcs image-registry login -c $(SNOW_CONNECTION)

logs: ## show spcs service logs
	snow spcs service logs p67.app.controld --container-name controld --instance-id 0 -c $(SNOW_CONNECTION)

logs-dash: ## show dashboard spcs service logs
	snow spcs service logs p67.app.dashboard --container-name dashboard --instance-id 0 -c $(SNOW_CONNECTION)

push: push-controld push-dash ## Push Docker images to Snowflake registry

push-controld: ## Tag and push controld image to Snowflake registry
	$(eval TAG := $(shell cat $(TAG_FILE) 2>/dev/null || echo latest))
	docker tag $(CONTROLD_IMAGE):$(TAG) $(SNOW_REPO)/$(CONTROLD_IMAGE):$(TAG)
	docker tag $(CONTROLD_IMAGE):$(TAG) $(SNOW_REPO)/$(CONTROLD_IMAGE):latest
	docker push $(SNOW_REPO)/$(CONTROLD_IMAGE):$(TAG)
	docker push $(SNOW_REPO)/$(CONTROLD_IMAGE):latest
	sed -i '' 's|image: /p67_src/core/img_repo/controld:.*|image: /p67_src/core/img_repo/controld:$(TAG)|' native-app/controld_service_spec.yml
	@echo "Pushed $(CONTROLD_IMAGE):$(TAG) and updated controld_service_spec.yml"

push-dash: ## Tag and push dashboard image to Snowflake registry
	$(eval TAG := $(shell cat $(TAG_FILE) 2>/dev/null || echo latest))
	docker tag $(DASH_IMAGE):$(TAG) $(DASH_REPO)/$(DASH_IMAGE):$(TAG)
	docker tag $(DASH_IMAGE):$(TAG) $(DASH_REPO)/$(DASH_IMAGE):latest
	docker push $(DASH_REPO)/$(DASH_IMAGE):$(TAG)
	docker push $(DASH_REPO)/$(DASH_IMAGE):latest
	sed -i '' 's|image: /p67_src/dash/img_repo/p67-dash:.*|image: /p67_src/dash/img_repo/p67-dash:$(TAG)|' native-app/dashboard_service_spec.yml
	@echo "Pushed $(DASH_IMAGE):$(TAG) and updated dashboard_service_spec.yml"

url: ## Print the ingress URL for the running SPCS service
	snow spcs service list-endpoints p67.app.controld \
		-c $(SNOW_CONNECTION) \
		--format json | \
		jq '.[] | select(.name == "web") | .ingress_url' -r | \
		xargs -I {} echo "https://{}"

dash-url: ## Print the ingress URL for the dashboard service
	snow spcs service list-endpoints p67.app.dashboard \
		-c $(SNOW_CONNECTION) \
		--format json | \
		jq '.[] | select(.name == "web") | .ingress_url' -r | \
		xargs -I {} echo "https://{}"


spcs-data-secret: ## Generate and create the p67 encryption_key Snowflake Secret and bind to app (idempotent)
	@snow sql -q "DESCRIBE SECRET p67_src.core.p67_encryption_key" \
	  -c $(SNOW_CONNECTION) > /dev/null 2>&1 && { \
	    echo "Secret p67_src.core.p67_encryption_key already exists — skipping creation."; \
	} || { \
	    KEY=$$(openssl rand -base64 32); \
	    echo "Creating Snowflake secret p67_src.core.p67_encryption_key..."; \
	    snow sql -q "USE SCHEMA p67_src.core; CREATE SECRET p67_encryption_key TYPE = GENERIC_STRING SECRET_STRING = '$$KEY'" \
	      -c $(SNOW_CONNECTION) > /dev/null; \
	    echo "Secret created."; \
	}
	@echo "Binding encryption_key reference to app..."
	@snow sql -q "CALL p67.v1.register_reference('encryption_key', 'ADD', SYSTEM\$$REFERENCE('SECRET', 'p67_src.core.p67_encryption_key', 'PERSISTENT', 'READ'))" \
	  -c $(SNOW_CONNECTION) > /dev/null
	@echo "encryption_key bound to app."
	@echo "Reinitializing service with new spec..."
	@snow sql -q "CALL p67.v1.init()" -c $(SNOW_CONNECTION) > /dev/null
	@echo "Done."

spcs-snowflake-eai: ## Bind the Snowflake egress EAI to the app and reinitialize
	@echo "Binding snowflake_egress_eai reference to app..."
	@snow sql -q "CALL p67.v1.register_reference('snowflake_egress_eai', 'ADD', SYSTEM\$$REFERENCE('EXTERNAL_ACCESS_INTEGRATION', 'p67_snowflake_egress_eai', 'PERSISTENT', 'USAGE'))" \
	  -c $(SNOW_CONNECTION) > /dev/null
	@echo "snowflake_egress_eai bound to app."
	@echo "Reinitializing service with new spec..."
	@snow sql -q "CALL p67.v1.init()" -c $(SNOW_CONNECTION) > /dev/null
	@echo "Done."

cert: ## Generate locally-trusted HTTPS certificates using mkcert
	@command -v mkcert >/dev/null 2>&1 || { echo "mkcert not found. Install with: brew install mkcert"; exit 1; }
	@mkdir -p .certs
	@mkcert -install 2>/dev/null || true
	@mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1
	@echo "Certificates generated in .certs/"
	@echo "  - .certs/localhost.pem (certificate)"
	@echo "  - .certs/localhost-key.pem (private key)"
