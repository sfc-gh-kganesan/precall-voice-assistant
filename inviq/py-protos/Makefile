.phony: install gen

PROTO_DIR=../protos
PROTO_OUT=./src/py_protos

install:
	uv sync

gen: install
	uv run python -m grpc_tools.protoc \
		-I$(PROTO_DIR) \
		--python_out=$(PROTO_OUT) \
		--pyi_out=$(PROTO_OUT) \
		--grpc_python_out=$(PROTO_OUT) \
		$(PROTO_DIR)/*.proto

	# Note this hack is needed to make the generated code relative imports work
	# This appears to be an issue with grpc_tools and python3
	# See discussion here: https://github.com/grpc/grpc/issues/9575
	if [ "$$(uname -s)" = "Darwin" ]; then \
		sed -i '' 's/^\(import.*_pb2\)/from . \1/' $(PROTO_OUT)/*.py; \
	else \
		sed -i 's/^\(import.*_pb2\)/from . \1/' $(PROTO_OUT)/*.py; \
	fi