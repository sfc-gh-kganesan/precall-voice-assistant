dbfile=./demo.db

.PHONY: dbclean dbinit dbrun dbshell protogen

dbclean:
	rm $(dbfile)

dbinit:
	sqlite3 $(dbfile) < ./sql/init.sql -echo -bail

dbrun:
	poetry run db serve

dbshell:
	sqlite3 $(dbfile)

protogen:
	cd protos && poetry run python -m grpc_tools.protoc -I. --pyi_out=../demo/db/grpc --python_out=../demo/db/grpc --grpc_python_out=../demo/db/grpc db.proto

	# Note this hack is needed to make the generated code relative imports work
	# This appears to be an issue with grpc_tools and python3
	# See discussion here: https://github.com/grpc/grpc/issues/9575
	sed -i '' 's/^\(import.*_pb2\)/from . \1/' demo/db/grpc/*.py

