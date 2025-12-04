.PHONY: fix build-harness

fix:
	pnpm lint:fix
	pnpm format

build-harness:
	docker build \
		--target runner \
		--build-arg SERVICE_NAME=harness \
		--build-arg SERVICE_PORT=3000 \
		-t p67/harness:latest \
		.
