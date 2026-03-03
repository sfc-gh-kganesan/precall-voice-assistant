# ── Stage 1: Build the Go supervisor binary ──────────────────────────
FROM golang:1.24-alpine AS go-builder

WORKDIR /build
COPY go.mod ./
COPY main.go ./

RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o p67-runner .

# ── Stage 2: Python runtime ──────────────────────────────────────────
FROM python:3.11-slim AS runtime

# System deps needed by numpy / snowflake-connector-python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache friendly)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Go supervisor binary
COPY --from=go-builder /build/p67-runner /usr/local/bin/p67-runner

# Copy the Python host script
COPY host.py /app/host.py

# Default env vars
ENV P67_HOST_SCRIPT=/app/host.py

# The runner expects a workflow dir as its first argument.
# In production this will be overridden by the orchestrator.
ENTRYPOINT ["p67-runner"]
