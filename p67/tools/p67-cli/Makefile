.PHONY: build ci clean help install

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*##"; printf ""} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)

bin/p67: ## Build the p67 executable
	pnpm run build

build: bin/p67 ## Build the p67 executable

ci: ## Run CI validations
	pnpm run ci

clean: ## Remove built files
	rm -rf bin/p67

fix: ## Fix lint / formatting issues
	pnpm lint:fix
	pnpm format

install: build ## Install the p67 command in your path
	./install.sh
