# Collector API

This API's responsibility is to receive new invoice ticket processing requests, which include:

- Ticket number (Service Now ticket)
- File list (files attached to original email from vendor)

## Development

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Setup

1. Install dependencies:

   ```bash
   make install
   ```

2. Run the development server:
   ```bash
   # on host OS...
   make dev

   # ...or in docker container - run from parent directory
   docker compose up --build
   ```

### Code Quality

Check if code is properly formatted. Print diff if not. Do not write any changes to the files:

```bash
make formatcheck
```

Format code:

```bash
make format
```

Lint code:

```bash
make lint
```

Type check:

```bash
make typecheck
```

### Github actions

Install [`act`](https://nektosact.com/installation/gh.html) to test actions locally:

```bash
gh extension install https://github.com/nektos/gh-act
```

### Build and deploy image to SPCS

## Prerequisites

* [`docker`](https://docs.docker.com/engine/install/) container engine
* [`jq`](https://github.com/jqlang/jq) CLI tool installed and available in your path
* [`snow`](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) CLI tool installed and configured with a default connection setup to the Snowflake account where the service will be deployed (sfengineering-aifde). If you want to use a non-default connection with the `snow` command, please export the `INVOICEIQ_SNOW_CONNECT` environment variable. For example, to use the connection `invoiceiq`, you would export `INVOICEIQ_SNOW_CONNECT="-c invoiceiq"`.

This script will build the image with docker, push it to the remote repository, and restart the SPCS service to pick up the new image:

```bash
./release/build_and_deploy.sh
```

