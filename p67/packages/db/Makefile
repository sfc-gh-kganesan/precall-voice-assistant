.PHONY: help init sql diff deploy

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.env:
	cp .env.example .env

init: .env ## Create .env file from .env.example

sql: ## Generate SQL schema from Prisma schema (from empty database)
	pnpm prisma migrate diff --from-empty --to-schema prisma/schema.prisma --script

diff: ## Show SQL diff between current database and Prisma schema
	pnpm prisma migrate diff --from-config-datasource --to-schema prisma/schema.prisma --script

deploy: ## Apply all pending migrations to the database
	pnpm prisma migrate deploy
	pnpm prisma generate

migrate: ## Run migrate for dev to generate migration scripts
	pnpm prisma migrate dev

shell: ## Open postgres shell
	source .env && psql $$DATABASE_URL
