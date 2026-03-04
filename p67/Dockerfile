# syntax=docker/dockerfile:1

# Base stage with pnpm setup
FROM node:20-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app

# Install all dependencies
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.json ./
COPY packages ./packages
COPY services ./services
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

# Shared builder stage - builds entire monorepo
FROM deps AS builder
RUN pnpm run build

# Generate Prisma Client for database package
# DATABASE_URL is required by prisma.config.ts but not used during generate
ENV DATABASE_URL="postgresql://placeholder:placeholder@localhost:5432/placeholder"
RUN cd packages/db && pnpm db:generate

# Generic service runner stage
FROM base AS runner
ARG SERVICE_NAME
ARG SERVICE_PORT=3000

# Install Python for multilingual workflow support
# Build tools needed for snowflake-connector-python native extensions
# Install Docker CLI for sandbox mode (spawning p67-runner containers)
RUN apk add --no-cache --virtual .build-deps \
        python3-dev \
        g++ \
        gcc \
        musl-dev \
    && apk add --no-cache python3 py3-pip docker-cli \
    && pip3 install --no-cache-dir --break-system-packages snowflake-connector-python \
    && apk del .build-deps

# Copy workspace config
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.json ./

# Copy package manifests for workspace resolution
COPY packages ./packages
COPY services/${SERVICE_NAME}/package.json ./services/${SERVICE_NAME}/

# Install production dependencies for specific service
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter=${SERVICE_NAME}...

# Copy built artifacts from builder
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/services/${SERVICE_NAME}/dist ./services/${SERVICE_NAME}/dist

ENV NODE_ENV=production
ENV PORT=${SERVICE_PORT}
ENV SERVICE_NAME=${SERVICE_NAME}
EXPOSE ${SERVICE_PORT}

# Entrypoint runs migrations then starts the service
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app/services/${SERVICE_NAME}
CMD ["/app/entrypoint.sh"]
