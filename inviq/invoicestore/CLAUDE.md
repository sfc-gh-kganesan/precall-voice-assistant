# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the InvoiceStore service, a gRPC-based service that is responsible for storing data related to invoices. This service handles:

- Meta data associated with invoice submissions
- Lifecycle processing for the invoices

## Development Commands

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Setup

```bash
make install
```

### Running the Application

```bash
# Development server
make dev
```

### Testing

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/test_main.py

# Run with verbose output
uv run pytest -v
```

### Code Quality

```bash
# Format code (write changes)
make format

# Check formatting (do not write changes)
make formatcheck

# Lint code
make lint

# Type checking
make typecheck
```

## Architecture

- **Framework**: gRPC with asyncio
- **Structure**: Simple gRPC service with file upload streaming
- **Package Structure**:
  - `app/main.py` - Main gRPC server and Invoice service implementation
- **Configuration**: pyproject.toml with ruff formatting/linting rules and pyright type checking

## gRPC Service

- **Port**: 50051
- **Service**: FileStore

## Ruff Configuration

The project uses strict linting with:

- Line length: 120 characters
- Target Python version: 3.12
- Enabled rules: pycodestyle errors/warnings, pyflakes, isort, flake8-bugbear, flake8-comprehensions, pyupgrade
- Format style: double quotes, space indentation
