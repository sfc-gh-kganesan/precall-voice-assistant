# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Extractor service, a gRPC-based service that accepts a file as input and returns a list of extracted fields as output. The service relies on an LLM based extraction process to read the file (typically a PDF), identify a list of fields in the file, and return those in the response. The service handles:

- File upload via gRPC streaming
- Taking this file and uploading it to a temporary Snowflake stage
- Running the Snowflake AISQL ai_extract() function on the file in the stage
- Processing the output and returning to the caller

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

## gRPC Service

- **Port**: 50051
- **Service**: Extractor

## Ruff Configuration

The project uses strict linting with:

- Line length: 120 characters
- Target Python version: 3.12
- Enabled rules: pycodestyle errors/warnings, pyflakes, isort, flake8-bugbear, flake8-comprehensions, pyupgrade
- Format style: double quotes, space indentation
