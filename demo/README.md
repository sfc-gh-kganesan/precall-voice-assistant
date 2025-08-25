# Quick start

From the `./demo` directory, run:

```sh
# install python dependencies
poetry install

# generate code from protos
make proto_gen

# initalize sqlite database
make db_init
```

In terminal A, run:

```sh
# start database grpc service
make db_run
```

In terminal B, run:

```sh
make uiapi_run
```

Finally, to test the uiapi service, run:

```sh
curl localhost:8010/workflows
```
