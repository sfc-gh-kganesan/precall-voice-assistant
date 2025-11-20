FROM python:3.11-slim

LABEL maintainer="Customer Experience Engineering <cxe-team@snowflake.com>"
LABEL description="External-Facing Web Agent Backend - Voice and Text Support with Phoenix Tracing"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv sync

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run with uv
CMD ["uv", "run", "uvicorn", "external_agent_api:app", "--host", "0.0.0.0", "--port", "8003"]
