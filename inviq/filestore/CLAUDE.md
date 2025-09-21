# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the FileStore service, a gRPC-based file upload service that accepts file uploads through streaming. The service handles:

- File uploads via gRPC streaming
- File storage in a local uploads directory
- Basic file validation and error handling

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
  - `app/main.py` - Main gRPC server and FileStore service implementation
  - `app/filestore.proto` - Protocol buffer definition
  - `app/filestore_pb2.py` - Generated protobuf code (auto-generated)
  - `app/filestore_pb2_grpc.py` - Generated gRPC code (auto-generated)
  - `tests/` - Test suite using pytest
- **Configuration**: pyproject.toml with ruff formatting/linting rules and pyright type checking

## gRPC Service

- **Port**: 50051
- **Service**: FileStore
- **Method**: UploadFile (streaming)
- **Upload Directory**: ./uploads/

## Ruff Configuration

The project uses strict linting with:

- Line length: 88 characters
- Target Python version: 3.12
- Enabled rules: pycodestyle errors/warnings, pyflakes, isort, flake8-bugbear, flake8-comprehensions, pyupgrade
- Format style: double quotes, space indentation