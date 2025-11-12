# Multi-stage build for Rust application in SPCS
FROM rust:1.75-slim as builder

WORKDIR /app

# Install dependencies for building
RUN apt-get update && \
    apt-get install -y pkg-config libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy manifest files
COPY Cargo.toml Cargo.lock* ./

# Create a dummy main.rs to cache dependencies
RUN mkdir -p src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release || true && \
    rm -rf src

# Copy actual source code
COPY src ./src

# Build the application
RUN cargo build --release

# Runtime stage - smaller image
FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies including Python for Snowflake CLI
RUN apt-get update && \
    apt-get install -y \
        ca-certificates \
        libssl3 \
        python3 \
        python3-pip \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Install Snowflake CLI for stage operations
RUN pip3 install --no-cache-dir snowflake-cli-labs --break-system-packages

# Copy the built binary from builder stage
COPY --from=builder /app/target/release/spcs-api-demo /app/spcs-api-demo

# Make sure binary is executable
RUN chmod +x /app/spcs-api-demo

# Set the entrypoint
ENTRYPOINT ["/app/spcs-api-demo"]

