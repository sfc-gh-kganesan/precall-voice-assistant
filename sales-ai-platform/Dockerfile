# Sales AI Platform - Snowflake SPCS Deployment
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set working directory
WORKDIR /app

# Configure uv for optimal Docker builds
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies in a separate layer for better caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Copy application code
COPY app.py utils.py ./
COPY graphs/ ./graphs/

# Set Python path and environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI application with uvicorn
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

