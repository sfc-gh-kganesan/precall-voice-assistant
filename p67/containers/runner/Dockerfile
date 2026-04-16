# syntax=docker/dockerfile:1
#
# p67-runner: sandboxed workflow executor
#
# Supports both Python and TypeScript workflows. The Go supervisor
# auto-detects the language from the workflow directory (main.py vs index.js)
# and execs the corresponding host process.
#
# Build context must be the monorepo root:
#   docker build -f containers/runner/Dockerfile -t p67-runner .

# ── Stage 1: Build the Go supervisor binary ──────────────────────────
FROM golang:1.24-alpine AS go-builder

WORKDIR /build
COPY containers/runner/go.mod ./
COPY containers/runner/main.go ./
COPY containers/runner/detect.go ./

RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o p67-runner .

# ── Stage 2: Build TypeScript (controld host + deps) ─────────────────
FROM node:20-alpine AS node-builder

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

# Copy workspace config + lockfile (layer cache friendly)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.json ./
COPY packages ./packages
COPY services ./services

# Install all deps and build the monorepo
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
RUN pnpm run build

# Deploy controld into a standalone directory with all production deps
# resolved (no workspace symlinks). This gives us a flat node_modules
# that works outside the monorepo.
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm --filter=@p67/controld deploy --legacy --prod /deployed

# ── Stage 3: Runtime ─────────────────────────────────────────────────
FROM node:20-slim AS runtime

# Default fallback — the canonical value is in runner-platform.json,
# passed via --build-arg by the Makefile. This default exists so bare
# `docker build` invocations don't fail with an empty variable.
ARG PYTHON_VERSION=3.11

# Python runtime for Python workflows (g++ needed to build snowflake-connector-python)
# curl needed for Cortex Code installer
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python${PYTHON_VERSION} python${PYTHON_VERSION}-dev \
        python3-pip python${PYTHON_VERSION}-venv \
        g++ curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python host + deps
COPY containers/runner/requirements.txt ./
COPY packages/workflow-sdk-python/p67_sdk /app/p67_sdk
RUN python${PYTHON_VERSION} -m pip install --no-cache-dir --break-system-packages -r requirements.txt \
    && apt-get purge -y --auto-remove python${PYTHON_VERSION}-dev g++ \
    && rm -rf /var/lib/apt/lists/*

COPY containers/runner/host.py /app/host.py
COPY containers/runner/host_gs.py /app/host_gs.py

# Install Cortex Code (coco) CLI
# The standard install script executes the binary to verify the install, which
# fails under QEMU/Rosetta emulation when building linux/amd64 on arm64 Macs
# (SIGILL, exit code 132). If this is fixed upstream, restore the original:
#
#   RUN curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | SKIP_PODMAN=1 sh
#
# Until then, we do a direct download-and-extract that skips binary execution.
# S3 URL is extracted from the install script so it stays in sync.
RUN set -e \
    && INSTALL_SCRIPT=$(curl -fsSL https://ai.snowflake.com/static/cc-scripts/install.sh) \
    && S3_BUCKET=$(echo "$INSTALL_SCRIPT" | grep 'S3_BUCKET=' | grep -v dev | head -1 | sed 's/.*"\(.*\)".*/\1/') \
    && S3_PREFIX=$(echo "$INSTALL_SCRIPT" | grep 'S3_PREFIX=' | head -1 | sed 's/.*"\(.*\)".*/\1/') \
    && S3_BASE="https://${S3_BUCKET}/${S3_PREFIX}" \
    && CHANNEL="stable" \
    && VERSION=$(curl -fsSL "${S3_BASE}/${CHANNEL}_version.txt" | tr -d '[:space:]') \
    && ENCODED_VERSION=$(echo "$VERSION" | sed 's/+/%2B/g') \
    && MANIFEST_URL="${S3_BASE}/${ENCODED_VERSION}/manifest.json" \
    && ARCH=$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/') \
    && TAR_NAME=$(curl -fsSL "$MANIFEST_URL" | \
         node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')); \
                   console.log(d.packages.linux['${ARCH}'].name)") \
    && ENCODED_TAR=$(echo "$TAR_NAME" | sed 's/+/%2B/g') \
    && TAR_URL="${S3_BASE}/${ENCODED_VERSION}/${ENCODED_TAR}" \
    && mkdir -p /root/.local/bin /root/.local/share/cortex \
    && curl -fSL "$TAR_URL" -o /tmp/coco.tar.gz \
    && tar -xzf /tmp/coco.tar.gz -C /tmp \
    && EXTRACTED_DIR=$(find /tmp -maxdepth 1 -type d -name 'coco-*' | head -1) \
    && mv "$EXTRACTED_DIR" "/root/.local/share/cortex/${VERSION}" \
    && ln -sf "/root/.local/share/cortex/${VERSION}/cortex" /root/.local/bin/cortex \
    && rm -f /tmp/coco.tar.gz \
    && echo "Cortex Code v${VERSION} installed (binary not verified — will run on target platform)"
ENV PATH="/root/.local/bin:$PATH"

# Go supervisor
COPY --from=go-builder /build/p67-runner /usr/local/bin/p67-runner

# TypeScript host: pnpm-deployed controld with flat node_modules
COPY --from=node-builder /deployed/dist /app/node-host/dist
COPY --from=node-builder /deployed/node_modules /app/node-host/node_modules

# package.json for ESM resolution (type: module)
RUN printf '{"type":"module"}\n' > /app/node-host/package.json

# Symlink so the Go runner can exec `node /app/host.js`
RUN ln -s /app/node-host/dist/lib/runtime/host.js /app/host.js

ENTRYPOINT ["p67-runner"]
