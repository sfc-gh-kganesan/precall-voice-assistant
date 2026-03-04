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
FROM node:20-alpine AS runtime

# Python runtime for Python workflows (g++ needed to build snowflake-connector-python)
RUN apk add --no-cache python3 py3-pip g++ python3-dev

WORKDIR /app

# Python host + deps
COPY containers/runner/requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY containers/runner/host.py /app/host.py

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
