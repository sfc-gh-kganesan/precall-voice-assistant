InvoiceIQ
=========

# Running locally

**STEP 1**: Create the `./collector/.env` file by running:

```sh
cp ./collector/.env{.example,}
```

Add the Programmatic Access Token to the `./collector/.env` file. This value can be found in the `ENG - FDE Dev` 1password vault, 
under the entry `[SFENGINEERING.AIFDE] svc-invoiceiq`.

**STEP 2**: Run the service with docker compose:

```sh
docker compose up --build
```

Test that the collector service is running by curling the healthcheck endpoint:

```sh
curl localhost:8000/healthcheck
```
