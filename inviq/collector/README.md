# Collector API

This API's responsibility is to receive new invoice ticket processing requests, which include:

- Ticket number (Service Notw ticket)
- File list (files attached to the original email)

## Development

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Setup

1. Install dependencies:

   ```bash
   make install
   ```

2. Run the development server:
   ```bash
   make dev
   ```

### VSCode Setup

**Install these extensions**

- [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)

**Virtual environment**

- The virtual environment created in `./venv` will not be detected properly if the `./collector` folder is not in the workspace root. To work around this, first create a new workspace and then manually add the `./collector` folder to the root.

### Testing

Run tests:

```bash
make test
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
