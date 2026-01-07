.PHONY: help init install

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.env:
	cp .env.example .env

init: .env install ## Initialize dependencies and configuration files. Run this first.

install: ## Reinstall node dependencies.
	pnpm install
