FROM python:3.12-slim

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

WORKDIR /inviq/filestore

COPY ./py-protos /inviq/py-protos
COPY ./py-util /inviq/py-util

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./filestore/uv.lock,target=uv.lock \
    --mount=type=bind,source=./filestore/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY ./filestore /inviq/filestore

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Place executables in the environment at the front of the path
ENV PATH="/inviq/filestore/.venv/bin:$PATH"

# Python output is sent straight to terminal/logs without being first buffered
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uv", "run", "python", "run_dev.py"]
