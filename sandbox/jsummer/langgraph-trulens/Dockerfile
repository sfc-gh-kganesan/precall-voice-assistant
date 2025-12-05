# MVP Dockerfile for LangGraph Service Function
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

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
COPY model.py graph.py utils.py metrics.py prompts.py evals.py ./

# Set Python path and environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

# Run the evaluation script
CMD ["uv", "run", "evals.py"]