.PHONY: db_init db_run db_clean proto_gen uiapi_run ui_run

proto_gen:
	cd protos && poetry run python -m grpc_tools.protoc -I. --pyi_out=../demo/db/grpc --python_out=../demo/db/grpc --grpc_python_out=../demo/db/grpc db.proto

	# Note this hack is needed to make the generated code relative imports work
	# This appears to be an issue with grpc_tools and python3
	# See discussion here: https://github.com/grpc/grpc/issues/9575
	sed -i '' 's/^\(import.*_pb2\)/from . \1/' demo/db/grpc/*.py

db_init:
	poetry run db init aura.db demo/db/sql/init.sql

db_run:
	poetry run db serve

db_clean:
	rm aura.db

uiapi_run:
	poetry run fastapi dev demo/ui_api.py --port 8010

ui_run:
	cd ui && npm run dev

